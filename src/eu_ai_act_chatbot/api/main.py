from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from mangum import Mangum
import logging
import time
from contextlib import asynccontextmanager

# Import components from the chatbot module
# Using absolute imports based on the assumed structure
from eu_ai_act_chatbot.storage.vector_store import VectorStore
from eu_ai_act_chatbot.storage.knowledge_graph import KnowledgeGraph
from eu_ai_act_chatbot.retrieval.hybrid_retriever import HybridRetriever
from eu_ai_act_chatbot.generation.llm_handler import LLMHandler
from eu_ai_act_chatbot.config import NEO4J_URI # For checking KG readiness

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global state dictionary to hold initialized components
state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize components
    logger.info("FastAPI application starting up...")
    try:
        logger.info("Initializing VectorStore...")
        state["vector_store"] = VectorStore()
        logger.info("VectorStore initialized.")

        logger.info("Initializing KnowledgeGraph...")
        state["knowledge_graph"] = KnowledgeGraph()
        # Add a check for KG connectivity if possible/needed
        state["knowledge_graph"].driver.verify_connectivity()
        logger.info("KnowledgeGraph initialized and connected.")

        logger.info("Initializing HybridRetriever...")
        state["retriever"] = HybridRetriever(
            vector_store=state["vector_store"],
            knowledge_graph=state["knowledge_graph"]
        )
        logger.info("HybridRetriever initialized.")

        logger.info("Initializing LLMHandler...")
        state["llm_handler"] = LLMHandler()
        logger.info("LLMHandler initialized.")

        logger.info("All components initialized successfully.")
    except Exception as e:
        logger.exception("Fatal error during component initialization.")
        # Depending on the desired behavior, you might want to exit or handle this differently
        # For now, log the error; the API endpoints will likely fail if components are missing
        state["initialization_error"] = str(e)

    yield

    # Shutdown: Clean up resources
    logger.info("FastAPI application shutting down...")
    kg: KnowledgeGraph = state.get("knowledge_graph")
    if kg:
        logger.info("Closing KnowledgeGraph connection.")
        kg.close()
    # Pinecone client and SentenceTransformer might not need explicit closing,
    # but add cleanup if necessary for specific versions or resources.
    logger.info("Shutdown complete.")


app = FastAPI(
    title="EU AI Act Compliance Chatbot",
    description="Ask questions about the EU AI Act.",
    version="0.1.0",
    lifespan=lifespan # Use the lifespan context manager
)

# Pydantic models for request and response
class Query(BaseModel):
    query: str = Field(..., description="The user's question about the EU AI Act.", example="What are the obligations for providers of high-risk AI systems?")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The AI-generated answer based on the EU AI Act context.")
    retrieved_articles: List[str] = Field([], description="List of article numbers retrieved as context.")

# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Received request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request finished: {response.status_code} in {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(f"Request failed after {process_time:.4f}s")
        # Re-raise the exception to be handled by FastAPI's exception handlers
        raise e

# Dependency function to get components (ensures they are initialized)
def get_retriever() -> HybridRetriever:
    if "initialization_error" in state:
         raise HTTPException(status_code=503, detail=f"Service Unavailable: Initialization failed - {state['initialization_error']}")
    retriever = state.get("retriever")
    if not retriever:
        raise HTTPException(status_code=503, detail="Service Unavailable: Retriever not initialized.")
    return retriever

def get_llm_handler() -> LLMHandler:
    if "initialization_error" in state:
         raise HTTPException(status_code=503, detail=f"Service Unavailable: Initialization failed - {state['initialization_error']}")
    llm_handler = state.get("llm_handler")
    if not llm_handler:
        raise HTTPException(status_code=503, detail="Service Unavailable: LLM handler not initialized.")
    return llm_handler

@app.post("/chat", response_model=ChatResponse)
async def chat(
    query: Query,
    retriever: HybridRetriever = Depends(get_retriever),
    llm_handler: LLMHandler = Depends(get_llm_handler)
) -> ChatResponse:
    """Receives a user query, performs hybrid retrieval, and generates an answer."""
    logger.info(f"Processing chat query: '{query.query[:50]}...'")
    try:
        # 1. Get context from hybrid search
        start_retrieval = time.time()
        context = retriever.search(query.query)
        retrieval_time = time.time() - start_retrieval
        retrieved_article_numbers = [item.get('article', 'N/A') for item in context]
        logger.info(f"Retrieval completed in {retrieval_time:.4f}s. Found context from articles: {retrieved_article_numbers}")

        # 2. Generate response using LLM
        start_generation = time.time()
        ai_response = llm_handler.generate_response(query.query, context)
        generation_time = time.time() - start_generation
        logger.info(f"LLM generation completed in {generation_time:.4f}s.")

        return ChatResponse(response=ai_response, retrieved_articles=retrieved_article_numbers)

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions from dependencies
        raise http_exc
    except Exception as e:
        logger.exception("An unexpected error occurred during chat processing.")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    # Check if components are initialized (basic check)
    if "initialization_error" in state:
         return {"status": "unhealthy", "reason": f"Initialization failed: {state['initialization_error']}"}
    if not all(k in state for k in ["vector_store", "knowledge_graph", "retriever", "llm_handler"]):
        return {"status": "unhealthy", "reason": "Components not fully initialized"}

    # Add more specific checks if needed (e.g., ping Neo4j, check Pinecone status)
    try:
         state["knowledge_graph"].driver.verify_connectivity()
         # Add a Pinecone check if feasible (e.g., describe index stats)
         state["vector_store"].index.describe_index_stats()
    except Exception as e:
         logger.error(f"Health check failed during component check: {e}")
         return {"status": "unhealthy", "reason": f"Component connectivity check failed: {type(e).__name__}"}

    return {"status": "healthy"}

# Mangum adapter for AWS Lambda
# Only create the handler if Mangum is installed
try:
    handler = Mangum(app)
    logger.info("Mangum handler created for AWS Lambda compatibility.")
except NameError:
    handler = None
    logger.info("Mangum not installed or FastAPI app instance not found. Lambda handler not created.") 