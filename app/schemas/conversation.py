from pydantic import BaseModel

class ConversationRequest(BaseModel):
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is my name?"
            }
        }

class ConversationResponse(BaseModel):
    response: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on your user data, your name is John Doe."
            }
        } 