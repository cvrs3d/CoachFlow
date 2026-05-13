from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    app_env: str = "dev"
    database_url: str

    coach_telegram_ids: str = ""

    client_cancellation_deadline_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def coach_ids(self) -> list[int]:
        if not self.coach_telegram_ids:
            return []

        return [int(item.strip()) for item in self.coach_telegram_ids.split(",") if item.strip()]


settings = Settings()  # pyright: ignore[reportCallIssue]
