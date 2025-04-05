import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Service URLs
NEO4J_URI = os.getenv("NEO4J_URI")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT") # Pinecone environment name

# Credentials
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "eu-ai-act")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-3-5-sonnet")

# Simple validation
required_vars = [
    "OPENROUTER_API_KEY", "PINECONE_API_KEY", "NEO4J_URI",
    "PINECONE_ENVIRONMENT", "NEO4J_PASSWORD"
]
missing_vars = [var for var in required_vars if not globals().get(var)]

if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}") 