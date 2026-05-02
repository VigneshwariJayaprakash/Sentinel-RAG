import ollama
import json


def build_prompt(query, retrieved_docs):
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    prompt = f"""
You are a compliance screening system.

You MUST respond in strict JSON format only.

Use ONLY the provided sanctions entries.
Do NOT use outside knowledge.

User Query:
{query}

Sanctions Entries:
{context}

If the query clearly matches one of the entries:
- decision = "MATCH"
- entity_number = matching entity number
- confidence = 0.9 or above

If no clear match:
- decision = "NO_MATCH"
- entity_number = null
- confidence = below 0.5

Respond EXACTLY in this JSON format:

{{
  "decision": "MATCH or NO_MATCH",
  "entity_number": "string or null",
  "confidence": float,
  "reason": "short explanation"
}}
"""

    return prompt


def generate_decision(query, retrieved_docs):
    prompt = build_prompt(query, retrieved_docs)

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response["message"]["content"]

    try:
        return json.loads(content)
    except:
        return {
            "decision": "ERROR",
            "entity_number": None,
            "confidence": 0.0,
            "reason": "Model did not return valid JSON",
            "raw_output": content
        }
