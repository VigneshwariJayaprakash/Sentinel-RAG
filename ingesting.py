import pandas as pd
import json
import re
import pickle
import networkx as nx
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


# -----------------------------------
# 1. Load OFAC CSV
# -----------------------------------
def load_sdn_csv(path="data/sdn.csv"):
    column_names = [
        "ent_num",
        "sdn_name",
        "sdn_type",
        "program",
        "title",
        "call_sign",
        "vessel_type",
        "tonnage",
        "gross_registered_tonnage",
        "vessel_flag",
        "vessel_owner",
        "remarks"
    ]

    df = pd.read_csv(path, header=None)
    df.columns = column_names
    return df


# -----------------------------------
# 2. Clean Data
# -----------------------------------
def clean_dataframe(df):
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace("-0-", "")
    return df


# -----------------------------------
# 3. Convert Row → Text
# -----------------------------------
def row_to_text(row):
    parts = []

    if isinstance(row["ent_num"], str) and row["ent_num"]:
        parts.append(f"Entity Number: {row['ent_num']}")

    if isinstance(row["sdn_name"], str) and row["sdn_name"]:
        parts.append(f"Name: {row['sdn_name']}")

    if isinstance(row["program"], str) and row["program"]:
        parts.append(f"Program: {row['program']}")

    if isinstance(row["remarks"], str) and row["remarks"]:
        parts.append(f"Remarks: {row['remarks']}")

    return "\n".join(parts)


# -----------------------------------
# 4. Alias Extraction
# -----------------------------------
def extract_aliases(remarks):
    if not isinstance(remarks, str):
        return []

    pattern = r"a\.k\.a\.\s*'([^']+)'"
    aliases = re.findall(pattern, remarks, flags=re.IGNORECASE)

    return [alias.strip() for alias in aliases if alias.strip()]


# -----------------------------------
# 5. ID Extraction
# -----------------------------------
def extract_ids(remarks):
    if not isinstance(remarks, str):
        return []

    # Pattern like RA-7884, V-17789572, etc.
    pattern = r"[A-Z]+-\d+"
    ids = re.findall(pattern, remarks)

    return ids


# -----------------------------------
# 6. Create Documents
# -----------------------------------
def create_documents(df):
    documents = []

    for _, row in df.iterrows():
        aliases = extract_aliases(row["remarks"])
        ids = extract_ids(row["remarks"])

        name = row["sdn_name"] if isinstance(row["sdn_name"], str) else ""

        metadata = {
            "ent_num": str(row["ent_num"]),
            "name": name,
            "program": row["program"] if isinstance(row["program"], str) else ""
        }

        if aliases:
            metadata["aliases"] = aliases

        if ids:
            metadata["ids"] = ids

        doc = Document(
            page_content=row_to_text(row),
            metadata=metadata
        )

        documents.append(doc)

    return documents


# -----------------------------------
# 7. Build Vector Store
# -----------------------------------
def build_vector_store(documents):
    print("Loading embedding model...")

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    print("Creating vector database...")

    Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory="vector_db"
    )

    print("Vector database created successfully.")


# -----------------------------------
# 8. Build BM25 Corpus
# -----------------------------------
def build_bm25_corpus(documents):
    bm25_corpus = []
    metadata_store = []

    for doc in documents:
        name = doc.metadata.get("name", "")
        aliases = doc.metadata.get("aliases", [])

        if not isinstance(name, str):
            name = ""

        aliases = [a for a in aliases if isinstance(a, str)]

        full_text = name + " " + " ".join(aliases)

        bm25_corpus.append(full_text)
        metadata_store.append(doc.metadata)

    with open("bm25_corpus.json", "w") as f:
        json.dump({
            "corpus": bm25_corpus,
            "metadata": metadata_store
        }, f)

    print("BM25 corpus saved.")


# -----------------------------------
# 9. Build Knowledge Graph
# -----------------------------------
def build_knowledge_graph(documents):
    G = nx.Graph()

    for doc in documents:
        ent_num = doc.metadata["ent_num"]
        name = doc.metadata.get("name", "")
        program = doc.metadata.get("program", "")
        aliases = doc.metadata.get("aliases", [])
        ids = doc.metadata.get("ids", [])

        # Entity node
        G.add_node(ent_num, type="entity", name=name)

        # Program node
        if program:
            G.add_node(program, type="program")
            G.add_edge(ent_num, program, relation="UNDER_PROGRAM")

        # Alias nodes
        for alias in aliases:
            G.add_node(alias, type="alias")
            G.add_edge(ent_num, alias, relation="HAS_ALIAS")

        # ID nodes
        for identifier in ids:
            G.add_node(identifier, type="id")
            G.add_edge(ent_num, identifier, relation="HAS_ID")

    with open("knowledge_graph.pkl", "wb") as f:
        pickle.dump(G, f)

    print("Knowledge graph saved.")


# -----------------------------------
# MAIN
# -----------------------------------
def main():
    print("Starting ingestion pipeline...")

    df = load_sdn_csv()
    df = clean_dataframe(df)

    documents = create_documents(df)

    print("Total documents:", len(documents))

    build_vector_store(documents)
    build_bm25_corpus(documents)
    build_knowledge_graph(documents)


if __name__ == "__main__":
    main()