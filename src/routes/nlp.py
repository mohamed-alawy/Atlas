from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from routes.schemas.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import ResponseStatus
import logging

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):

    project_model = await ProjectModel.create_instance(request.app.db_client)
    
    chunk_model = await ChunkModel.create_instance(request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": ResponseStatus.PROJECT_NOT_FOUND.value}
        )
    
    nlp_controller = NLPController(
        vector_db_client=request.app.vector_db_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )

    has_record = True
    page_no = 1
    inserted_count = 0
    idx = 0

    while has_record:
        page_chunks = await chunk_model.get_project_chunks(project_id=project.id, page_no=page_no)

        if len(page_chunks):
            page_no += 1
            
        if not page_chunks or len(page_chunks) == 0:
            has_record = False
            break

        chunks_ids = list(range(idx, idx + len(page_chunks)))
        idx += len(page_chunks)

        is_inserted = nlp_controller.index_into_vector_db(

            project=project,
            chunks=page_chunks,
            do_reset= push_request.do_reset,
            chunk_ids=chunks_ids
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseStatus.INSERT_INTO_VECTORDB_FAILED.value}
            )
        
        inserted_count += len(page_chunks)
        
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": ResponseStatus.INSERT_INTO_VECTORDB_SUCCESS.value, 
                 "inserted_count": inserted_count}
    )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):

    project_model = await ProjectModel.create_instance(request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id)
    
    nlp_controller = NLPController(
        vector_db_client=request.app.vector_db_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )

    collection_info = nlp_controller.get_vector_db_collections_info(project=project)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": ResponseStatus.VECTORDB_COLLECTION_RETURNED.value, 
                 "collection_info": collection_info}
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: str, search_request: SearchRequest):

    project_model = await ProjectModel.create_instance(request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id)
    
    nlp_controller = NLPController(
        vector_db_client=request.app.vector_db_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )

    results = nlp_controller.search_vector_db_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit
    )

    if not results:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": ResponseStatus.VECTORDB_SEARCH_ERROR.value}
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": ResponseStatus.VECTORDB_SEARCH_SUCCESS.value,
                "results": results}
    )
        
