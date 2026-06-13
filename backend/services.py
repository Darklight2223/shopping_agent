import json
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