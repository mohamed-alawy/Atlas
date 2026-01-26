from fastapi import FastAPI
from routes import base, data, nlp
from helpers import get_settings
from motor.motor_asyncio import AsyncIOMotorClient
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory

app = FastAPI()

async def startup_span():
    settings = get_settings()
    app.mongo_connection = AsyncIOMotorClient(settings.MONGO_URI)
    app.db_client = app.mongo_connection[settings.MONGO_DATABASE]

    llm_provider_factory = LLMProviderFactory(config=settings)
    vectordb_provider_factory = VectorDBProviderFactory(config=settings)

    # Initialize LLM providers
    app.generation_client = llm_provider_factory.create(settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    app.embedding_client = llm_provider_factory.create(settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                             embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    # Initialize VectorDB providers
    app.vector_db_client = vectordb_provider_factory.create(settings.VECTOR_DB_BACKEND)
    app.vector_db_client.connect()

async def shutdown_span():
    app.mongo_connection.close()
    app.vector_db_client.disconnect()

# app.router.lifespan.on_startup.append(startup_span)
# app.router.lifespan.on_shutdown.append(shutdown_span)

app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)