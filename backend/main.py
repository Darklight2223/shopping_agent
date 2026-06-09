from dotenv import load_dotenv
import os

from sentence_transformers import SentenceTransformer
from supabase import create_client
from groq import Groq

load_dotenv()

# -----------------------------
# CONFIG
# -----------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TOP_K = 5
max_price = 500

# -----------------------------
# CLIENTS
# -----------------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = Groq(
    api_key=GROQ_API_KEY
)

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

import re

def parse_price(price):
    if not price:
        return 0.0

    cleaned = re.sub(r"[^\d.]", "", str(price))

    try:
        return float(cleaned)
    except:
        return 0.0


# -----------------------------
# SEARCH FUNCTION
# -----------------------------
def search_products(query: str):

    query_embedding = embedding_model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    result = supabase.rpc(
        "match_products_filtered",
        {
            "query_embedding": query_embedding,
            "max_price": max_price,
            "match_count": TOP_K
        }
    ).execute()

    products = result.data

    if not products:
        return []

    # discount percentage
    for p in products:

        actual = parse_price(p.get("actual_price", 0))
        discount = parse_price(p.get("discount_price", 0))

        if actual > 0:
            p["discount_percent"] = (
                (actual - discount) / actual
            ) * 100
        else:
            p["discount_percent"] = 0

    # sort by discount descending
    products.sort(
        key=lambda x: x["discount_percent"],
        reverse=True
    )

    return products[:5]


# -----------------------------
# LLM RECOMMENDATION
# -----------------------------
def recommend(query, products):

    prompt = f"""
User Query:
{query}

Products:
{products}

Analyze these products and recommend the best options.

For each product include:
- Name
- Category
- Rating
- Actual Price
- Discount Price
- Discount %
- Why it matches user query

Keep response concise.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


# -----------------------------
# MAIN
# -----------------------------
query = input("Search Product: ")

products = search_products(query)

if not products:
    print("No products found.")
else:

    print("\nTop 5 Products:\n")

    for p in products:

        print("=" * 60)

        print("Name:", p.get("name"))
        print("Main Category:", p.get("main_category"))
        print("Sub Category:", p.get("sub_category"))
        print("Rating:", p.get("ratings"))
        print("Actual Price:", p.get("actual_price"))
        print("Discount Price:", p.get("discount_price"))
        print(
            "Discount %:",
            round(p.get("discount_percent", 0), 2)
        )

    print("\n\nAI Recommendation:\n")

    recommendation = recommend(
        query,
        products
    )

    print(recommendation)