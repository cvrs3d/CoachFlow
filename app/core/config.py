from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    class Config:
        env_file = ".env"


settings = Settings()
