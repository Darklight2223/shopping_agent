import json
import base64
from typing import List

from pydantic import BaseModel

from sentence_transformers import SentenceTransformer
from supabase import create_client

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from config import *
from prompts import *
from tools import add_discount_percentage



class QueryExtraction(BaseModel):
    product_type: str
    category: str
    max_price: int
    features: List[str]

class ImageProductInfo(BaseModel):
    product_type: str
    category: str
    features: List[str]
    color: str
    style: str

# class Recommendation(BaseModel):
#     name: str
#     category: str
#     rating: str
#     actual_price: str
#     discount_price: str
#     discount_percent: str
#     reason: str


# class Recommendations(BaseModel):
#     recommendations: List[Recommendation]



supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)



def extract_query(query):

    prompt = ChatPromptTemplate.from_template(
        EXTRACT_QUERY_PROMPT
    )

    structured_llm = llm.with_structured_output(
        QueryExtraction
    )

    chain = prompt | structured_llm

    try:

        result = chain.invoke(
            {
                "query": query
            }
        )

        print("\n=== EXTRACTED QUERY ===")
        print(result)

        return result.model_dump()

    except Exception as e:

        print(
            f"Extraction Error: {e}"
        )

        return {
            "product_type": "",
            "category": "",
            "max_price": DEFAULT_MAX_PRICE,
            "features": []
        }




def search_products(
    query,
    max_price
):

    embedding = embedding_model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    result = supabase.rpc(
        "match_products_filtered",
        {
            "query_embedding": embedding,
            "max_price": max_price,
            "match_count": TOP_K
        }
    ).execute()

    products = result.data or []

    products = add_discount_percentage(
        products
    )

    return products



def recommend(
    query,
    extracted_query,
    products
):

    prompt = ChatPromptTemplate.from_template(
        RECOMMEND_PROMPT
    )


    chain = prompt | llm

    result = chain.invoke(
        {
            "query": query,
            "constraints": json.dumps(
                extracted_query,
                indent=2
            ),
            "products": json.dumps(
                products,
                indent=2
            )
        }
    )

    print("\n=== RECOMMENDATIONS ===")
    print(result.content)

    return result.content


def extract_from_image(image_path, message=""):
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(
            f.read()
        ).decode()

    vision_llm = ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=GROQ_API_KEY,
        temperature=0
    )

    structured_llm = vision_llm.with_structured_output(
        ImageProductInfo
    )

    text_prompt = (message or "").strip()
    prompt = f"""
    Analyze this image.

    Extract:
    - product_type
    - category
    - color
    - style
    - important product features

    The user also provided this shopping text prompt:
    {text_prompt if text_prompt else 'No additional text prompt.'}

    Use the text prompt as extra context for the product analysis.
    If the text mentions style, budget, brand, color, features, or category, reflect that in the extraction.

    Return only structured output.
    """

    result = structured_llm.invoke(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
    )

    return result.model_dump()


def image_to_query(info, message=""):
    parts = [
        info.get("product_type", ""),
        info.get("category", ""),
        info.get("color", ""),
        info.get("style", ""),
        *info.get("features", [])
    ]

    if message:
        parts.append(message.strip())

    return " ".join(
        str(p) for p in parts if p
    )


def recommend_from_image(image_path, message):
    message = (message or "").strip()

    image_info = extract_from_image(
        image_path,
        message
    )

    query = image_to_query(
        image_info,
        message
    )

    extracted_query = {}
    if message:
        extracted_query = extract_query(message)

    merged_constraints = {
        "product_type": extracted_query.get("product_type") or image_info.get("product_type", ""),
        "category": extracted_query.get("category") or image_info.get("category", ""),
        "max_price": extracted_query.get("max_price") or DEFAULT_MAX_PRICE,
        "features": list(dict.fromkeys((image_info.get("features", []) or []) + (extracted_query.get("features", []) or []))),
        "color": image_info.get("color", ""),
        "style": image_info.get("style", "")
    }

    max_price = merged_constraints.get("max_price") or DEFAULT_MAX_PRICE

    products = search_products(
        query=query,
        max_price=max_price
    )

    products = add_discount_percentage(
        products
    )

    res = recommend(
        query=query,
        extracted_query=merged_constraints,
        products=products[:10]
    )

    return res