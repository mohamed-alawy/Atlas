from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingStatus

class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_file_path(project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]
    
    def get_file_loader(self, file_id: str):

        file_extension = self.get_file_extension(file_id).lower()
        file_path = os.path.join(self.project_path, file_id)

        if file_extension == ProcessingStatus.TXT.value:
            return TextLoader(file_path, encoding='utf-8')
        elif file_extension == ProcessingStatus.PDF.value:
            return PyMuPDFLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id)
        return loader.load()
    
    def process_file_content(self,file_content: list,
                             chunk_size: int = 100, 
                             chunk_overlap: int = 20):
   
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )

        file_content_text = [doc.page_content for doc in file_content]
        file_content_metadata = [doc.metadata for doc in file_content]

        chunks = text_splitter.create_documents(
            file_content_text,
            metadatas=file_content_metadata
        )

        return chunks
