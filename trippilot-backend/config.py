from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 用绝对路径，保证不管从哪个目录启动（uvicorn / pytest / 脚本）都能读到配置
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    DATABASE_URL: str
    AMAP_API_KEY: str
    LLM_API_KEY: str
    LLM_BASE_URL: str
    # 登录 token 的签名密钥，生产环境请在 .env.local 里改成随机值
    AUTH_SECRET: str = "trippilot-dev-secret-change-me"

    model_config = SettingsConfigDict(
        # 先读 .env（可提交的公共默认值），再用 .env.local 覆盖（本地真实密钥，不进 git）
        env_file=(BASE_DIR / ".env", BASE_DIR / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
