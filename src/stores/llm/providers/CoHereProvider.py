from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnums
import logging
import cohere

class CoHereProvider(LLMInterface):
    def __init__(self, api_key: str,
                 defult_input_token: int = 1000,
                 defult_generation_output_token: int = 1000,
                 defult_generation_temperature: float = 0.1):
        
        self.api_key = api_key

        self.defult_input_token = defult_input_token
        self.defult_generation_output_token = defult_generation_output_token
        self.defult_generation_temperature = defult_generation_temperature
        
        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = cohere.Client(self.api_key)

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def get_proccessed_text(self, text: str):
        return text[:self.defult_input_token].strip()
    
    def generate_text(self, prompt: str,chat_history: list = [], max_output_tokens: int = None, temperature: float = None):
        if not self.client:
            raise ValueError("Cohere client is not initialized.")
            return None
        
        if not self.generation_model_id:
            raise ValueError("Generation model is not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.defult_generation_output_token
        temperature = temperature if temperature is not None else self.defult_generation_temperature

        chat_history.append(self.construct_prompt(prompt, CoHereEnums.USER.value))

        response = self.client.generate(
            model=self.generation_model_id,
            prompt=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature
        )

        if not response or not response.text:
            self.logger.error("Invalid response from Cohere API.")
            return None
        
        return response.text
    
    def embed_text(self, text: str, document_type: str = None):
        if not self.client:
            raise ValueError("Cohere client is not initialized.")
            return None
        
        if not self.embedding_model_id:
            raise ValueError("Embedding model is not set.")
            return None
        
        input_type = CoHereEnums.DOCUMENT.value 
        if document_type == DocumentTypeEnums.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        response = self.client.embed(
            texts=[self.get_proccessed_text(text)],
            model=self.embedding_model_id,
            input_type=input_type,
            embedding_types=["float"]
        )

        if not response or not response.embeddings or not response.embeddings.float:
            self.logger.error("Invalid embedding response from Cohere API.")
            return None
        
        return response.embeddings.float[0]
    
    def construct_prompt(self, prompt, role):
        return {
            "role": role, 
            "content": self.get_proccessed_text(prompt)
        }