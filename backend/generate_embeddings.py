
# pip install -q sentence-transformers supabase

import torch
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

# ==================================
# CONFIG
# ==================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TABLE_NAME = "products"

# ==================================
# SUPABASE
# ==================================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================================
# GPU CHECK
# ==================================

print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# ==================================
# LOAD MODEL
# ==================================

print("Loading embedding model...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
print("Model loaded.")

# ==================================
# PROCESS ONE NULL ROW AT A TIME
# ==================================

total_processed = 0

while True:
    row = (
        supabase.table(TABLE_NAME)
        .select("id,name,main_category,sub_category")
        .is_("embedding", "null")
        .order("id")
        .limit(1)
        .execute()
        .data
    )

    if not row:
        break

    row = row[0]

    text = (
        f"Product Name: {row.get('name', '')} "
        f"Main Category: {row.get('main_category', '')} "
        f"Sub Category: {row.get('sub_category', '')}"
    )

    try:
        embedding = model.encode(
            text,
            normalize_embeddings=True
        ).tolist()

        supabase.table(TABLE_NAME).update(
            {"embedding": embedding}
        ).eq(
            "id",
            row["id"]
        ).execute()

        total_processed += 1

        if total_processed % 100 == 0:
            print(f"✓ Processed {total_processed}")

    except Exception as e:
        print(f"Failed ID {row['id']}: {e}")

print(f"Done. Total processed: {total_processed}")

