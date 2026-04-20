import json
import random

print("Loading BM25 metadata...")

with open("bm25_corpus.json", "r") as f:
    data = json.load(f)

metadata = data.get("metadata", [])

if not metadata:
    print("ERROR: No metadata found.")
    exit()

print(f"Loaded {len(metadata)} entities.")

# Select 20 random sanctioned entities
sample_entities = random.sample(metadata, min(20, len(metadata)))

auto_tests = []

for entity in sample_entities:
    name = entity.get("name", "")
    ent_num = entity.get("ent_num")

    if not name:
        continue

    # Exact match
    auto_tests.append({
        "query": name,
        "label": "MATCH",
        "entity_number": ent_num
    })

    # Lowercase version
    auto_tests.append({
        "query": name.lower(),
        "label": "MATCH",
        "entity_number": ent_num
    })

    # Small typo
    if len(name) > 5:
        typo = name[:-1]
        auto_tests.append({
            "query": typo,
            "label": "MATCH",
            "entity_number": ent_num
        })

# Add 20 random negative examples
for _ in range(20):
    random_string = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
    auto_tests.append({
        "query": random_string,
        "label": "NO_MATCH",
        "entity_number": None
    })

print(f"Generated {len(auto_tests)} test samples.")

with open("evaluation_data_auto.json", "w") as f:
    json.dump(auto_tests, f, indent=2)

print("Auto evaluation dataset generated successfully.")