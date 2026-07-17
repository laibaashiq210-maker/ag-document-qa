"""
Central configuration for the RAG backend.
Uses pydantic-settings so every value can be overridden via a .env file
or real environment variables, without touching code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4

    chroma_persist_dir: str = "./chroma_db"
    upload_dir: str = "./uploaded_docs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single shared settings instance, imported everywhere else.
settings = Settings()
