"""Config base every service extends."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Shared configuration surface.

    Concrete, not abstract: the point is that every service reads the same names
    for the same things.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SERVICE_NAME: str = "unnamed"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    DEFAULT_HTTP_TIMEOUT: float = 10.0
