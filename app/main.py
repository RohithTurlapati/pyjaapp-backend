from fastapi import FastAPI
from mangum import Mangum

from app.core.database import Base, engine
from app.routers import auth

app = FastAPI(title="Pyjaapp Backend API")


@app.get("/api/dev/init-db", tags=["dev"])
async def init_db():
    """
    Helper endpoint to safely create tables in Production
    without crashing Lambdas on startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return {"message": "Database tables created successfully!"}


app.include_router(auth.router, prefix="/api/auth")


@app.get("/")
def health_check():
    return {"status": "ok", "environment": "serverless"}


# Mangum wrapper for AWS Lambda
handler = Mangum(app)
