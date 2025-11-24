from pydantic_settings import BaseSettings

class settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    GEMINI_API_KEY: str
    FILE_ALLOWED_TYPES: list
    MAX_FILE_SIZE_MB: int
    FILE_CHUNK_SIZE: int
    MONGO_URI: str
    MONGO_DATABASE: str
    
    class Config:
        env_file = ".env"

def get_settings():
    return settings()