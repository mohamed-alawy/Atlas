from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers import get_settings, settings
from controllers import DataController
import aiofiles
from models import ResponseStatus
import logging

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{file_id}")
async def upload_file(file_id: str, file: UploadFile, 
                      app_settings : settings = Depends(get_settings)):

    # validate file
    dataController = DataController()

    is_valid, message = dataController.validate_upload_file(file)
    
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": message}
        )

    file_path, file_id = dataController.generate_unique_file_path(file.filename, file_id)

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
     

