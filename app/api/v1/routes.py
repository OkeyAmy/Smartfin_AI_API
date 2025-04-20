from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.schemas.conversation import ConversationRequest, ConversationResponse, MessageSchema
from typing import List, Dict
from app.db.mongodb import MongoDB
import google.generativeai as genai
from datetime import datetime

router = APIRouter()

@router.post("/conversation/{user_id}", response_model=ConversationResponse)
async def process_conversation(
    request: Request,
    user_id: str,  # This is used to search for documents with _id, user_id, or userId fields
    conversation: ConversationRequest = None
):
    """
    Process a conversation with the AI assistant.
    This endpoint handles multiple operations:
    - Send a message and get a response (default)
    - Retrieve conversation history
    - Clear conversation history
    
    The conversation history is maintained persistently in MongoDB
    until explicitly cleared by the user.
    """
    # Initialize AI service
    ai_service = AIService()
    
    # Check if this is a new session (page refresh)
    # We no longer reset on page refresh, since history is stored persistently
    # But we can use this to track new sessions for analytics
    session_id = str(request.headers.get('sec-fetch-site', ''))
    is_new_session = session_id == 'none'  
    
    # Determine operation from request
    operation = conversation.operation if conversation and conversation.operation else "message"
    
    # OPERATION: Clear conversation history
    if operation == "clear":
        try:
            await ai_service.reset_chat(user_id)
            return ConversationResponse(
                success=True,
                messages=[],
                response="Conversation history cleared"
            )
        except Exception as e:
            print(f"Error clearing conversation history: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")
    
    # OPERATION: Get conversation history
    if operation == "history":
        try:
            messages = await ai_service.get_conversation_history(user_id)
            return ConversationResponse(
                messages=messages,
                success=True
            )
        except Exception as e:
            print(f"Error retrieving conversation history: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")
    
    # OPERATION: Process new message (default)
    # Process conversation
    if not conversation or not conversation.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Try to verify MongoDB connection first
    try:
        db = MongoDB.get_db()
        # Quick ping to verify connection
        await db.command("ping")
        print(f"MongoDB connection verified for user {user_id}")
    except Exception as db_error:
        print(f"MongoDB connection error: {str(db_error)}")
        # We'll continue and let the AI service handle fallbacks
    
    try:
        # Empty dict as placeholder - the AI service will fetch data directly from MongoDB
        user_data = {}
            
        response = await ai_service.process_conversation(
            user_message=conversation.message,
            user_data=user_data,  # This is now just a fallback
            user_id=user_id
        )
        
        # Get updated conversation history - handle potential errors
        try:
            messages = await ai_service.get_conversation_history(user_id)
        except Exception as history_error:
            print(f"Error getting conversation history after processing: {str(history_error)}")
            # Create minimal history with just the current message if history retrieval fails
            messages = [
                {
                    "role": "user",
                    "content": conversation.message,
                    "timestamp": datetime.now()
                }
            ]
        
        return ConversationResponse(
            response=response,
            messages=messages,
            success=True
        )
    except Exception as e:
        print(f"Error in conversation endpoint: {str(e)}")
        # Return a user-friendly error response
        return ConversationResponse(
            response="I'm having trouble processing your request right now. Our team has been notified of the issue.",
            messages=[{"role": "user", "content": conversation.message, "timestamp": datetime.now()}],
            success=False,
            error=f"Internal server error: {str(e)}"
        )

@router.get("/users/sample", response_model=List[str])
async def get_sample_users(limit: int = 5):
    """Get a list of sample user IDs for testing."""
    users = await UserService.list_sample_users(limit)
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return users

@router.get("/health", response_model=Dict[str, str])
@router.head("/health")
async def health_check():
    """
    Check the health status of the service and its dependencies.
    Returns the status of MongoDB connection and Gemini AI availability.
    Supports both GET and HEAD requests.
    """
    health_status = {
        "status": "healthy",
        "mongodb": "unavailable",
        "gemini_ai": "unavailable",
        "data_access": "unknown"
    }
    
    try:
        # Check MongoDB connection
        db = MongoDB.get_client()
        db.admin.command('ping')
        health_status["mongodb"] = "connected"
        
        # Check if we can find any data with userId field
        try:
            db = MongoDB.get_db()
            collections = await db.list_collection_names()
            user_id_found = False
            
            for collection_name in collections:
                if collection_name == "conversation_history":
                    continue
                    
                collection = db[collection_name]
                # Check if any document has userId field
                doc_with_userid = await collection.find_one({"userId": {"$exists": True}})
                if doc_with_userid:
                    user_id_found = True
                    health_status["data_access"] = "userId fields found"
                    break
            
            if not user_id_found:
                health_status["data_access"] = "no userId fields found"
        except Exception as data_error:
            health_status["data_access"] = f"error: {str(data_error)}"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["mongodb"] = f"error: {str(e)}"
    
    try:
        # Check Gemini AI availability using class method
        if AIService.initialize():
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


