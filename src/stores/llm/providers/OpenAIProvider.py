from ..LLMInterface import LLMInterface
from openai import OpenAI
import logging
from ..LLMEnums import OpenAIEnums

class OpenAIProvider(LLMInterface):
    def __init__(self, api_key: str, base_url: str = None,
                 defult_input_token: int = 1000,
                 defult_generation_output_token: int = 1000,
                 defult_generation_temperature: float = 0.1):
        
        self.api_key = api_key
        self.base_url = base_url

        self.defult_input_token = defult_input_token
        self.defult_generation_output_token = defult_generation_output_token
        self.defult_generation_temperature = defult_generation_temperature
        
        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id
        self.logger.info(f"Generation model set to {model_id}")

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(f"Embedding model set to {model_id} with size {embedding_size}")

    def get_proccessed_text(self, text: str):
        return text[:self.defult_input_token].strip()
    
    def generate_text(self, prompt: str,chat_history: list = [], max_output_tokens: int = None, temperature: float = None):
        if not self.client:
            raise ValueError("OpenAI client is not initialized.")
            return None
        
        if not self.generation_model_id:
            raise ValueError("Generation model is not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.defult_generation_output_token
        temperature = temperature if temperature is not None else self.defult_generation_temperature

        chat_history.append(self.construct_prompt(prompt, OpenAIEnums.USER.value))

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature
        )
        
        if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
            self.logger.error("No response received from OpenAI.")
            return None
        
        return response.choices[0].message.content
    
       
    def embed_text(self, text: str, document_type: str = None):
        if not self.client:
            raise ValueError("OpenAI client is not initialized.")
            return None
        
        if not self.embedding_model_id:
            raise ValueError("Embedding model is not set.")
            return None
        
        response = self.client.embeddings.create(
            input=self.get_proccessed_text(text),
            model=self.embedding_model_id
        )

        if not response or len(response.data) == 0 or not response.data[0].embedding:
            self.logger.error("No embedding data received from OpenAI.")
            return None
        
        return response.data[0].embedding
    
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.get_proccessed_text(prompt)
        }

        
        