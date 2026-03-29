from contextlib import asynccontextmanager

from fastapi import FastAPI
from mangum import Mangum

from app.core.database import Base, engine
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In development, create tables automatically on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Pyjaapp Backend API", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth")


@app.get("/")
def health_check():
    return {"status": "ok", "environment": "serverless"}


# Mangum wrapper for AWS Lambda
handler = Mangum(app)
