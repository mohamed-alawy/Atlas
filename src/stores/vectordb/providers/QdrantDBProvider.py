from qdrant_client import QdrantClient, models
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
from models.db_schemas import RetrievedDocument
from typing import List
import logging


class QdrantDBProvider(VectorDBInterface):
    def __init__(self, db_client, default_vector_size: int=786,
                 distance_method: str = None,
                 index_type: str = None, index_threshold: int = 100):
        
        self.client = None
        self.db_client = db_client
        self.distance_method = None
        self.default_vector_size = default_vector_size
        

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger("uvicorn")

    async def connect(self):
        self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        self.client = None

    async def is_collection_exists(self, collection_name: str) -> bool:
        return await self.client.collection_exists(collection_name=collection_name)

    async def list_all_collections(self) -> List:
        return await self.client.get_collections()

    async def get_collection_info(self, collection_name: str) -> dict:
        return await self.client.get_collection(collection_name=collection_name)

    async def delete_collection(self, collection_name: str):
        if await self.is_collection_exists(collection_name=collection_name):
            self.logger.info(f"Deleting Qdrant collection: {collection_name}")
            return await self.client.delete_collection(collection_name=collection_name)

    async def create_collection(self, collection_name: str, 
                                embedding_size: int, 
                                do_reset: bool = False):
        if do_reset and await self.is_collection_exists(collection_name=collection_name):
            _ = await self.delete_collection(collection_name=collection_name)

        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.info(f"Creating Qdrant collection: {collection_name}")
            
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method
                )
            )
            return True
        return False

    async def insert_one(self, collection_name: str,text: str, vector: List, 
                         metadata: dict = None, 
                         record_id: str = None):

        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False
        
        try:
            # Use upsert with PointStruct to insert a single point
            _ = await self.client.upsert(
                collection_name=collection_name,
                points=[models.PointStruct(
                    id=record_id,
                    vector=vector,
                    payload={"text": text, "metadata": metadata}
                )]
            )

        except Exception as e:
            self.logger.error(f"Error inserting record: {e}")
            return False

        return True

    async def insert_many(self, collection_name: str,texts: List, vectors: List, 
                          metadatas: List = None, 
                          record_ids: List = None,
                          batch_size: int = 50):

        if metadatas is None:
            metadatas = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))
        
        if record_ids is None:
            record_ids = [None] * len(texts)

        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False

        for i in range(0, len(texts), batch_size):
            batch_end  = i + batch_size
            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            points = [
                models.PointStruct(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={"text": batch_texts[x], "metadata": batch_metadatas[x]}
                ) for x in range(len(batch_texts))
            ]

            try:
                _ = await self.client.upsert(
                    collection_name=collection_name,
                    points=points
                )
            except Exception as e:
                self.logger.error(f"Error inserting batch starting at index {i}: {e}")
                return False

        return True

    async def search_by_vector(self, collection_name: str, vector: List, limit: int = 5):

        results = await self.client.query_points(
                      collection_name, 
                      vector, 
                      limit=limit
                    )
        
        if not results or len(results.points) == 0:
            return None
        
        return [
            RetrievedDocument(**{
                "text": point.payload.get("text", ""),
                "score": point.score
            }) for point in results.points
        ]
                                            
