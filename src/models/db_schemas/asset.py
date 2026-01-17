from pydantic import BaseModel, Field, validator
from typing import Optional
from bson.objectid import ObjectId
from datetime import datetime

class Asset(BaseModel):

    id: Optional[ObjectId] = Field(None, alias="_id")
    asset_project_id: ObjectId
    asset_name: str = Field(..., min_length=1)
    asset_type: str = Field(..., min_length=1)
    asset_size: int = Field(gt=0, default=None)
    asset_config: dict = Field(default=None)
    asset_push_date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def get_indexes(cls):
        return [
                {
                    "key" : [
                        ("asset_project_id", 1)
                        ],
                    "name": "asset_project_id_index",
                    "unique": True
                },
                {
                    "key" : [
                        ("asset_name", 1),
                        ("asset_project_id", 1)
                        ],
                    "name": "asset_name_project_id_index",
                    "unique": True
                }
            ]