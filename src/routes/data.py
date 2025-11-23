from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers import get_settings, settings
from controllers import DataController, ProcessController
import aiofiles
from models import ResponseStatus
import logging
from .schemas.data import ProcessRequest

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_file(project_id: str, file: UploadFile, 
                      app_settings : settings = Depends(get_settings)):

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
                 "file_id": file_id}
    )
     
@data_router.post("/process/{project_id}")
async def process_file(project_id: str, process_request: ProcessRequest):
    
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset
    file_id = process_request.file_id

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
    
    return JSONResponse(
        content={"message": ResponseStatus.FILE_PROCESSING_SUCCESS.value,
                 "num_chunks": len(file_chunks)}
    )