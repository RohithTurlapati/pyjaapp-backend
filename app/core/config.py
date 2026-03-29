from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "dev"
    s3_bucket_name: str = "pyjaapp-dev-assets"
    database_url: str = "postgresql+asyncpg://appuser:testpass@localhost:5432/postgres"
    jwt_secret_key: str = "supersecretkey"
    jwt_algorithm: str = "HS256"
    google_client_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
