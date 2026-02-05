from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from helpers import get_settings, settings
from controllers import DataController, ProcessController
import aiofiles
import os
from models import ResponseStatus, AssetTypeEnum
import logging
from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.AssetModel import AssetModel
from models.db_schemas import DataChunk, Asset
from models.ChunkModel import ChunkModel
from controllers import NLPController
from tasks.file_processing import process_project_files
from tasks.process_workflow import process_and_push_workflow

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_file(request: Request, project_id: int, file: UploadFile, 
                      app_settings : settings = Depends(get_settings)):
 
    project_model = await ProjectModel.create_instance(request.app.db_client)
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
    
    asset_model = await AssetModel.create_instance(request.app.db_client)
    
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_name=file_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_size=os.path.getsize(file_path),
    )

    asset_record = await asset_model.create_asset(asset_resource)

    return JSONResponse(
        content={"message": ResponseStatus.FILE_UPLOAD_SUCCESS.value,
                 "file_id": str(asset_record.asset_id),
                 }
    )

@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    task = process_project_files.delay(
        project_id=project_id,
        file_id=process_request.file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset,
    )

    return JSONResponse(
        content={
            "signal": ResponseStatus.FILE_PROCESSING_SUCCESS.value,
            "task_id": task.id
        }
    )
  
@data_router.post("/process-and-push/{project_id}")
async def process_and_push_endpoint(request: Request, project_id: int, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    workflow_task = process_and_push_workflow.delay(
        project_id=project_id,
        file_id=process_request.file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset
    )

    return JSONResponse(
        content={
            "message": ResponseStatus.PROCESS_AND_PUSH_WORKFLOW_STARTED.value,
            "task_id": workflow_task.id
        }
    )