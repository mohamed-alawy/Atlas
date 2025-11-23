from .BaseController import BaseController
from .FileController import FileController
from fastapi import UploadFile
from models import ResponseStatus
import regex as re
import os

class DataController(BaseController):
    
    def __init__(self):
        super().__init__()

    def validate_upload_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseStatus.FILE_TYPE_NOT_ALLOWED.value
        
        if file.size > self.app_settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            return False, ResponseStatus.FILE_SIZE_EXCEEDED.value
        
        return True, ResponseStatus.FILE_VALID.value
    
    def generate_unique_file_path(self, original_filename: str, file_id: str):
        
        random_name = self.generate_random_string()
        file_path = FileController().get_file_path(file_id)
        cleaned_filename = self.get_cleaned_filename(original_filename)

        new_file_path = os.path.join(file_path, f"{random_name}_{cleaned_filename}")
        while os.path.exists(new_file_path):
            random_name = self.generate_random_string()
            new_file_path = os.path.join(file_path, f"{random_name}_{cleaned_filename}")
        return new_file_path, random_name+"_"+cleaned_filename
    
    def get_cleaned_filename(self, original_filename: str):
        # Remove special characters and spaces
        cleaned_filename = re.sub(r'[^\w\.-]', '_', original_filename.strip())
        cleaned_filename = cleaned_filename.replace(' ', '_').lower()
        return cleaned_filename