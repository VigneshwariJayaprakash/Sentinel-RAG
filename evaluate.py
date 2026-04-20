import json
from retriever import graph_lookup, hybrid_retrieve, deterministic_decision


def run_query(query):
    # 1. Graph lookup
    graph_entity = graph_lookup(query)

    if graph_entity:
        return {
            "decision": "MATCH",
            "entity_number": graph_entity
        }

    # 2. Hybrid retrieval fallback
    candidates = hybrid_retrieve(query)
    result = deterministic_decision(query, candidates)

    return {
        "decision": result["decision"],
        "entity_number": result["entity_number"]
    }


def evaluate():
    with open("evaluation_data_auto.json", "r") as f:
        test_data = json.load(f)

    total = len(test_data)
    correct = 0
    false_positive = 0
    false_negative = 0

    for item in test_data:
        query = item["query"]
        true_label = item["label"]
        true_entity = item["entity_number"]

        prediction = run_query(query)

        predicted_label = prediction["decision"]
        predicted_entity = prediction["entity_number"]

        if predicted_label == true_label:
            if predicted_label == "MATCH":
                if str(predicted_entity) == str(true_entity):
                    correct += 1
                else:
                    false_positive += 1
            else:
                correct += 1
        else:
            if predicted_label == "MATCH":
                false_positive += 1
            else:
                false_negative += 1
            print("MISSED CASE:", query, "Expected:", true_label, "Predicted:", predicted_label)

    accuracy = correct / total
    precision = correct / (correct + false_positive) if (correct + false_positive) > 0 else 0
    recall = correct / (correct + false_negative) if (correct + false_negative) > 0 else 0

    print("\n=== Evaluation Report ===")
    print(f"Total Samples: {total}")
    print(f"Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    print(f"False Positives: {false_positive}")
    print(f"False Negatives: {false_negative}")


if __name__ == "__main__":
    evaluate()



    