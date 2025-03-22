#!/usr/bin/env python3
"""
EU AI Act Embedding Service
A lightweight API service to generate embeddings for text
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
import time
import json
import httpx
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("embedding-service")

# Configuration
DEFAULT_BATCH_SIZE = int(os.environ.get("DEFAULT_BATCH_SIZE", "16"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "openai/text-embedding-ada-002")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))  # Default for ada-002

# Initialize the app
app = FastAPI(
    title="EU AI Act Embedding Service",
    description="Lightweight text embedding generation service using OpenRouter",
    version="1.0.0"
)

# Shared state
state = {
    "ready": OPENROUTER_API_KEY != "",
    "startup_time": time.time(),
    "requests_processed": 0,
    "total_texts_embedded": 0,
    "total_processing_time": 0
}

# Request models
class EmbeddingRequest(BaseModel):
    texts: List[str]
    batch_size: Optional[int] = None

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    processing_time: float

# Async HTTP client
async def get_http_client():
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

# Embedding generation function using OpenRouter
async def generate_embeddings_with_openrouter(
    texts: List[str], 
    client: httpx.AsyncClient,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> List[List[float]]:
    """Generate embeddings for a list of texts using OpenRouter API"""
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter API key not configured")
        # Return zero embeddings as fallback
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://eu-ai-act-compliance.com"  # Replace with your actual domain
    }
    
    # Process in batches to avoid large payloads
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            payload = {
                "model": EMBEDDING_MODEL,
                "input": batch
            }
            
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/embeddings", 
                json=payload, 
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.text}")
                # Fallback for failed batch
                all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])
                continue
                
            result = response.json()
            batch_embeddings = [data["embedding"] for data in result["data"]]
            all_embeddings.extend(batch_embeddings)
            
        except Exception as e:
            logger.error(f"Error generating embeddings for batch {i}: {e}")
            # Fallback for failed batch
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])
    
    return all_embeddings

# Routes
@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "EU AI Act Embedding Service",
        "status": "ready" if state["ready"] else "not configured",
        "model": EMBEDDING_MODEL,
        "startup_time": state["startup_time"],
        "requests_processed": state["requests_processed"],
        "total_texts_embedded": state["total_texts_embedded"]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy" if state["ready"] else "not configured"}

@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    client: httpx.AsyncClient = Depends(get_http_client)
):
    """Generate embeddings for a list of texts"""
    if not state["ready"]:
        raise HTTPException(
            status_code=503,
            detail="Embedding service not configured properly, check OPENROUTER_API_KEY"
        )
    
    # Track stats
    state["requests_processed"] += 1
    state["total_texts_embedded"] += len(request.texts)
    
    # Use requested batch size or default
    batch_size = request.batch_size or DEFAULT_BATCH_SIZE
    
    # Generate embeddings
    start_time = time.time()
    embeddings = await generate_embeddings_with_openrouter(request.texts, client, batch_size)
    processing_time = time.time() - start_time
    
    # Track total processing time
    state["total_processing_time"] += processing_time
    
    # Return response
    return EmbeddingResponse(
        embeddings=embeddings,
        processing_time=processing_time
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info") 