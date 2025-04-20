from app.db.mongodb import MongoDB
from bson import ObjectId
from typing import Optional, Dict, List, Any

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
        Searches through every collection for the user data and builds a comprehensive
        financial profile for the user.
        """
        try:
            db = MongoDB.get_db()
            all_user_data = {}
            
            # Try to convert to ObjectId (for MongoDB _id fields)
            try:
                obj_id = ObjectId(user_id)
            except:
                obj_id = None
            
            # List of collections to search
            collections = await db.list_collection_names()
            
            # These collections are most likely to contain user financial data
            financial_collections = [
                'users', 'transactions', 'accounts', 'expenses_summary', 'products_services',
                'investments', 'loans', 'insurance', 'credit_cards', 'expense', 'products'
            ]
            
            # Prioritize financial collections
            prioritized_collections = [c for c in financial_collections if c in collections]
            other_collections = [c for c in collections if c not in financial_collections]
            
            # Search through prioritized collections first, then others
            for collection_name in prioritized_collections + other_collections:
                collection = db[collection_name]
                
                # Try with ObjectId
                if obj_id:
                    data = await collection.find_one({"_id": obj_id}, {"password": 0})
                    if data:
                        all_user_data[collection_name] = data
                        continue
                
                # Try with string ID
                data = await collection.find_one({"_id": user_id}, {"password": 0})
                if data:
                    all_user_data[collection_name] = data
                    continue
                
                # Try with user_id field 
                data = await collection.find_one({"user_id": user_id}, {"password": 0})
                if data:
                    all_user_data[collection_name] = data
                    continue
                
                # Try with userId field (as in user's example)
                data = await collection.find_one({"userId": user_id}, {"password": 0})
                if data:
                    all_user_data[collection_name] = data
                    continue
                
                if obj_id:
                    data = await collection.find_one({"user_id": obj_id}, {"password": 0})
                    if data:
                        all_user_data[collection_name] = data
                        continue
                    
                    # Try with userId field and ObjectId
                    data = await collection.find_one({"userId": obj_id}, {"password": 0})
                    if data:
                        all_user_data[collection_name] = data
                        continue
                
                # Try to find data related to this user even if not directly keyed by ID
                related_data = await collection.find({"$or": [
                    {"user_id": {"$exists": True}},
                    {"userId": {"$exists": True}}
                ]}).to_list(100)
                
                if related_data:
                    # Try to match on any sub-document that references this user
                    for doc in related_data:
                        if str(doc.get("user_id")) == user_id or str(doc.get("userId")) == user_id:
                            # Create or append to a list for this collection
                            if collection_name not in all_user_data:
                                all_user_data[collection_name] = []
                            all_user_data[collection_name].append(doc)
            
            return all_user_data if all_user_data else None
            
        except Exception as e:
            print(f"Error retrieving user data from all collections: {e}")
            return None
    
    @staticmethod
    async def list_sample_users(limit: int = 5) -> List[str]:
        """
        Return a list of sample user IDs for testing.
        """
        try:
            db = MongoDB.get_db()
            
            # First try users collection
            if "users" in await db.list_collection_names():
                users = await db.users.find({}, {"_id": 1}).limit(limit).to_list(limit)
                if users:
                    return [str(user["_id"]) for user in users]
            
            # Check for collections with userId field (as seen in the user's example)
            for collection_name in await db.list_collection_names():
                collection = db[collection_name]
                # First try to find documents with userId field
                docs_with_userid = await collection.find({"userId": {"$exists": True}}, {"userId": 1}).limit(limit).to_list(limit)
                if docs_with_userid:
                    return [str(doc["userId"]) for doc in docs_with_userid]
                
                # If not found, try with _id field
                docs = await collection.find({}, {"_id": 1}).limit(limit).to_list(limit)
                if docs:
                    return [str(doc["_id"]) for doc in docs]
            
            return []
        except Exception as e:
            print(f"Error listing sample users: {e}")
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