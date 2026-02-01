from pydantic_settings import BaseSettings
from typing import List

class settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    MAX_FILE_SIZE_MB: int
    FILE_CHUNK_SIZE: int
    
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DB: str
    
    GENERATION_BACKEND_LITRAL: List[str]
    GENERATION_BACKEND: str  
    EMBEDDING_BACKEND: str  

    OPENAI_API_KEY: str = None
    OPENAI_BASE_URL: str = None
    COHERE_API_KEY: str = None

    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None

    INPUT_MAX_TOKEN: int = None
    GENERATION_MAX_TOKEN: int = None
    GENERATION_TEMPERATURE: float = None

    VECTOR_DB_BACKEND_LITRAL: List[str]
    VECTOR_DB_BACKEND: str 
    VECTOR_DB_PATH: str 
    VECTOR_DB_DISTANCE_METHOD: str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100
    
    PRIMARY_LANGUAGE: str = "en"
    DEFAULT_LANGUAGE: str = "en"

    class Config:
        env_file = ".env"

def get_settings():
    return settings()