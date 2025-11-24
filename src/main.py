from fastapi import FastAPI
from routes import base, data
from helpers import get_settings
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    settings = get_settings()
    
    app.mongo_connection = AsyncIOMotorClient(settings.MONGO_URI)
    app.db_client = app.mongo_connection[settings.MONGO_DATABASE]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongo_connection.close()

app.include_router(base.base_router)
app.include_router(data.data_router)