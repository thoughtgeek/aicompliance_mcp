from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, sessions, documents

app = FastAPI(title="AI Doc Generator API", description="Backend for AI Compliance Documentation Generator")

# CORS setup - essential for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(documents.router, prefix="/api", tags=["documents"])

@app.get("/")
async def root():
    return {"message": "AI Doc Generator API is running", "status": "ok"} 