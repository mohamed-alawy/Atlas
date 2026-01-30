from .BaseDataModel import BaseDataModel
from .db_schemas import Project
from .enums.DataBaseEnum import DataBaaseEnum

class ProjectModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaaseEnum.CLLECTION_PROJECTS_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.initialize_collection()
        return instance

    async def initialize_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaaseEnum.CLLECTION_PROJECTS_NAME.value not in all_collections:
            await self.db_client.create_collection(DataBaaseEnum.CLLECTION_PROJECTS_NAME.value)

        # Always ensure indexes exist (idempotent) — previously indexes were only created when the
        # collection was newly created, so existing collections could miss required indexes.
        indexes = Project.get_indexes()
        for index in indexes:
            await self.collection.create_index(index["key"], name=index["name"], unique=index["unique"])

    async def create_project(self, project: Project):
        result = await self.collection.insert_one(project.dict(by_alias=True, exclude_unset=True))
        project.project_id = result.inserted_id
        return project
    
    async def get_project_or_create_one(self, project_id: str):
        record = await self.collection.find_one({
            "project_id": project_id
            })
        
        if record is None:
            project = Project(project_id=project_id)
            project = await self.create_project(project)
            
            return project
        
        return Project(**record)
    
    async def get_all_projects(self, page: int = 1, page_size: int = 10):
        
        total_docs = await self.collection.count_documents({})

        total_pages = total_docs  // page_size
        if total_docs % page_size > 0:
            total_pages += 1

        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)
        
        projects=[]
        async for document in cursor:
            projects.append(Project(**document))

        return projects, total_pages