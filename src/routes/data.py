from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from helpers import get_settings, settings
from controllers import DataController, ProcessController
import aiofiles
from models import ResponseStatus
import logging
from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.db_schemas import DataChunk
from models.ChunkModel import ChunkModel

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_file(request: Request, project_id: str, file: UploadFile, 
                      app_settings : settings = Depends(get_settings)):
 
    project_model = ProjectModel(request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id)

    # validate file
    dataController = DataController()

    is_valid, message = dataController.validate_upload_file(file)
    
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": message}
        )

    file_path, file_id = dataController.generate_unique_file_path(file.filename, project_id)

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while content := await file.read(app_settings.FILE_CHUNK_SIZE):
                await f.write(content)
    except Exception as e:
        
        logger.error(f"File upload failed: {e}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": ResponseStatus.FILE_UPLOAD_FAILED.value}
        )
    
    return JSONResponse(
        content={"message": ResponseStatus.FILE_UPLOAD_SUCCESS.value,
                 "file_id": file_id,
                 }
    )
     
@data_router.post("/process/{project_id}")
async def process_file(request: Request, project_id: str, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset
    file_id = process_request.file_id

    project_model = ProjectModel(request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id)

    process_controller = ProcessController(project_id)

    file_content = process_controller.get_file_content(file_id)

    file_chunks = process_controller.process_file_content(
        file_content=file_content,
        chunk_size=chunk_size,
        chunk_overlap=overlap_size
    )

    if file_chunks is None or len(file_chunks) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": ResponseStatus.FILE_PROCESSING_FAILED.value}
        )
    
    file_chunks = [
        DataChunk(
            chunk_text=chunk.page_content,
            chunk_metadata=chunk.metadata,
            chunk_order=i+1,
            chunk_project_id=project.id
        )
        for i, chunk in enumerate(file_chunks)
        ]
    
    chunk_model = ChunkModel(request.app.db_client)

    if do_reset:
        await chunk_model.delete_chunks_by_project_id(project.id)
        return JSONResponse(
            content={"message": ResponseStatus.FILE_PROCESSING_RESET.value,
                     "num_chunks": 0,
                     }
        )

    num_records = await chunk_model.insert_multiple_chunks(file_chunks)

    return JSONResponse(
        content={"message": ResponseStatus.FILE_PROCESSING_SUCCESS.value,
                 "num_chunks": num_records,
                 }
    )
