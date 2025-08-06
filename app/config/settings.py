from pydantic_settings import BaseSettings
from pydantic import AnyUrl, SecretStr


class Settings(BaseSettings):
    telegram_token: SecretStr
    hh_client_id: str
    hh_client_secret: str
    oauth_redirect_uri: AnyUrl
    database_url: str = "sqlite+aiosqlite:///./data.db"
    user_agent: str = "headhunter-xorbot/1.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
