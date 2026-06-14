from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File, Form
from pydantic import BaseModel
import os

from config import DEFAULT_MAX_PRICE

from services import (
    extract_query,
    recommend_from_image,
    search_products,
    recommend
)

from tools import (
    prepare_products,
    filter_by_budget
)

app = FastAPI(
    title="Product Recommendation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
def root():
    return {
        "message": "Product Recommendation API is running"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    query = request.message.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid query."
        )

    try:

        extracted_query = extract_query(query)

        max_price = (
            extracted_query.get("max_price")
            or DEFAULT_MAX_PRICE
        )

        products = search_products(
            query,
            max_price
        )

        if not products:
            return {
                "message": "No products found.",
                "products": []
            }

        cleaned_products = prepare_products(
            products
        )

        cleaned_products = filter_by_budget(
            cleaned_products,
            max_price
        )

        recommendations = recommend(
            query=query,
            extracted_query=extracted_query,
            products=cleaned_products
        )

        return {
            "message": recommendations,
            "products": cleaned_products[:10]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/image-search")
async def image_search(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    message: str = Form("")

):
    try:

        os.makedirs("uploads", exist_ok=True)

        image_path = f"uploads/{file.filename}"

        with open(image_path, "wb") as f:
            f.write(await file.read())

        result = recommend_from_image(
            image_path,
            message
        )

        return {
            "message": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )