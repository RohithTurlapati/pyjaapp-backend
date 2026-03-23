from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "dev"
    dynamodb_table_name: str = "pyjaapp-dev-items"
    s3_bucket_name: str = "pyjaapp-dev-assets"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
