# Smartfin AI API

A FastAPI-based conversational AI service that integrates Google's Gemini AI with MongoDB to provide personalized responses based on user data.

## Features

- 🤖 Powered by Google's Gemini 2.0 Flash Exp model
- 🗄️ MongoDB integration for user data management
- 💬 Maintains conversation history per user session
- 🔄 Automatic session management (resets on page refresh)
- 🔍 Comprehensive collection search functionality
- 🔒 Secure data handling with sensitive information filtering

## Project Structure

```
app/
├── api/
│   └── v1/
│       └── routes.py         # API endpoints
├── core/
│   └── config.py            # Configuration settings
├── db/
│   └── mongodb.py           # MongoDB connection management
├── models/                  # Data models (if needed)
├── schemas/
│   └── conversation.py      # Pydantic models
├── services/
│   ├── ai_service.py        # Gemini AI integration
│   └── user_service.py      # User data operations
└── main.py                  # FastAPI application
│
└── run.py                  # Run FastAPI application
│
└── requirements.txt        # Requirements 

```

## Prerequisites

- Python 3.8+
- MongoDB database
- Google AI API key

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# MongoDB Settings
MONGODB_URI="your_mongodb_connection_string"
MONGODB_DB_NAME="your_database_name"

# Google AI Settings
GOOGLE_API_KEY="your_google_ai_api_key"
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd smartfin-ai
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Unix or MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the server:
```bash
python run.py
# or
uvicorn app.main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Get Sample Users
```http
GET /api/v1/users/sample
```
Returns a list of sample user IDs for testing.

### Process Conversation
```http
POST /api/v1/conversation/{user_id}
```
Process a conversation with the AI assistant.

Request body:
```json
{
    "message": "Your message here"
}
```

## Example Usage

1. Get a sample user ID:
```bash
curl -X 'GET' 'http://localhost:8000/api/v1/users/sample'
```

2. Start a conversation:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/conversation/59b99db4cfa9a34dcd7885b6' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What information do you have about me?"
}'
```

## Features in Detail

### Conversation Management
- Each user gets a dedicated chat session
- Chat history is maintained until page refresh
- Automatic session cleanup on page refresh

### Data Security
- Sensitive information filtering
- Password fields are automatically excluded
- Private data (IDs, etc.) are not exposed in responses

### MongoDB Integration
- Efficient collection searching
- Automatic ObjectID handling
- Comprehensive error handling

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request



## Acknowledgments

- Google Gemini AI for the language model
- FastAPI for the web framework
- MongoDB for the database
- All contributors and users of this project 