import pandas as pd

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

df = pd.read_csv("data/sdn.csv", header=None)
df.columns = column_names

# Strip whitespace from ALL string cells
df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# Replace placeholder values
df = df.replace("-0-", "")

print("Total rows:", len(df))
print("\nFirst 3 rows:")
print(df.head(3))



def row_to_text(row):
    parts = []

    if row["ent_num"]:
        parts.append(f"Entity Number: {row['ent_num']}")
    if row["sdn_name"]:
        parts.append(f"Name: {row['sdn_name']}")
    if row["sdn_type"]:
        parts.append(f"Type: {row['sdn_type']}")
    if row["program"]:
        parts.append(f"Program: {row['program']}")
    if row["remarks"]:
        parts.append(f"Remarks: {row['remarks']}")

    return "\n".join(parts)


# Create a new column with formatted text
df["rag_text"] = df.apply(row_to_text, axis=1)

# Show one example
print("\nSample RAG text:\n")
print(df["rag_text"].iloc[2])