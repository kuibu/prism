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
    matrix_agent_bot_username_prefix: str = Field(
        default="prism_agent",
        validation_alias="MATRIX_AGENT_BOT_USERNAME_PREFIX",
    )
    matrix_agent_bot_password_secret: str = Field(
        default="dev_agent_bot_secret",
        validation_alias="MATRIX_AGENT_BOT_PASSWORD_SECRET",
    )

    http_timeout_seconds: float = Field(default=3.0, validation_alias="HTTP_TIMEOUT_SECONDS")
    http_retry_attempts: int = Field(default=3, validation_alias="HTTP_RETRY_ATTEMPTS")
    telegram_api_base_url: str = Field(
        default="https://api.telegram.org",
        validation_alias="TELEGRAM_API_BASE_URL",
    )
    telegram_poll_default_timeout_seconds: int = Field(
        default=0,
        validation_alias="TELEGRAM_POLL_DEFAULT_TIMEOUT_SECONDS",
    )
    telegram_poll_default_limit: int = Field(
        default=20,
        validation_alias="TELEGRAM_POLL_DEFAULT_LIMIT",
    )
    telegram_outbound_default_limit: int = Field(
        default=3,
        validation_alias="TELEGRAM_OUTBOUND_DEFAULT_LIMIT",
    )

    agent_default_llm_enabled: bool = Field(
        default=True,
        validation_alias="AGENT_DEFAULT_LLM_ENABLED",
    )
    agent_default_llm_provider: str = Field(
        default="openai_compatible",
        validation_alias="AGENT_DEFAULT_LLM_PROVIDER",
    )
    agent_default_llm_model: str = Field(
        default="qwen2.5-32b",
        validation_alias="AGENT_DEFAULT_LLM_MODEL",
    )
    agent_default_llm_api_key: str = Field(
        default="",
        validation_alias="AGENT_DEFAULT_LLM_API_KEY",
    )
    agent_default_llm_base_url: str = Field(
        default="https://32b.qwen.rag8.cn/v1",
        validation_alias="AGENT_DEFAULT_LLM_BASE_URL",
    )
    agent_default_llm_api_path: str = Field(
        default="/chat/completions",
        validation_alias="AGENT_DEFAULT_LLM_API_PATH",
    )
    agent_default_llm_temperature: float = Field(
        default=0.3,
        validation_alias="AGENT_DEFAULT_LLM_TEMPERATURE",
    )
    agent_default_llm_max_tokens: int = Field(
        default=500,
        validation_alias="AGENT_DEFAULT_LLM_MAX_TOKENS",
    )
    agent_default_llm_timeout_seconds: float = Field(
        default=18.0,
        validation_alias="AGENT_DEFAULT_LLM_TIMEOUT_SECONDS",
    )

    agent_memory_backend: str = Field(
        default="local",
        validation_alias="AGENT_MEMORY_BACKEND",
    )
    openviking_base_url: str = Field(
        default="http://openviking:1933",
        validation_alias="OPENVIKING_BASE_URL",
    )
    openviking_api_key: str = Field(
        default="",
        validation_alias="OPENVIKING_API_KEY",
    )
    openviking_agent_id: str = Field(
        default="prism-gateway-api",
        validation_alias="OPENVIKING_AGENT_ID",
    )
    openviking_timeout_seconds: float = Field(
        default=6.0,
        validation_alias="OPENVIKING_TIMEOUT_SECONDS",
    )
    openviking_retry_attempts: int = Field(
        default=2,
        validation_alias="OPENVIKING_RETRY_ATTEMPTS",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
