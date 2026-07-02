import os


class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8081"))
    # slowapi 限流规则，格式见 https://slowapi.readthedocs.io（如 "10/minute"）
    rate_limit: str = os.getenv("RATE_LIMIT", "10/minute")


settings = Settings()
