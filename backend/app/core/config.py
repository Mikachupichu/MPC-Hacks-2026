from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mpc_hacks_2026"
    app_name: str = "MPC Hacks 2026 API"
    app_version: str = "0.1.0"
    debug: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
