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

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_file(request: Request, project_id: str, file: UploadFile, 
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
        asset_project_id=project.id,
        asset_name=file_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_size=os.path.getsize(file_path),
    )

    asset_record = await asset_model.create_asset(asset_resource)

    return JSONResponse(
        content={"message": ResponseStatus.FILE_UPLOAD_SUCCESS.value,
                 "file_id": str(asset_record.id),
                 }
    )
     
@data_router.post("/process/{project_id}")
async def process_file(request: Request, project_id: str, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset
    file_id = process_request.file_id

    project_model = await ProjectModel.create_instance(request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id)
    
    asset_model = await AssetModel.create_instance(request.app.db_client)

    project_files_ids = {}

    if process_request.file_id:
        asset_record = await asset_model.get_asset_record_by_name(project.id, file_id)
        if not asset_record:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": ResponseStatus.FILE_NOT_FOUND.value}
            )
    
        project_files_ids = {
                    asset_record.id:asset_record.asset_name
        }
    else:
        project_assets = await asset_model.get_all_assets(project.id, AssetTypeEnum.FILE.value)
        project_files_ids = {
                    record.id:record.asset_name 
                    for record in project_assets
                    }

    if not project_files_ids or len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": ResponseStatus.NO_FILES_TO_PROCESS.value}
        )

    process_controller = ProcessController(project_id)

    num_records = 0
    num_files = 0

    chunk_model = await ChunkModel.create_instance(request.app.db_client)

    if do_reset:
            await chunk_model.delete_chunks_by_project_id(project.id)
            return JSONResponse(
                content={
                    "message": ResponseStatus.FILE_PROCESSING_RESET.value,
                    "num_chunks": 0,
                }
            )
    for asset_id, file_id in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id)

        if file_content is None:
            logger.error(f"Failed to load content for file: {file_id} in project: {project_id}")
            continue

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
                chunk_project_id=project.id,
                chunk_assets_id=asset_id
            )
            for i, chunk in enumerate(file_chunks)
            ]
        
        num_records += await chunk_model.insert_multiple_chunks(file_chunks)
        num_files += 1

    return JSONResponse(
        content={
                "message": ResponseStatus.FILE_PROCESSING_SUCCESS.value,
                "inserted_chunks": num_records,
                "processed_files": num_files
            }
    )
