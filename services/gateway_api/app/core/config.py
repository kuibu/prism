from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gateway_env: str = Field(default="development", validation_alias="GATEWAY_ENV")
    gateway_host: str = Field(default="0.0.0.0", validation_alias="GATEWAY_HOST")
    gateway_port: int = Field(default=8000, validation_alias="GATEWAY_PORT")

    opa_url: str = Field(default="http://opa:8181", validation_alias="OPA_URL")
    opa_policy_path: str = Field(default="/v1/data/prism/allow", validation_alias="OPA_POLICY_PATH")
    opa_data_root: str = Field(default="/v1/data/prism", validation_alias="OPA_DATA_ROOT")

    immudb_host: str = Field(default="immudb", validation_alias="IMMUDB_HOST")
    immudb_port: int = Field(default=3322, validation_alias="IMMUDB_PORT")
    immudb_timeout_seconds: float = Field(default=2.0, validation_alias="IMMUDB_TIMEOUT_SECONDS")
    immudb_retry_attempts: int = Field(default=3, validation_alias="IMMUDB_RETRY_ATTEMPTS")
    immudb_username: str = Field(default="immudb", validation_alias="IMMUDB_USERNAME")
    immudb_password: str = Field(default="immudb", validation_alias="IMMUDB_PASSWORD")
    immudb_database: str = Field(default="defaultdb", validation_alias="IMMUDB_DATABASE")

    matrix_homeserver_url: str = Field(
        default="http://synapse:8008",
        validation_alias="MATRIX_HOMESERVER_URL",
    )
    matrix_upload_max_bytes: int = Field(
        default=10_485_760,
        validation_alias="MATRIX_UPLOAD_MAX_BYTES",
    )

    http_timeout_seconds: float = Field(default=3.0, validation_alias="HTTP_TIMEOUT_SECONDS")
    http_retry_attempts: int = Field(default=3, validation_alias="HTTP_RETRY_ATTEMPTS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
