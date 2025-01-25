import os
import google.generativeai as genai
from app.core.config import settings
import json
from typing import Optional, Dict
from datetime import datetime
from bson import ObjectId

def _load_prompt(file_name: str) -> str:
    """Load prompt from a file with error handling."""
    try:
        file_path = os.path.join('prompts', file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Warning: Prompt file {file_name} not found.")
        return "Unable to load prompt. Please check the file name."
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return "Unable to load prompt due to an error."


class AIService:
    _instance = None
    _chat_sessions = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIService, cls).__new__(cls)
            try:
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                cls.model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=_load_prompt('system_instruction.txt'))
            except Exception as e:
                print(f"Error initializing Gemini AI: {e}")
                cls.model = None
        return cls._instance
    
    def _get_or_create_chat(self, user_id: str):
        """Get existing chat session or create new one."""
        if user_id not in self._chat_sessions:
            self._chat_sessions[user_id] = self.model.start_chat(history=[])
        return self._chat_sessions[user_id]
    
    def reset_chat(self, user_id: str):
        """Reset chat history for a user."""
        if user_id in self._chat_sessions:
            del self._chat_sessions[user_id]
    
    def _convert_objectid_to_string(self, data: Dict) -> Dict:
        """Convert ObjectId and datetime fields in the data dictionary to strings."""
        if not data:
            return data
            
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, dict):
                data[key] = self._convert_objectid_to_string(value)
        return data
    
    async def process_conversation(self, user_message: str, user_data: Dict, user_id: str) -> str:
        """Process user message and return AI response."""
        try:
            if not self.model:
                return "AI model is not initialized. Please check the API key."
            
            # Convert ObjectId fields to strings for JSON serialization
            user_data = self._convert_objectid_to_string(user_data)
            
            # Get or create chat session for this user
            chat = self._get_or_create_chat(user_id)
            
            prompt = f"""
            You are a helpful AI assistant with access to this user data: {json.dumps(user_data)}
            User asks: {user_message}
            Respond in a natural, conversational way. Only mention the specific information that was asked for.
            Do not reveal sensitive information like IDs, passwords, or private data.
            """
            
            response = chat.send_message(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"I encountered an error while processing your message: {str(e)}" 