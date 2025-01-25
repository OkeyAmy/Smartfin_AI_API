from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.schemas.conversation import ConversationRequest, ConversationResponse
from typing import List

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