from fastapi import FastAPI
from mangum import Mangum

# from app.api import items

app = FastAPI(title="Pyjaapp Backend API")

# app.include_router(items.router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "environment": "serverless"}


# Mangum wrapper for AWS Lambda
handler = Mangum(app)
