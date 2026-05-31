from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mpc_hacks_2026"
    app_name: str = "MPC Hacks 2026 API"
    app_version: str = "0.1.0"
    debug: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

    model_config = {"env_file": ".env.local", "env_file_encoding": "utf-8"}


settings = Settings()
