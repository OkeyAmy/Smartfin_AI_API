from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class ConversationRequest(BaseModel):
    """Schema for conversation request from frontend"""
    message: str = Field(..., description="User message")
    operation: Optional[str] = Field(None, description="Operation type: 'message', 'history', 'clear'")

class MessageSchema(BaseModel):
    """Schema for a single message in the conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")

class ConversationResponse(BaseModel):
    """Schema for conversation response to frontend"""
    response: Optional[str] = Field(None, description="AI response to user message")
    messages: Optional[List[MessageSchema]] = Field(None, description="Conversation history")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    success: Optional[bool] = Field(None, description="Operation success status")
    error: Optional[str] = Field(None, description="Error message if operation failed") 