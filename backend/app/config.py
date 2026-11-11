import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jwt_secret: str = ""
    database_url: str = "sqlite:///./trading.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            jwt_secret=os.getenv("JWT_SECRET", ""),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./trading.db"),
        )


settings = Settings.from_env()
