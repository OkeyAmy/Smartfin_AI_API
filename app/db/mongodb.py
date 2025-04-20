from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from app.core.config import settings

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls, uri: str = None):
        """Connect to MongoDB with provided URI or from settings."""
        if cls.client is not None:
            return
            
        mongo_uri = uri or settings.MONGODB_URI
        db_name = settings.MONGODB_DB_NAME
        
        cls.client = AsyncIOMotorClient(mongo_uri)
        cls.db = cls.client[db_name]
        
        # Test connection
        await cls.client.admin.command('ping')
        print(f"Connected to MongoDB: {db_name}")
        
        return cls.client
    
    @classmethod
    async def close(cls):
        """Close the MongoDB connection."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get MongoDB client instance."""
        if cls.client is None:
            raise Exception("MongoDB connection not established")
        return cls.client
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get MongoDB database instance."""
        if cls.db is None:
            raise Exception("MongoDB connection not established")
        return cls.db 