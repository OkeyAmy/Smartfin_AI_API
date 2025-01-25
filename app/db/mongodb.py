from pymongo import MongoClient
from pymongo.server_api import ServerApi
from app.core.config import settings
from typing import Optional

class MongoDB:
    client: Optional[MongoClient] = None
    
    @classmethod
    def get_client(cls) -> MongoClient:
        if cls.client is None:
            cls.client = MongoClient(settings.MONGODB_URI, server_api=ServerApi('1'))
            # Test connection
            try:
                cls.client.admin.command('ping')
                print("Successfully connected to MongoDB!")
            except Exception as e:
                print(f"MongoDB connection error: {e}")
                raise e
        return cls.client
    
    @classmethod
    def get_db(cls):
        client = cls.get_client()
        return client[settings.MONGODB_DB_NAME]
    
    @classmethod
    def close_connection(cls):
        if cls.client:
            cls.client.close()
            cls.client = None 