from dotenv import load_dotenv
import os
import re
import json

from sentence_transformers import SentenceTransformer
from supabase import create_client
from groq import Groq


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TOP_K = 20
DEFAULT_MAX_PRICE = 500



supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

client = Groq(
    api_key=GROQ_API_KEY
)

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)



def parse_price(price):

    if not price:
        return 0.0

    cleaned = re.sub(
        r"[^\d.]",
        "",
        str(price)
    )

    try:
        return float(cleaned)
    except Exception:
        return 0.0



def extract_query(query: str):

    prompt = f"""
Extract shopping constraints from the user query.

User Query:
{query}

Return ONLY valid JSON.

Schema:

{{
    "product_type": "",
    "category": "",
    "max_price": null,
    "features": []
}}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            response_format={
                "type": "json_object"
            }
        )

        return json.loads(
            response.choices[0].message.content
        )

    except Exception as e:

        print("Query extraction failed:", e)

        return {
            "product_type": "",
            "category": "",
            "max_price": DEFAULT_MAX_PRICE,
            "features": []
        }




def search_products(
    query: str,
    max_price: float
):

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

    for p in products:

        actual = parse_price(
            p.get("actual_price")
        )

        discount = parse_price(
            p.get("discount_price")
        )

        if actual > 0:

            p["discount_percent"] = round(
                ((actual - discount) / actual) * 100,
                2
            )

        else:

            p["discount_percent"] = 0

    return products



def prepare_products(products):

    cleaned = []

    for p in products:

        cleaned.append(
            {
                "name": p.get("name"),
                "category": p.get("main_category"),
                "rating": p.get("ratings"),
                "actual_price": p.get("actual_price"),
                "discount_price": p.get("discount_price"),
                "discount_percent": p.get(
                    "discount_percent"
                )
            }
        )

    return cleaned

def filter_by_budget(products, max_price):
    filtered = []
    for p in products:
        price = parse_price(p.get("discount_price"))
        if price <= max_price and p.get("name"):
            filtered.append(p)
    return filtered


def recommend(
    query,
    extracted_query,
    products
):

    prompt = f"""
You are a shopping recommendation assistant.

User Query:
{query}

Extracted Constraints:
{json.dumps(extracted_query, indent=2)}

Candidate Products:
{json.dumps(products, indent=2)}

Rules:

1. Recommend only relevant products.
2. Do not invent products.
3. No duplicates.
4. Respect budget constraints.
5. If no suitable products exist, return empty recommendations.
6. Prefer higher ratings and better discounts.

Return ONLY JSON.

Schema:

{{
    "recommendations": [
        {{
            "name": "",
            "category": "",
            "rating": "",
            "actual_price": "",
            "discount_price": "",
            "discount_percent": "",
            "reason": ""
        }}
    ]
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        response_format={
            "type": "json_object"
        }
    )

    return json.loads(
        response.choices[0].message.content
    )


def main():

    query = input(
        "Search Product: "
    ).strip()

    if not query:

        print(
            "Please enter a valid query."
        )
        return

    print("\nExtracting query...\n")

    extracted_query = extract_query(
        query
    )

    print(
        json.dumps(
            extracted_query,
            indent=2
        )
    )

    max_price = (
        extracted_query.get(
            "max_price"
        )
        or DEFAULT_MAX_PRICE
    )

    print("\nSearching products...\n")

    products = search_products(
        query=query,
        max_price=max_price
    )

    if not products:

        print("No products found.")
        return

    print(
        f"Retrieved {len(products)} products."
    )

    cleaned_products = prepare_products(products)
    cleaned_products = filter_by_budget(cleaned_products, max_price)

    print(
        "\nGenerating recommendations...\n"
    )

    recommendations = recommend(
        query=query,
        extracted_query=extracted_query,
        products=cleaned_products
    )

    print("=" * 80)
    print("AI RECOMMENDATIONS")
    print("=" * 80)

    print(
        json.dumps(
            recommendations,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
