from helpers import get_settings, settings

class BaseDataModel:
    def __init__(self, db_client):
        self.db_client = db_client
        self.app_settings = get_settings()