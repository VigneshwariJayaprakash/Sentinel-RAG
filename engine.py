import json
import pickle
import networkx as nx
from rank_bm25 import BM25Okapi
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from rapidfuzz import fuzz
from sentence_transformers import CrossEncoder
import time

class SentinelRAGEngine:

    def __init__(self):
        print("Initializing SentinelRAG Engine...")

        # Load Vector Store (degrade gracefully if model download is blocked)
        self.embedding_model = None
        self.vector_store = None
        try:
            self.embedding_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            self.vector_store = Chroma(
                persist_directory="vector_db",
                embedding_function=self.embedding_model
            )
        except Exception as e:
            print(f"Warning: Vector retrieval unavailable, falling back to BM25 only. {e}")

        # Load BM25
        with open("bm25_corpus.json", "r") as f:
            data = json.load(f)

        corpus = data["corpus"]
        self.metadata = data["metadata"]

        tokenized_corpus = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Load Knowledge Graph
        with open("knowledge_graph.pkl", "rb") as f:
            self.graph = pickle.load(f)

        # Load Cross Encoder (fallback to non-reranked flow if blocked)
        self.cross_encoder = None
        try:
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")
        except Exception as e:
            print(f"Warning: Cross-encoder unavailable, rerank disabled. {e}")

        print("Engine ready.")

    def normalize(self, text):
        return text.lower().strip()

    def graph_lookup(self, query):
        query_clean = query.strip()

        if query_clean in self.graph.nodes:
            node_type = self.graph.nodes[query_clean].get("type")

            if node_type in ["alias", "id"]:
                neighbors = list(self.graph.neighbors(query_clean))
                for n in neighbors:
                    if self.graph.nodes[n].get("type") == "entity":
                        return n

            if node_type == "entity":
                return query_clean

        return None

    def hybrid_retrieve(self, query, k=5):
        vector_candidates = []
        if self.vector_store is not None:
            vector_docs = self.vector_store.similarity_search(query, k=k)
            vector_candidates = [doc.metadata for doc in vector_docs]

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:k]

        bm25_candidates = [self.metadata[i] for i in top_indices]

        combined = vector_candidates + bm25_candidates

        unique_candidates = {}
        for candidate in combined:
            ent_num = candidate["ent_num"]
            if ent_num not in unique_candidates:
                unique_candidates[ent_num] = candidate

        return list(unique_candidates.values())

    def rerank(self, query, candidates):
        if self.cross_encoder is None:
            return candidates

        pairs = [(query, c.get("name", "")) for c in candidates]
        scores = self.cross_encoder.predict(pairs)

        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        return [c for c, score in scored]

    def deterministic_decision(self, query, candidates):

        FUZZY_MATCH_THRESHOLD = 85
        query_norm = self.normalize(query)

        for candidate in candidates:
            name = candidate.get("name", "")
            aliases = candidate.get("aliases", [])
            ids = candidate.get("ids", [])

            name_norm = self.normalize(name)

            if query_norm == name_norm:
                return {
                    "decision": "MATCH",
                    "entity_number": candidate["ent_num"],
                    "confidence": 1.0,
                    "reason": "Exact match with primary name."
                }

            for alias in aliases:
                if query_norm == self.normalize(alias):
                    return {
                        "decision": "MATCH",
                        "entity_number": candidate["ent_num"],
                        "confidence": 1.0,
                        "reason": f"Exact match with alias '{alias}'."
                    }

            for identifier in ids:
                if query_norm == self.normalize(identifier):
                    return {
                        "decision": "MATCH",
                        "entity_number": candidate["ent_num"],
                        "confidence": 1.0,
                        "reason": f"Exact match with ID '{identifier}'."
                    }

            similarity = fuzz.token_sort_ratio(query_norm, name_norm)
            if similarity >= FUZZY_MATCH_THRESHOLD:
                return {
                    "decision": "MATCH",
                    "entity_number": candidate["ent_num"],
                    "confidence": round(similarity / 100, 2),
                    "reason": f"High fuzzy similarity ({similarity})."
                }

        return {
            "decision": "NO_MATCH",
            "entity_number": None,
            "confidence": 0.0,
            "reason": "No sufficient similarity found."
        }

    def screen(self, query):

        timings = {}
        start_total = time.time()

        #  Graph lookup
        start_graph = time.time()
        graph_entity = self.graph_lookup(query)
        timings["graph_lookup_ms"] = (time.time() - start_graph) * 1000

        if graph_entity:
            timings["total_ms"] = (time.time() - start_total) * 1000
            return {
                "decision": "MATCH",
                "entity_number": graph_entity,
                "confidence": 1.0,
                "reason": "Graph alias/entity lookup match.",
                "latency": timings
            }

        #  Hybrid retrieval
        start_retrieval = time.time()
        candidates = self.hybrid_retrieve(query)
        timings["hybrid_retrieval_ms"] = (time.time() - start_retrieval) * 1000

        # Quick fuzzy pre-check (no cross-encoder yet)
        query_norm = self.normalize(query)
        top_candidate = candidates[0]
        name_norm = self.normalize(top_candidate.get("name", ""))

        quick_similarity = fuzz.token_sort_ratio(query_norm, name_norm)

        # If very high similarity → skip cross-encoder
        if quick_similarity >= 92:
            decision = self.deterministic_decision(query, candidates)
            timings["rerank_ms"] = 0
            timings["decision_logic_ms"] = 0
            timings["total_ms"] = (time.time() - start_total) * 1000
            decision["latency"] = timings
            decision["reason"] += " (Skipped cross-encoder)"
            return decision

        # Otherwise use cross-encoder
        start_rerank = time.time()
        reranked = self.rerank(query, candidates)
        timings["rerank_ms"] = (time.time() - start_rerank) * 1000

        #  Deterministic decision
        start_decision = time.time()
        decision = self.deterministic_decision(query, reranked)
        timings["decision_logic_ms"] = (time.time() - start_decision) * 1000

        timings["total_ms"] = (time.time() - start_total) * 1000
        decision["latency"] = timings

        return decision