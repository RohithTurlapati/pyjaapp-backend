from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "dev"
    s3_bucket_name: str = "pyjaapp-dev-assets"
    database_url: str = "postgresql+asyncpg://appuser:testpass@localhost:5432/postgres"
    jwt_secret_key: str = "supersecretkey"
    jwt_algorithm: str = "HS256"
    google_client_id: str = ""
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "Pyjaapp <pyjaapp@gmail.com>"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
