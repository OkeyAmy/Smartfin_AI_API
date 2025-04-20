import os
import google.generativeai as genai
from app.core.config import settings
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from bson import ObjectId
from app.db.mongodb import MongoDB

def _load_prompt(file_name: str) -> str:
    """Load prompt from a file with error handling."""
    try:
        file_path = os.path.join('app', 'prompt', file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Warning: Prompt file {file_name} not found.")
        return "Unable to load prompt. Please check the file name."
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return "Unable to load prompt due to an error."


class AIService:
    model = None
    chats = {}  # Store chats by user ID
    
    @classmethod
    def initialize(cls):
        """Initialize the Gemini AI model."""
        if cls.model is None:
            try:
                genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                cls.model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=_load_prompt('system_instruction.txt'))
                return True
            except Exception as e:
                print(f"Error initializing AI model: {e}")
                return False
        return True
    
    async def reset_chat(self, user_id: str) -> None:
        """Reset the chat history for a user and clear it from MongoDB."""
        if user_id in self.chats:
            del self.chats[user_id]
        
        # Also clear from database
        try:
            db = MongoDB.get_db()
            # Delete records with both user_id and userId fields
            await db.conversation_history.delete_many(
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            )
        except Exception as e:
            print(f"Error clearing conversation history from MongoDB: {e}")
    
    async def _get_or_create_chat(self, user_id: str):
        """
        Get existing chat or create a new one for the user.
        Loads conversation history from MongoDB if available.
        """
        if user_id not in self.chats:
            try:
                # Use class method rather than instance method
                AIService.initialize()
                
                # Ensure we have a reference to the model
                model = AIService.model
                if not model:
                    print(f"Error: AI model is not initialized")
                    return None
                
                # Create a new chat
                self.chats[user_id] = model.start_chat(history=[])
                
                # Try to load previous conversation from MongoDB
                await self._load_conversation_history(user_id)
            except Exception as e:
                print(f"Error creating chat for user {user_id}: {e}")
                return None
        return self.chats[user_id]
    
    async def _load_conversation_history(self, user_id: str) -> None:
        """
        Load conversation history from MongoDB and apply it to the current chat.
        """
        try:
            db = MongoDB.get_db()
            # Get the most recent 50 messages - check both user_id and userId fields
            messages = await db.conversation_history.find(
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ).sort("timestamp", -1).limit(50).to_list(50)
            
            # Sort messages by timestamp so they're in chronological order
            messages.sort(key=lambda x: x.get("timestamp", datetime.min))
            
            # If we have messages, add them to the chat
            if messages and user_id in self.chats:
                chat = self.chats[user_id]
                
                # Add each message to the chat
                for msg in messages:
                    role = msg.get("role")
                    content = msg.get("content")
                    
                    if role and content:
                        # We don't await this because Gemini's API doesn't need async
                        # We're just replaying the history, not generating new responses
                        if role == "user":
                            chat.send_message(content)
                        else:
                            # For assistant messages, we add them directly to history
                            # but this depends on the Gemini API implementation
                            # This might need adjustment based on how the API works
                            pass
        except Exception as e:
            print(f"Error loading conversation history for user {user_id}: {e}")
    
    async def _save_message(self, user_id: str, role: str, content: str) -> None:
        """
        Save a message to MongoDB for persistent conversation history.
        """
        try:
            db = MongoDB.get_db()
            await db.conversation_history.insert_one({
                "user_id": user_id,  # Keep this for backward compatibility
                "userId": user_id,   # Add this to match database structure
                "role": role,
                "content": content,
                "timestamp": datetime.now()
            })
        except Exception as e:
            print(f"Error saving message to MongoDB: {e}")
    
    def _convert_objectid_to_string(self, data: Any) -> Any:
        """
        Convert ObjectId and datetime fields in data to strings.
        Works with both dictionaries and lists.
        """
        if isinstance(data, dict):
            # Process dictionary
            for key, value in list(data.items()):
                if isinstance(value, ObjectId):
                    data[key] = str(value)
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    data[key] = self._convert_objectid_to_string(value)
            return data
        elif isinstance(data, list):
            # Process list
            return [self._convert_objectid_to_string(item) for item in data]
        else:
            # Return unchanged for other types
            return data
    
    async def process_conversation(self, user_message: str, user_data: Dict, user_id: str) -> str:
        """
        Process user message with context from user data.
        Maintains conversation history in both memory and MongoDB.
        """
        try:
            # Save user message to MongoDB first (do this early to ensure it's saved even if we encounter errors)
            await self._save_message(user_id, "user", user_message)
            
            # First ensure model is initialized at the class level
            if not AIService.initialize():
                error_msg = "Could not initialize AI model. Please check your API key."
                await self._save_message(user_id, "assistant", error_msg)
                return error_msg
            
            # Get or create chat for this user
            chat = await self._get_or_create_chat(user_id)
            if not chat:
                error_msg = "Could not create chat session. Please try again later."
                await self._save_message(user_id, "assistant", error_msg)
                return error_msg
            
            try:
                # Get all user data directly from MongoDB with error handling
                all_user_data = await self._get_all_user_data_from_mongodb(user_id)
                
                # If MongoDB retrieval fails, use the passed user_data as fallback
                if not all_user_data or "error" in all_user_data:
                    if user_data and len(user_data) > 0:
                        all_user_data = user_data
                    else:
                        # Minimal context if no data is available
                        all_user_data = {"note": "No specific user data is available. Providing general financial advice."}
                
                # Convert MongoDB-specific types to strings (handle potential errors)
                try:
                    all_user_data = self._convert_objectid_to_string(all_user_data)
                except Exception as e:
                    print(f"Error converting ObjectIds to strings: {str(e)}")
                    # Provide a simplified version if conversion fails
                    all_user_data = {"user_id": user_id, "note": "Error accessing detailed user data."}
                
                # Create the prompt with all user data - use a smaller JSON representation
                # to avoid overwhelming the model
                compact_data = json.dumps(all_user_data)
                # if len(compact_data) > 8000:  # Truncate if too large
                #     print(f"Warning: User data JSON is very large ({len(compact_data)} chars)")
                #     compact_data = compact_data[:7500] + "... (truncated)"
                
                # Create the prompt with focus on answering regardless of data quality
                prompt = f"""
                You are a professional financial assistant.
                
                Here is the available user data (if any): {compact_data}
                
                IMPORTANT: 
                1. DO NOT reveal sensitive information like IDs, passwords, or full account numbers.
                2. Provide helpful financial advice based on the data if available.
                3. If no specific user data is available, provide general financial guidance.
                4. Be conversational and friendly while remaining professional.
                5. Remember previous parts of our conversation as context.
                6. Always provide a helpful response even if data is limited.
                7. Search the available data to answer the user's question. If no relevant information is found, provide guidance on how to achieve their goal within the application.

                The application has the following features:
                1. Contacts: Allows users to input and manage their customers
                2. Expenses: Shows the expenses incurred by the user
                3. Products: Allows users to add their products
                4. Transactions: Shows the user's transaction history

                User asks: {user_message}
                """
                
                # Send message to AI with timeout handling
                try:
                    response = chat.send_message(prompt)
                    ai_response = response.text.strip()
                    
                    # Check for empty response
                    if not ai_response:
                        ai_response = "I understand your question but I'm having trouble formulating a response. Could you please rephrase your question or ask something more specific about your finances?"
                except Exception as model_error:
                    print(f"Error from AI model: {str(model_error)}")
                    # Fallback response if AI model fails
                    ai_response = "I apologize, but I'm having trouble processing your request right now. This may be due to a temporary issue with the AI service. Please try again shortly."
                
                # Save assistant response to MongoDB
                await self._save_message(user_id, "assistant", ai_response)
                
                return ai_response
                
            except Exception as inner_error:
                print(f"Inner error in process_conversation: {str(inner_error)}")
                fallback_response = "I'm having trouble accessing your financial data at the moment. Is there something general I can help you with about financial planning or advice?"
                await self._save_message(user_id, "assistant", fallback_response)
                return fallback_response
                
        except Exception as e:
            print(f"Error processing conversation: {str(e)}")
            error_response = "I apologize for the inconvenience. Our system is experiencing a temporary issue. Please try again in a few moments."
            
            # Try to save the error response, but don't raise another exception if this fails
            try:
                await self._save_message(user_id, "assistant", error_response)
            except:
                pass
            
            return error_response
    
    async def _get_all_user_data_from_mongodb(self, user_id: str) -> Dict:
        """
        Retrieve all data related to the user directly from MongoDB.
        Reads from all collections in the cluster filtering by userId field.
        """
        try:
            db = MongoDB.get_db()
            all_user_data = {}
            
            # Get list of all collections in the database
            collections = await db.list_collection_names()
            
            # Skip conversation_history collection as it's not user data
            if 'conversation_history' in collections:
                collections.remove('conversation_history')
            
            # Query all collections for any data related to this user ID
            for collection_name in collections:
                collection = db[collection_name]
                
                # Try to find data with this user ID in any field
                try:
                    # Try as ObjectId if possible
                    obj_id = None
                    try:
                        obj_id = ObjectId(user_id)
                    except:
                        # Not a valid ObjectId, continue with string ID
                        pass
                    
                    # Build query based on available ID formats
                    # Add "userId" field as per user's database structure
                    if obj_id:
                        id_query = {"$or": [
                            {"_id": obj_id}, 
                            {"user_id": obj_id},
                            {"userId": obj_id},
                            {"userId": user_id}
                        ]}
                    else:
                        id_query = {"$or": [
                            {"_id": user_id}, 
                            {"user_id": user_id},
                            {"userId": user_id}
                        ]}
                    
                    # Find documents with limit to prevent overwhelming the model
                    docs = await collection.find(id_query).limit(10).to_list(10)
                    
                    if docs and len(docs) > 0:
                        # Keep data structures from growing too large
                        if len(docs) > 1:
                            # For multiple documents, only keep essential fields
                            simplified_docs = []
                            for doc in docs:
                                # Filter large fields to keep data manageable
                                simplified_doc = {k: v for k, v in doc.items() 
                                                if not isinstance(v, (dict, list)) or 
                                                   (isinstance(v, (dict, list)) and len(str(v)) < 1000)}
                                simplified_docs.append(simplified_doc)
                            all_user_data[collection_name] = simplified_docs
                        else:
                            # For single document, keep as is
                            all_user_data[collection_name] = docs[0]
                        continue
                    
                    # Skip text search as it's error-prone and may not be configured
                    # on all MongoDB instances
                    
                except Exception as e:
                    print(f"Error querying collection {collection_name}: {str(e)}")
                    continue
            
            # If no user data found, return a friendly message
            if not all_user_data:
                return {"message": "No user data found. I can still help with general financial questions."}
            
            return all_user_data
            
        except Exception as e:
            print(f"Error retrieving all user data from MongoDB: {str(e)}")
            # Return a minimal data structure rather than an empty dict
            return {"error": "Could not retrieve user data", "user_id": user_id}
    
    async def get_conversation_history(self, user_id: str) -> List[Dict]:
        """
        Get the conversation history for a user from MongoDB.
        Returns a list of messages in the format expected by the frontend.
        """
        try:
            db = MongoDB.get_db()
            # Query for records with either user_id or userId fields
            messages = await db.conversation_history.find(
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ).sort("timestamp", 1).to_list(100)  # Sort by timestamp ascending
            
            # Format for frontend
            history = []
            for msg in messages:
                history.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp")
                })
            
            return history
        except Exception as e:
            print(f"Error getting conversation history from MongoDB: {e}")
            
            # Fallback to in-memory history if available
            if user_id in self.chats:
                chat = self.chats[user_id]
                history = []
                
                for message in chat.history:
                    role = "user" if message.role == "user" else "assistant"
                    content = message.parts[0].text
                    history.append({
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now()
                    })
                
                return history
            
            return [] 