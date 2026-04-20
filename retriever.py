import json
import pickle
import networkx as nx
from rank_bm25 import BM25Okapi
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from rapidfuzz import fuzz
from sentence_transformers import CrossEncoder

FUZZY_MATCH_THRESHOLD = 85


# ----------------------------
# Load Vector Store
# ----------------------------
def load_vector_store():
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = Chroma(
        persist_directory="vector_db",
        embedding_function=embedding_model
    )

    return vector_store


# ----------------------------
# Load BM25 Corpus
# ----------------------------
def load_bm25():
    with open("bm25_corpus.json", "r") as f:
        data = json.load(f)

    corpus = data["corpus"]
    metadata = data["metadata"]

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, metadata


# ----------------------------
# Load Knowledge Graph
# ----------------------------
def load_graph():
    with open("knowledge_graph.pkl", "rb") as f:
        return pickle.load(f)


# ----------------------------
# Load Cross Encoder
# ----------------------------
def load_cross_encoder():
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")


# ----------------------------
# Graph Lookup
# ----------------------------
def graph_lookup(query):
    G = load_graph()
    query_clean = query.strip()

    if query_clean in G.nodes:
        node_type = G.nodes[query_clean].get("type")

        if node_type in ["alias", "id"]:
            neighbors = list(G.neighbors(query_clean))
            for n in neighbors:
                if G.nodes[n].get("type") == "entity":
                    return n

        if node_type == "entity":
            return query_clean

    return None


# ----------------------------
# Hybrid Retrieval
# ----------------------------
def hybrid_retrieve(query, k=5):
    vector_store = load_vector_store()
    bm25, metadata = load_bm25()

    # Vector retrieval
    vector_docs = vector_store.similarity_search(query, k=k)
    vector_candidates = [doc.metadata for doc in vector_docs]

    # BM25 retrieval
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:k]

    bm25_candidates = [metadata[i] for i in top_indices]

    # Merge & deduplicate
    combined = vector_candidates + bm25_candidates

    unique_candidates = {}
    for candidate in combined:
        ent_num = candidate["ent_num"]
        if ent_num not in unique_candidates:
            unique_candidates[ent_num] = candidate

    return list(unique_candidates.values())


# ----------------------------
# Cross-Encoder Re-ranking
# ----------------------------
def rerank_candidates(query, candidates):
    model = load_cross_encoder()

    pairs = [(query, c.get("name", "")) for c in candidates]
    scores = model.predict(pairs)

    scored_candidates = list(zip(candidates, scores))
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    reranked = [c for c, score in scored_candidates]

    return reranked


# ----------------------------
# Deterministic Matching
# ----------------------------
def normalize(text):
    return text.lower().strip()


def deterministic_decision(query, candidates):
    query_norm = normalize(query)

    for candidate in candidates:
        name = candidate.get("name", "")
        aliases = candidate.get("aliases", [])
        ids = candidate.get("ids", [])

        name_norm = normalize(name)

        # Exact primary match
        if query_norm == name_norm:
            return {
                "decision": "MATCH",
                "entity_number": candidate["ent_num"],
                "confidence": 1.0,
                "reason": "Exact match with primary name."
            }

        # Exact alias match
        for alias in aliases:
            if query_norm == normalize(alias):
                return {
                    "decision": "MATCH",
                    "entity_number": candidate["ent_num"],
                    "confidence": 1.0,
                    "reason": f"Exact match with alias '{alias}'."
                }

        # Exact ID match
        for identifier in ids:
            if query_norm == normalize(identifier):
                return {
                    "decision": "MATCH",
                    "entity_number": candidate["ent_num"],
                    "confidence": 1.0,
                    "reason": f"Exact match with ID '{identifier}'."
                }

        # Fuzzy match on primary name
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


# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    query = input("Enter name to screen: ")

    # 1️⃣ Graph lookup first
    graph_entity = graph_lookup(query)

    if graph_entity:
        decision = {
            "decision": "MATCH",
            "entity_number": graph_entity,
            "confidence": 1.0,
            "reason": "Graph alias/entity lookup match."
        }
    else:
        # Hybrid retrieval
        candidates = hybrid_retrieve(query)

        # Cross-encoder re-ranking
        reranked = rerank_candidates(query, candidates)

        # Deterministic decision
        decision = deterministic_decision(query, reranked)

    print("\nDecision:\n")
    print(decision)