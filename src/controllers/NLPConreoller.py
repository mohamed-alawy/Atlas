from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnums
from typing import List
import json

class NLPController(BaseController):
    def __init__(self, vector_db_client, generation_client, embedding_client, template_parser):
        super().__init__()
        self.vector_db_client = vector_db_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
    
    def create_collection_name(self, project_id: str):
        return f"collection_{project_id}".strip()
    
    def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id = project.project_id)
        return self.vector_db_client.delete_collection(collection_name)
    
    def get_vector_db_collections_info(self, project: Project):
        collection_name = self.create_collection_name(project_id = project.project_id)
        collection_info = self.vector_db_client.get_collection_info(collection_name)

        return json.loads(json.dumps(collection_info, default=lambda x: x.__dict__))

    def index_into_vector_db(self, project: Project, chunks: List[DataChunk], 
                                chunk_ids: List[int],
                                do_reset: bool = False):
        # get collection name       
        collection_name = self.create_collection_name(project_id = project.project_id)
        
        # mange items to be indexed
        texts = [chunk.chunk_text for chunk in chunks]
        metadata = [chunk.chunk_metadata for chunk in chunks]
        vectors = [
            self.embedding_client.embed_text(text=txt, 
                                             document_type=DocumentTypeEnums.DOCUMENT.value) 
            for txt in texts
        ]

        # create collection if not exists
        _ = self.vector_db_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )

        # insert items into collection
        _ = self.vector_db_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            vectors=vectors,
            metadatas=metadata,
            record_ids=chunk_ids
        )

        return True

    def search_vector_db_collection(self, project: Project, text: str, limit: int =5):
        collection_name = self.create_collection_name(project_id = project.project_id)
        
        # get embedding for the query text
        vector = self.embedding_client.embed_text(
            text=text, 
            document_type=DocumentTypeEnums.QUERY.value
        )

        # perform search in vector db
        if not vector or len(vector) == 0:
            return False
        
        results = self.vector_db_client.search_by_vector(
            collection_name=collection_name,
            vector=vector,
            limit=limit
        )

        if not results:
            return False
        
        return results
    
    def answer_rag_query(self, project: Project, query: str, limit: int =5  ):

        answer, full_prompt, chat_history = None, None, None

        # retrieve relevant documents from vector db
        retrieved_docs = self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit
        )

        if not retrieved_docs or len(retrieved_docs) == 0:
            return answer, full_prompt, chat_history
        
        # construct llm prompt
        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompt = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                "doc_index" : idx + 1,
                "chunk_text": doc.text
            }) for idx, doc in enumerate(retrieved_docs)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt", {
            "query": query
        })

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt, 
                role=self.generation_client.enums.SYSTEM.value
                )
        ]

        full_prompt = "\n\n".join([
            documents_prompt,
            footer_prompt,
        ])

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

        return answer, full_prompt, chat_history



        

