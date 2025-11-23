from .BaseController import BaseController
import os

class FileController(BaseController):
    
    def __init__(self):
        super().__init__()

    def get_file_path(self, project_id: str):
        project_path = os.path.join(self.files_dir, project_id)

        if not os.path.exists(project_path):
            os.makedirs(project_path)

        return project_path