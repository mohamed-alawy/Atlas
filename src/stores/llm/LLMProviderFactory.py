from .LLMEnums import LLMEnums
from .providers import CoHereProvider, OpenAIProvider

class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config

    def create(self, provider: str):
        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                base_url=self.config.OPENAI_BASE_URL,
                defult_input_token=self.config.INPUT_MAX_TOKEN,
                defult_generation_output_token=self.config.GENERATION_MAX_TOKEN,
                defult_generation_temperature=self.config.GENERATION_TEMPERATURE
            )

        if provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key=self.config.COHERE_API_KEY,
                defult_input_token=self.config.INPUT_MAX_TOKEN,
                defult_generation_output_token=self.config.GENERATION_MAX_TOKEN,
                defult_generation_temperature=self.config.GENERATION_TEMPERATURE
                
                )
    
        return None