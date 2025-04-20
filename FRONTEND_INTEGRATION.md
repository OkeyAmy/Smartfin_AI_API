# Frontend Integration Guide

This document outlines how to connect your Next.js frontend to the Smartfin AI FastAPI backend.

## Application Features

Smartfin AI is a financial assistant with the following modules:

1. **Contacts**: Allows users to input and manage their customers
2. **Expenses**: Tracks the expenses incurred by the user
3. **Products**: Enables users to add and manage their product inventory 
4. **Transactions**: Records and displays the user's transaction history

## API Endpoint

The main API endpoint for communication is:

```
POST /api/v1/conversation/{user_id}
```

This single endpoint handles all chatbot operations by changing the `operation` parameter.

> **Note:** The `user_id` parameter should be the **userId** field from your application database, not the MongoDB _id field.

## Database Structure

The application expects data in MongoDB collections with the following structure:

```json
{
  "_id": {"$oid":"67ffc9a6eab5cf1fda980b8d"},
  "userId": "QOJkQvNN3PdiHtuXTSR1l2fWwxj2", // This is the user_id used in API endpoints
  "amount": {"$numberInt":"11"},
  "category": "Entertainment",
  "description": "Subscription service",
  "date": {"$date":{"$numberLong":"-27080352000000"}},
  "createdAt": {"$date":{"$numberLong":"1744816550743"}}
}
```

The backend searches all collections for documents containing the specified `userId` field to provide personalized responses.

## Conversation History Changes

The backend now stores conversation history **persistently in MongoDB**. This means:

1. Conversations are remembered across page refreshes and application restarts
2. Users can continue conversations where they left off, even after closing the browser
3. The LLM has access to the full conversation history for better context-aware responses
4. The conversation history is only cleared when explicitly requested by the user

## API Operations

### 1. Send a Message (Default)

**Request:**
```javascript
const response = await fetch("/api/v1/conversation/{user_id}", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ 
    message: "What's my current balance?",
    operation: "message" // This is the default operation
  }),
});
```

**Response:**
```json
{
  "response": "Based on your financial data, your current balance is $5,243.28.",
  "messages": [
    {
      "role": "user",
      "content": "What's my current balance?",
      "timestamp": "2023-07-15T10:30:00.000Z"
    },
    {
      "role": "assistant",
      "content": "Based on your financial data, your current balance is $5,243.28.",
      "timestamp": "2023-07-15T10:30:05.000Z"
    }
  ],
  "success": true
}
```

### 2. Get Conversation History

**Request:**
```javascript
const response = await fetch("/api/v1/conversation/{user_id}", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ 
    operation: "history"
  }),
});
```

**Response:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's my current balance?",
      "timestamp": "2023-07-15T10:30:00.000Z"
    },
    {
      "role": "assistant",
      "content": "Based on your financial data, your current balance is $5,243.28.",
      "timestamp": "2023-07-15T10:30:05.000Z"
    }
  ],
  "success": true
}
```

### 3. Clear Conversation History

**Request:**
```javascript
const response = await fetch("/api/v1/conversation/{user_id}", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ 
    operation: "clear"
  }),
});
```

**Response:**
```json
{
  "response": "Conversation history cleared",
  "messages": [],
  "success": true
}
```

## Example Frontend Integration

Update your frontend code to use the new API endpoint. Here's an example implementation for a Next.js React component:

```javascript
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react'; // Or your auth provider

export default function FinancialAssistant() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Load conversation history when component mounts
  useEffect(() => {
    if (session?.user?.id) {
      loadConversationHistory();
    }
  }, [session?.user?.id]);

  // Function to load conversation history
  const loadConversationHistory = async () => {
    if (!session?.user?.id) return;
    
    setIsLoadingHistory(true);
    try {
      const response = await fetch("/api/v1/conversation/" + session.user.id, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          operation: "history"
        }),
      });
      
      const data = await response.json();
      
      if (data.messages && Array.isArray(data.messages)) {
        setMessages(data.messages);
      }
    } catch (error) {
      console.error("Error loading conversation history:", error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Function to send a message
  const sendMessage = async () => {
    if (input.trim() === "") return;
    
    // Get user_id from session
    const user_id = session?.user?.id;
    
    // If no user_id, show an error or prompt to login
    if (!user_id) {
      setMessages(prev => [
        ...prev, 
        { role: "user", content: input },
        { role: "assistant", content: "Please log in to use the financial assistant." }
      ]);
      setInput("");
      return;
    }

    const newMessage = { role: "user", content: input, timestamp: new Date() };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/v1/conversation/" + user_id, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          message: input,
          operation: "message"
        }),
      });
      
      const data = await response.json();

      if (data.response) {
        // Add AI response to message list
        setMessages(prev => [...prev, {
          role: "assistant",
          content: data.response,
          timestamp: new Date()
        }]);
        
        // Alternatively, use the complete conversation history from the response
        // This ensures frontend and backend history are in sync
        // setMessages(data.messages);
      } else if (data.error) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `Error: ${data.error}`,
          timestamp: new Date()
        }]);
      }
    } catch (error) {
      console.error("Error:", error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, there was an error connecting to the financial assistant.",
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to clear conversation history
  const clearConversationHistory = async () => {
    if (!session?.user?.id || !window.confirm("Are you sure you want to clear your conversation history?")) return;
    
    try {
      const response = await fetch("/api/v1/conversation/" + session.user.id, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          operation: "clear"
        }),
      });
      
      if (response.ok) {
        setMessages([]);
      }
    } catch (error) {
      console.error("Error clearing conversation history:", error);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-gray-50 rounded-lg p-4">
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {isLoadingHistory && <p className="text-center text-gray-500">Loading conversation history...</p>}
        
        {messages.length === 0 && !isLoadingHistory && (
          <div className="text-center text-gray-500 mt-10">
            <p>Welcome to your Financial Assistant!</p>
            <p>Ask questions about your financial data, expenses, contacts, or transactions.</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] rounded-lg p-3 ${
              msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white border border-gray-200'
            }`}>
              {msg.content}
              <div className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-100' : 'text-gray-400'}`}>
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="flex items-center border-t pt-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about your finances..."
          disabled={isLoading}
          className="flex-1 border border-gray-300 rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={sendMessage}
          disabled={isLoading || !input.trim()}
          className="bg-blue-500 text-white px-4 py-2 rounded-r-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-300"
        >
          Send
        </button>
        <button
          onClick={clearConversationHistory}
          disabled={isLoading || messages.length === 0}
          className="ml-2 bg-gray-200 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-300 focus:outline-none"
          title="Clear conversation history"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
```

## AI Capabilities

The AI assistant is powered by Google's Gemini 2.0 Flash model and is designed to:

1. **Analyze financial data** across all your application modules
2. **Provide personalized insights** based on the user's specific data
3. **Maintain context** throughout the conversation
4. **Protect sensitive information** by following security guidelines

The AI can answer questions about:
- Customer information (from Contacts)
- Expense categories and spending patterns
- Product inventory and performance
- Transaction history and trends

## API Routes in Next.js

If you're using API routes in Next.js to proxy requests to your backend, here's how to set them up:

```javascript
// src/app/api/conversation/[userId]/route.js
import { NextResponse } from "next/server";

export async function POST(req, { params }) {
  try {
    const { userId } = params;
    const body = await req.json();
    const { message, operation = "message" } = body;
    
    // Get your backend URL from environment variables
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    // Make the request to your deployed backend
    const response = await fetch(`${backendUrl}/api/v1/conversation/${userId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ 
        message,
        operation
      }),
    });
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error forwarding request to backend:", error);
    return NextResponse.json(
      { error: "Failed to communicate with backend" },
      { status: 500 }
    );
  }
}
```

## Sample User Selection

To get sample user IDs for testing, use the existing endpoint:

```javascript
const getSampleUsers = async () => {
  try {
    const response = await fetch("/api/v1/users/sample");
    const userIds = await response.json();
    return userIds;
  } catch (error) {
    console.error("Error fetching sample users:", error);
    return [];
  }
};
```

## Environment Configuration

Make sure your frontend's environment variables point to your deployed backend:

```
# .env.local for Next.js
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

## Security Considerations

1. **User Authentication**: Ensure that the frontend properly authenticates users before allowing access to the conversation endpoint.

2. **Data Privacy**: The AI is programmed not to reveal sensitive information like user IDs or passwords.

3. **Error Handling**: Implement proper error handling to prevent exposing implementation details to end users.

4. **Rate Limiting**: Consider implementing rate limiting on the frontend to prevent abuse of the AI service.

## Troubleshooting

If you encounter issues with the integration:

1. **Check Network Requests**: Use browser developer tools to inspect the request/response cycle.

2. **Verify userId Format**: Ensure you're using the correct userId field from your database (not the MongoDB _id).

3. **Check API Availability**: Use the health endpoint to verify that both MongoDB and the AI service are operational:
   ```javascript
   const checkHealth = async () => {
     const response = await fetch("/api/v1/health");
     const health = await response.json();
     console.log("API Health:", health);
     return health.status === "ok";
   };
   ```

4. **Handle Loading States**: Implement proper loading states to improve user experience during API calls.

5. **Debug Mode**: Add a debug mode to log communication details and API responses:
   ```javascript
   const DEBUG = process.env.NEXT_PUBLIC_DEBUG === "true";
   
   // Usage in API calls
   if (DEBUG) console.log("Sending request:", body);
   ``` 