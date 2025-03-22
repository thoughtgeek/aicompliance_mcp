#!/usr/bin/env python3
"""
EU AI Act Compliance System - API Gateway
A lightweight API Gateway that orchestrates requests between components
"""

import os
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api-gateway")

# Service URLs from environment variables with defaults for local development
TERMINUSDB_URL = os.environ.get("TERMINUSDB_URL", "http://terminusdb:6363")
VECTOR_DB_URL = os.environ.get("VECTOR_DB_URL", "http://vector-db:6333")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://embedding-service:8000")
LLM_URL = os.environ.get("LLM_URL", "http://llm-service:8008")

# Initialize the API gateway
app = FastAPI(
    title="EU AI Act Compliance API Gateway",
    description="API Gateway for EU AI Act Compliance System",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state for monitoring component status
state = {
    "ready": False,
    "component_status": {
        "terminusdb": False,
        "vector_db": False,
        "embedding": False,
        "llm": False
    },
    "requests_processed": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_processing_time": 0,
}

# Model definitions
class Document(BaseModel):
    id: str
    content: str
    score: Optional[float] = None
    source: Optional[str] = None
    type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    min_score: Optional[float] = 0.6
    filter: Optional[Dict[str, Any]] = None

class ComplianceQueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    min_score: Optional[float] = 0.6
    temperature: Optional[float] = 0.1
    filter: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    uptime: float
    requests_processed: int

# HTTP client
async def get_http_client():
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

# Background task to check components health
@app.on_event("startup")
async def startup_event():
    # Start a background task to periodically check component health
    asyncio.create_task(check_components_health())

async def check_components_health():
    """Periodically check health of all components"""
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check TerminusDB
                try:
                    resp = await client.get(f"{TERMINUSDB_URL}/api/health")
                    state["component_status"]["terminusdb"] = resp.status_code == 200
                except:
                    state["component_status"]["terminusdb"] = False
                
                # Check Vector DB
                try:
                    resp = await client.get(f"{VECTOR_DB_URL}/readiness")
                    state["component_status"]["vector_db"] = resp.status_code == 200
                except:
                    state["component_status"]["vector_db"] = False
                
                # Check Embedding Service
                try:
                    resp = await client.get(f"{EMBEDDING_URL}/health")
                    state["component_status"]["embedding"] = resp.status_code == 200
                except:
                    state["component_status"]["embedding"] = False
                
                # Check LLM Service
                try:
                    resp = await client.get(f"{LLM_URL}/health")
                    state["component_status"]["llm"] = resp.status_code == 200
                except:
                    state["component_status"]["llm"] = False
                
                # Update overall readiness
                state["ready"] = all(state["component_status"].values())
                
                logger.info(f"Component health check: {state['component_status']}")
        except Exception as e:
            logger.error(f"Error checking component health: {e}")
        
        # Wait before next check
        await asyncio.sleep(30)

# Helper functions
async def get_vector_embeddings(client: httpx.AsyncClient, texts: List[str]) -> List[List[float]]:
    """Get embeddings for a list of texts"""
    try:
        response = await client.post(
            f"{EMBEDDING_URL}/embeddings",
            json={"texts": texts}
        )
        
        if response.status_code != 200:
            logger.error(f"Error getting embeddings: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Error getting embeddings")
        
        return response.json()["embeddings"]
    except Exception as e:
        logger.error(f"Error calling embedding service: {e}")
        raise HTTPException(status_code=500, detail=f"Error calling embedding service: {str(e)}")

async def search_vector_db(client: httpx.AsyncClient, embedding: List[float], 
                          max_results: int = 5, min_score: float = 0.6) -> List[Dict[str, Any]]:
    """Search vector database using embedding"""
    try:
        # Prepare search payload for Qdrant
        payload = {
            "vector": embedding,
            "limit": max_results,
            "with_payload": True,
            "with_vectors": False,
            "score_threshold": min_score
        }
        
        response = await client.post(
            f"{VECTOR_DB_URL}/collections/eu_ai_act/points/search",
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Error searching vector database: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Error searching vector database")
        
        # Extract results - adjust this according to your vector DB response format
        results = response.json().get("result", [])
        
        # Format to standard Document format
        documents = []
        for item in results:
            # Extract payload
            payload = item.get("payload", {})
            
            # Create document
            document = Document(
                id=str(item.get("id", "")),
                content=payload.get("content", ""),
                score=item.get("score", 0),
                source=payload.get("source", ""),
                type=payload.get("type", ""),
                metadata=payload.get("metadata", {})
            )
            documents.append(document)
        
        return documents
    except Exception as e:
        logger.error(f"Error searching vector database: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching vector database: {str(e)}")

async def query_knowledge_graph(client: httpx.AsyncClient, query: str, 
                               filter_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Query TerminusDB knowledge graph"""
    try:
        # Build the query parameters
        params = {"query": query}
        if filter_params:
            params.update(filter_params)
        
        response = await client.get(
            f"{TERMINUSDB_URL}/api/documents",
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Error querying knowledge graph: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Error querying knowledge graph")
        
        # Format to standard Document format
        results = response.json()
        documents = []
        
        for item in results:
            document = Document(
                id=item.get("id", ""),
                content=item.get("content", ""),
                source=item.get("source", ""),
                type=item.get("type", ""),
                metadata=item.get("metadata", {})
            )
            documents.append(document)
        
        return documents
    except Exception as e:
        logger.error(f"Error querying knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying knowledge graph: {str(e)}")

async def generate_llm_response(client: httpx.AsyncClient, query: str, 
                               documents: List[Document], temperature: float = 0.1) -> Dict[str, Any]:
    """Generate response using LLM service"""
    try:
        payload = {
            "query": query,
            "documents": [doc.dict() for doc in documents],
            "temperature": temperature
        }
        
        response = await client.post(f"{LLM_URL}/generate", json=payload)
        
        if response.status_code != 200:
            logger.error(f"Error generating LLM response: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Error generating LLM response")
        
        return response.json()
    except Exception as e:
        logger.error(f"Error calling LLM service: {e}")
        raise HTTPException(status_code=500, detail=f"Error calling LLM service: {str(e)}")

# Routes
@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service info"""
    return {
        "service": "EU AI Act Compliance API Gateway",
        "status": "ready" if state["ready"] else "not ready",
        "components": state["component_status"],
        "requests": {
            "processed": state["requests_processed"],
            "successful": state["successful_requests"],
            "failed": state["failed_requests"]
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if state["ready"] else "unhealthy",
        components=state["component_status"],
        uptime=time.time(),  # This should be relative to start time in a real implementation
        requests_processed=state["requests_processed"]
    )

@app.post("/search", response_model=List[Document])
async def search(request: QueryRequest, client: httpx.AsyncClient = Depends(get_http_client)):
    """Search for relevant documents using vector similarity"""
    start_time = time.time()
    state["requests_processed"] += 1
    
    try:
        # Convert query to embedding
        embeddings = await get_vector_embeddings(client, [request.query])
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings")
        
        # Search vector database
        results = await search_vector_db(
            client, 
            embeddings[0], 
            max_results=request.max_results, 
            min_score=request.min_score
        )
        
        state["successful_requests"] += 1
        state["total_processing_time"] += (time.time() - start_time)
        
        return results
    except Exception as e:
        state["failed_requests"] += 1
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge_graph", response_model=List[Document])
async def query_graph(request: QueryRequest, client: httpx.AsyncClient = Depends(get_http_client)):
    """Search the knowledge graph for structured information"""
    start_time = time.time()
    state["requests_processed"] += 1
    
    try:
        results = await query_knowledge_graph(client, request.query, request.filter)
        
        state["successful_requests"] += 1
        state["total_processing_time"] += (time.time() - start_time)
        
        return results
    except Exception as e:
        state["failed_requests"] += 1
        logger.error(f"Error in knowledge graph query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compliance_query", response_model=Dict[str, Any])
async def compliance_query(request: ComplianceQueryRequest, client: httpx.AsyncClient = Depends(get_http_client)):
    """Full compliance query workflow: search, retrieve context, generate response"""
    start_time = time.time()
    state["requests_processed"] += 1
    
    try:
        # 1. Get embedding for query
        embeddings = await get_vector_embeddings(client, [request.query])
        if not embeddings or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings")
        
        # 2. Search vector database for similar content
        vector_results = await search_vector_db(
            client, 
            embeddings[0], 
            max_results=request.max_results, 
            min_score=request.min_score
        )
        
        # 3. Query knowledge graph for structured information if appropriate
        kg_results = []
        if request.filter:
            try:
                kg_results = await query_knowledge_graph(client, request.query, request.filter)
            except Exception as e:
                logger.warning(f"Knowledge graph query failed, continuing with vector results only: {e}")
        
        # 4. Combine results, prioritizing higher scores
        all_documents = vector_results + kg_results
        all_documents.sort(key=lambda x: x.score if x.score is not None else 0, reverse=True)
        
        if len(all_documents) > request.max_results:
            all_documents = all_documents[:request.max_results]
        
        # 5. Generate response using LLM with context documents
        llm_response = await generate_llm_response(
            client,
            request.query,
            all_documents,
            temperature=request.temperature or 0.1
        )
        
        # 6. Prepare final response
        response = {
            "answer": llm_response["response"],
            "model": llm_response["model"],
            "provider": llm_response["provider"],
            "processing_time": time.time() - start_time,
            "sources": llm_response.get("sources", []),
            "context_documents": [doc.dict() for doc in all_documents]
        }
        
        state["successful_requests"] += 1
        state["total_processing_time"] += (time.time() - start_time)
        
        return response
    except Exception as e:
        state["failed_requests"] += 1
        logger.error(f"Error in compliance query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system_info", response_model=Dict[str, Any])
async def system_info(client: httpx.AsyncClient = Depends(get_http_client)):
    """Get information about all components in the system"""
    try:
        component_info = {}
        
        # Get TerminusDB info
        try:
            resp = await client.get(f"{TERMINUSDB_URL}/api/info")
            if resp.status_code == 200:
                component_info["terminusdb"] = resp.json()
            else:
                component_info["terminusdb"] = {"status": "error", "code": resp.status_code}
        except Exception as e:
            component_info["terminusdb"] = {"status": "error", "message": str(e)}
        
        # Get Vector DB info
        try:
            resp = await client.get(f"{VECTOR_DB_URL}/collections/eu_ai_act")
            if resp.status_code == 200:
                component_info["vector_db"] = resp.json()
            else:
                component_info["vector_db"] = {"status": "error", "code": resp.status_code}
        except Exception as e:
            component_info["vector_db"] = {"status": "error", "message": str(e)}
        
        # Get Embedding Service info
        try:
            resp = await client.get(f"{EMBEDDING_URL}/")
            if resp.status_code == 200:
                component_info["embedding"] = resp.json()
            else:
                component_info["embedding"] = {"status": "error", "code": resp.status_code}
        except Exception as e:
            component_info["embedding"] = {"status": "error", "message": str(e)}
        
        # Get LLM Service info
        try:
            resp = await client.get(f"{LLM_URL}/")
            if resp.status_code == 200:
                component_info["llm"] = resp.json()
            else:
                component_info["llm"] = {"status": "error", "code": resp.status_code}
        except Exception as e:
            component_info["llm"] = {"status": "error", "message": str(e)}
        
        return {
            "gateway": {
                "status": "ready" if state["ready"] else "not ready",
                "requests_processed": state["requests_processed"],
                "successful_requests": state["successful_requests"],
                "failed_requests": state["failed_requests"],
            },
            "components": component_info
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info") 