from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LogMind"
    data_dir: str = "./data"
    use_sentence_transformers: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    use_chroma: bool = False
    chroma_dir: str = "./data/chroma"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
