from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (PgVectorDistanceMethodEnums, PgVectorTableSchemaEnums,
                             PgVectorIndexTypeEnums, DistanceMethodEnums)
from models.db_schemas import RetrievedDocument
from typing import List
import logging
from sqlalchemy.sql import text as sql_text
from sqlalchemy.exc import IntegrityError
import json

class PGVectorProvider(VectorDBInterface):
    def __init__(self, db_client, default_vector_size: int=786,
                 distance_method: str = None,
                 index_type: str = None, index_threshold: int = 100):
        
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_type = index_type
        self.index_threshold = index_threshold

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = PgVectorDistanceMethodEnums.DOT.value

        self.pgvector_table_prefix = PgVectorTableSchemaEnums._PREFIX.value
        
        self.logger = logging.getLogger("uvicorn")

        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"
    
    async def connect(self):
        async with self.db_client() as session:
            try:
                # Check if vector extension already exists
                result = await session.execute(sql_text(
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                ))
                extension_exists = result.scalar_one_or_none()
                
                if not extension_exists:
                    # Only create if it doesn't exist
                    await session.execute(sql_text("CREATE EXTENSION vector"))
                    await session.commit()
            except Exception as e:
                # If extension already exists or any other error, just log and continue
                self.logger.warning(f"Vector extension setup: {str(e)}")
                await session.rollback()

    async def disconnect(self):
        pass

    async def is_collection_exists(self, collection_name: str) -> bool:
        record = None
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(sql_text(
                    f"SELECT * FROM pg_tables WHERE tablename = '{collection_name}';"
                ))
                record = result.scalar_one_or_none()
        return record is not None

    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(sql_text(
                    f"SELECT tablename FROM pg_tables WHERE tablename LIKE '{self.pgvector_table_prefix}'"
                ))
                records = result.scalars().all()
        return records
    
    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text(f'''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE tablename = '{collection_name}';
                ''')

                counters_sql = sql_text(f'''
                    SELECT COUNT(*) FROM {collection_name};
                ''')

                table_info = await session.execute(table_info_sql)
                record_count = await session.execute(counters_sql)

                table_data = table_info.fetchone()
                record_count = record_count.scalar_one()

                if not table_data:
                    return None
                
                return {
                    "table_info": {
                        "schemaname": table_data[0],
                        "tablename": table_data[1],
                        "tableowner": table_data[2],
                        "tablespace": table_data[3],
                        "hasindexes": table_data[4]
                    },
                    "record_count": record_count
                }
            
    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Dropping table {collection_name}...")
                await session.execute(sql_text(
                    f"DROP TABLE IF EXISTS {collection_name};"
                ))
                await session.commit()
        return True
    
    async def create_collection(self, collection_name: str, 
                                embedding_size: int = None, 
                                do_reset: bool = False):
        
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)

        if embedding_size is None:
            embedding_size = self.default_vector_size

        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.info(f"Creating table {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_table_sql = sql_text(f'''
                        CREATE TABLE {collection_name} (
                            {PgVectorTableSchemaEnums.ID.value} bigserial PRIMARY KEY,
                            {PgVectorTableSchemaEnums.TEXT.value} text,
                            {PgVectorTableSchemaEnums.VECTOR.value} vector({embedding_size}),
                            {PgVectorTableSchemaEnums.METADATA.value} jsonb DEFAULT \'{{}}\',
                            {PgVectorTableSchemaEnums.CHUNK_ID.value} integer,
                            FOREIGN KEY ({PgVectorTableSchemaEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)
                        );
                    ''')
                    await session.execute(create_table_sql)
                    await session.commit()
            return True
        return False
    
    async def is_index_exists(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                check_index_sql = sql_text(f'''
                    SELECT 1
                    FROM pg_indexes
                    WHERE tablename = '{collection_name}'
                    AND indexname = '{index_name}';
                ''')
                result = await session.execute(check_index_sql)
                return bool(result.scalar_one_or_none())
            
    async def create_vector_index(self, collection_name: str, 
                                  index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        is_index_existed = await self.is_index_exists(collection_name=collection_name)
        if is_index_existed:
            return False  

        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f'''
                    SELECT COUNT(*) FROM {collection_name};
                ''')
                result = await session.execute(count_sql)
                record_count = result.scalar_one()

                if record_count < self.index_threshold:
                    return False
                
                self.logger.info(f"Creating index for collection {collection_name}...")

                index_name = self.default_index_name(collection_name)
                create_index_sql = sql_text(f'''
                    CREATE INDEX {index_name}
                    ON {collection_name}
                    USING {index_type} ({PgVectorTableSchemaEnums.VECTOR.value} {self.distance_method});
                ''')
                await session.execute(create_index_sql)

                self.logger.info(f"Ending index creation for collection {collection_name}...")

    async def reset_vector_index(self, collection_name: str,
                                    index_type: str = PgVectorIndexTypeEnums.HNSW.value):
            index_name = self.default_index_name(collection_name)
            async with self.db_client() as session:
                async with session.begin():
                    drop_index_sql = sql_text(f'''
                        DROP INDEX IF EXISTS {index_name};
                    ''')
                    await session.execute(drop_index_sql)

            return await self.create_vector_index(collection_name=collection_name,
                                                    index_type=index_type)
    
    async def insert_one(self, collection_name: str,text: str, vector: list, 
                         metadata: dict = None, 
                         record_id: str = None):

        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False
        
        if record_id is None:
            self.logger.error(f"record_id must be provided for PGVectorProvider.")
            return False

        async with self.db_client() as session:
            async with session.begin():
                insert_sql = sql_text(f'''
                    INSERT INTO {collection_name} 
                    ({PgVectorTableSchemaEnums.TEXT.value}, 
                     {PgVectorTableSchemaEnums.VECTOR.value}, 
                     {PgVectorTableSchemaEnums.METADATA.value}, 
                     {PgVectorTableSchemaEnums.CHUNK_ID.value})
                    VALUES (:text, :vector, :metadata, :chunk_id);
                ''')

                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_sql, {
                    "text": text,
                    "vector": '[' + ','.join([str(v) for v in vector]) + ']',
                    "metadata": metadata_json,
                    "chunk_id": record_id
                })
                await session.commit()
                
                await self.create_vector_index(collection_name=collection_name)

        return True
                
    async def insert_many(self, collection_name: str,texts: list, vectors: list, 
                          metadatas: list = None, record_ids: list = None,
                          batch_size: int = 50):
        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False

        if len(vectors) != len(record_ids):
            self.logger.error(f"Length of vectors and record_ids must be the same.")
            return False
        
        if not metadatas or len(metadatas) == 0:
            metadatas = [None] * len(texts)
        
        if record_ids is None:
            record_ids = list(range(0, len(texts)))
        
        if record_ids is None:
            record_ids = [None] * len(texts)

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i+batch_size]
                    batch_metadatas = metadatas[i:i+batch_size] 
                    batch_record_ids = record_ids[i:i+batch_size]

                    values = []

                    for _text, _vector, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadatas, batch_record_ids):
                        
                        matadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"
                        values.append({
                            "text": _text,
                            "vector": '[' + ','.join([str(v) for v in _vector]) + ']',
                            "metadata": matadata_json,
                            "chunk_id": _record_id
                        })

                    batch_insert_sql = sql_text(f'''
                        INSERT INTO {collection_name} 
                        ({PgVectorTableSchemaEnums.TEXT.value}, 
                         {PgVectorTableSchemaEnums.VECTOR.value}, 
                         {PgVectorTableSchemaEnums.METADATA.value}, 
                         {PgVectorTableSchemaEnums.CHUNK_ID.value})
                        VALUES (:text, :vector, :metadata, :chunk_id);
                        ''')
                    await session.execute(batch_insert_sql, values)
                
        await self.create_vector_index(collection_name=collection_name)
        
        return True
    
    async def search_by_vector(self, collection_name: str,vector: list, limit: int) -> List[RetrievedDocument]:
        if not await self.is_collection_exists(collection_name=collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False
        
        vector = '[' + ','.join([str(v) for v in vector]) + ']'
        async with self.db_client() as session:
            async with session.begin():
                search_sql = sql_text(f'''
                    SELECT 
                        {PgVectorTableSchemaEnums.TEXT.value} as text,
                        1 - ({PgVectorTableSchemaEnums.VECTOR.value} <=> :vector) as score
                    FROM {collection_name}
                    ORDER BY score DESC
                    LIMIT {limit};
                ''')
                result = await session.execute(search_sql, {"vector": vector})
                records = result.fetchall()
                
                return [
                    RetrievedDocument(
                        text=record.text,
                        score=record.score
                    ) for record in records
                ]