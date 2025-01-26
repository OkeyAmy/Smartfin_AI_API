from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.schemas.conversation import ConversationRequest, ConversationResponse
from typing import List, Dict
from app.db.mongodb import MongoDB
import google.generativeai as genai

router = APIRouter()

@router.post("/conversation/{user_id}", response_model=ConversationResponse)
async def process_conversation(
    request: Request,
    user_id: str,
    conversation: ConversationRequest
):
    """
    Process a conversation with the AI assistant.
    The conversation history is maintained until the page is refreshed.
    """
    # Check if this is a new session (page refresh)
    session_id = str(request.headers.get('sec-fetch-site', ''))
    if session_id == 'none':  # This indicates a page refresh
        AIService().reset_chat(user_id)
    
    # Get user data from all collections
    user_data = await UserService.get_user_data_from_all_collections(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User data not found in any collection")
    
    # Process conversation
    ai_service = AIService()
    response = await ai_service.process_conversation(
        user_message=conversation.message,
        user_data=user_data,
        user_id=user_id
    )
    
    return ConversationResponse(response=response)

@router.get("/users/sample", response_model=List[str])
async def get_sample_users(limit: int = 5):
    """Get a list of sample user IDs for testing."""
    users = await UserService.list_sample_users(limit)
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return users

@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """
    Check the health status of the service and its dependencies.
    Returns the status of MongoDB connection and Gemini AI availability.
    """
    health_status = {
        "status": "healthy",
        "mongodb": "unavailable",
        "gemini_ai": "unavailable"
    }
    
    try:
        # Check MongoDB connection
        db = MongoDB.get_client()
        db.admin.command('ping')
        health_status["mongodb"] = "connected"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["mongodb"] = f"error: {str(e)}"
    
    try:
        # Check Gemini AI availability
        model = AIService().model
        if model:
            health_status["gemini_ai"] = "available"
        else:
            health_status["status"] = "degraded"
            health_status["gemini_ai"] = "initialization failed"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["gemini_ai"] = f"error: {str(e)}"
    
    if health_status["mongodb"] != "connected" or health_status["gemini_ai"] != "available":
        health_status["status"] = "degraded"
    
    return health_status


