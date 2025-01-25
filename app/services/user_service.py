from app.db.mongodb import MongoDB
from bson import ObjectId
from typing import Optional, Dict, List

class UserService:
    @staticmethod
    async def get_user_data(user_id: str) -> Optional[Dict]:
        """Retrieve user data from MongoDB."""
        try:
            db = MongoDB.get_db()
            # First try to find the user by ObjectId
            query = {"_id": ObjectId(user_id)}
            user = db.users.find_one(query, {"password": 0})
            
            if user:
                return user
            
            # If not found, try finding by string ID
            query = {"_id": user_id}
            user = db.users.find_one(query, {"password": 0})
            
            return user
            
        except Exception as e:
            print(f"Error retrieving user data: {e}")
            return None
    
    @staticmethod
    async def get_user_data_from_all_collections(user_id: str) -> Optional[Dict]:
        """
        Retrieve user data from all collections in MongoDB by user ID.
        Searches through every collection for the user data.
        """
        try:
            db = MongoDB.get_db()
            all_user_data = {}
            
            for collection_name in db.list_collection_names():
                try:
                    # Try ObjectId first
                    query = {"_id": ObjectId(user_id)}
                    data = db[collection_name].find_one(query, {"password": 0})
                    if data:
                        all_user_data[collection_name] = data
                except:
                    # Try string ID
                    query = {"_id": user_id}
                    data = db[collection_name].find_one(query, {"password": 0})
                    if data:
                        all_user_data[collection_name] = data
                        
                # Also search for any documents referencing this user ID in other fields
                ref_query = {"user_id": user_id}
                ref_data = list(db[collection_name].find(ref_query, {"password": 0}))
                if ref_data:
                    if collection_name not in all_user_data:
                        all_user_data[collection_name] = []
                    all_user_data[collection_name].extend(ref_data)
            
            return all_user_data if all_user_data else None
            
        except Exception as e:
            print(f"Error retrieving user data: {e}")
            return None
    
    @staticmethod
    async def list_sample_users(limit: int = 5) -> List[str]:
        """List sample user IDs from the database."""
        try:
            db = MongoDB.get_db()
            users = list(db.users.find({}, {"_id": 1}).limit(limit))
            return [str(user['_id']) for user in users]
        except Exception as e:
            print(f"Error listing users: {e}")
            return []
    
    @staticmethod
    async def validate_user_access(user_id: str) -> bool:
        """Validate user's access rights."""
        try:
            user = await UserService.get_user_data(user_id)
            return user is not None
        except Exception as e:
            print(f"Validation error: {e}")
            return False 