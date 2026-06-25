import os
import json
import sqlite3
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Basic Server with ADK integration",
    description="A FastAPI server interacting with ADK API",
    version="0.2.0"
)

ADK_URL = os.getenv("ADK_URL", "https://basic-agent-service-478948596809.us-central1.run.app").rstrip('/')

# Database setup
DB_FILE = "adk_sessions.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id TEXT,
            session_id TEXT,
            agent_app_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, session_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class CreateSessionRequest(BaseModel):
    user_id: str
    agent_app_name: str = "basic_agent_app"

class GenerateRequest(BaseModel):
    user_id: str
    prompt_query: str
    agent_app_name: str = "basic_agent_app"

@app.get("/")
async def root():
    """Root endpoint to verify the server is running."""
    return {"status": "ok", "message": "FastAPI server is up and running!"}

@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"ping": "pong"}

@app.post("/create_session")
async def create_session(req: CreateSessionRequest):
    session_id = f"s_{uuid.uuid4().hex[:8]}"
    
    # Store in DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_sessions (user_id, session_id, agent_app_name) VALUES (?, ?, ?)", 
            (req.user_id, session_id, req.agent_app_name)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    conn.close()
    
    # Call ADK API to create session
    adk_endpoint = f"{ADK_URL}/apps/{req.agent_app_name}/users/{req.user_id}/sessions/{session_id}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Empty POST to ADK endpoint according to spec to initialize
            response = await client.post(adk_endpoint, headers=headers, json={}, timeout=10.0)
            response.raise_for_status()
            try:
                return json.loads(response.text)
            except ValueError:
                return {"detail": "Non-JSON response from ADK", "text": response.text}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"ADK Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate(req: GenerateRequest):
    # Retrieve user session from DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id FROM user_sessions WHERE user_id = ? AND agent_app_name = ? ORDER BY created_at DESC LIMIT 1",
        (req.user_id, req.agent_app_name)
    )
    row = cursor.fetchone()
    conn.close()
    
    session_id = None
    if row:
        session_id = row[0]
    else:
        # Create a new session if none exists
        create_req = CreateSessionRequest(user_id=req.user_id, agent_app_name=req.agent_app_name)
        session_resp = await create_session(create_req)
        session_id = session_resp.get("id")
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create session in ADK.")
            
    # Now call /run_sse
    run_endpoint = f"{ADK_URL}/run_sse"
    payload = {
        "appName": req.agent_app_name,
        "userId": req.user_id,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [
                {
                    "text": req.prompt_query
                }
            ]
        },
        "streaming": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(run_endpoint, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            print("adk response: ", response.text)
            
            raw_text = response.text.strip()
            # If the ADK responds with SSE format, strip the "data:" prefix
            if raw_text.startswith("data:"):
                raw_text = raw_text.replace("data:", "", 1).strip()
                
            return json.loads(raw_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ADK Error: {e}")

if __name__ == "__main__":
    # Run the server using uvicorn when executing the file directly
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)