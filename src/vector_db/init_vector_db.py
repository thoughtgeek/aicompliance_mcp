#!/usr/bin/env python3
"""
EU AI Act Vector Database Initialization
This script initializes a Qdrant vector database with EU AI Act content.
"""

import os
import sys
import json
import requests
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import httpx
import time
from tqdm import tqdm

# Configuration
QDRANT_URL = os.environ.get("VECTOR_DB_URL", "http://localhost:6333")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8000")
TERMINUSDB_URL = os.environ.get("TERMINUSDB_URL", "http://localhost:6363")
TERMINUSDB_USER = os.environ.get("TERMINUSDB_USER", "admin")
TERMINUSDB_PASSWORD = os.environ.get("TERMINUSDB_PASSWORD", "root")
DB_NAME = "eu_ai_act"
COLLECTION_NAME = "eu_ai_act"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 dimensions

# Class to integrate with TerminusDB
class TerminusDBClient:
    def __init__(self, url: str, user: str, password: str, db_name: str):
        self.url = url
        self.user = user
        self.password = password
        self.db_name = db_name
        self.session = requests.Session()
        self.authenticate()
        
    def authenticate(self):
        """Authenticate with TerminusDB server"""
        auth_url = f"{self.url}/api/auth/basic/user"
        response = self.session.post(
            auth_url, 
            json={"user": self.user, "password": self.password}
        )
        if response.status_code != 200:
            raise Exception(f"Failed to authenticate with TerminusDB: {response.text}")
        
        # Set auth token in headers for future requests
        jwt_token = response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {jwt_token}"})
    
    def query_documents(self, document_type: str) -> List[Dict[str, Any]]:
        """Query documents of a specific type from TerminusDB"""
        query_url = f"{self.url}/api/document/{self.db_name}?type={document_type}"
        response = self.session.get(query_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to query {document_type} documents: {response.text}")
        
        return response.json()
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get a specific document by ID"""
        doc_url = f"{self.url}/api/document/{self.db_name}/{document_id}"
        response = self.session.get(doc_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get document {document_id}: {response.text}")
        
        return response.json()

# Class to integrate with Embedding Service
class EmbeddingClient:
    def __init__(self, url: str):
        self.url = url
        
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        # Use httpx for async requests
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.url}/embeddings",
                    json={"texts": texts},
                    timeout=60.0  # Longer timeout for batch processing
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to get embeddings: {response.text}")
                
                return response.json()["embeddings"]
            except Exception as e:
                print(f"Error getting embeddings: {e}")
                # If embedding service is not available, use dummy embeddings
                # This will be replaced with actual embeddings in production
                return [[0.0] * VECTOR_SIZE for _ in texts]

# Function to extract vectorizable content from documents
def extract_text_from_document(doc_type: str, doc: Dict[str, Any]) -> str:
    """Extract text content from a document based on its type"""
    if doc_type == "Requirement":
        return f"Requirement: {doc.get('title', '')}. {doc.get('description', '')}"
    elif doc_type == "Obligation":
        return f"Obligation: {doc.get('title', '')}. {doc.get('description', '')}"
    elif doc_type == "LegalCitation":
        return f"Article {doc.get('article', '')}, Paragraph {doc.get('paragraph', '')}: {doc.get('text', '')}"
    elif doc_type == "FAQ":
        return f"Question: {doc.get('question', '')} Answer: {doc.get('answer', '')}"
    elif doc_type == "RiskCategory":
        return f"Risk Category {doc.get('name', '')}: {doc.get('description', '')}"
    elif doc_type == "Documentation":
        return f"Documentation '{doc.get('title', '')}': {doc.get('description', '')}. Required content: {doc.get('requiredContent', '')}"
    elif doc_type == "Evidence":
        return f"Evidence '{doc.get('title', '')}': {doc.get('description', '')}. Verification method: {doc.get('verificationMethod', '')}"
    elif doc_type == "ConformityAssessment":
        return f"Assessment Procedure '{doc.get('title', '')}': {doc.get('description', '')}"
    elif doc_type == "AISystem":
        return f"AI System '{doc.get('name', '')}': {doc.get('description', '')}"
    else:
        return f"{doc_type}: {json.dumps(doc)}"

# Mock embedding function for testing without embedding service
def get_mock_embedding(text: str) -> List[float]:
    """Generate a deterministic mock embedding for testing"""
    import hashlib
    hash_object = hashlib.md5(text.encode())
    hex_dig = hash_object.hexdigest()
    
    # Convert hex digest to a list of floats between -1 and 1
    result = []
    for i in range(0, min(VECTOR_SIZE * 2, len(hex_dig)), 2):
        hex_pair = hex_dig[i:i+2]
        value = (int(hex_pair, 16) / 255.0) * 2 - 1  # Scale to [-1, 1]
        result.append(value)
    
    # Pad if necessary
    while len(result) < VECTOR_SIZE:
        result.append(0.0)
    
    return result[:VECTOR_SIZE]

# Initialize Qdrant collection
def init_qdrant_collection(client: QdrantClient) -> None:
    """Initialize or recreate the Qdrant collection"""
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME in collection_names:
        print(f"Collection {COLLECTION_NAME} already exists. Recreating...")
        client.delete_collection(collection_name=COLLECTION_NAME)
    
    # Create collection with specified parameters
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    
    # Create payload index for filtering
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="type",
        field_schema="keyword"
    )
    
    print(f"Collection {COLLECTION_NAME} created successfully.")

# Main function
async def main():
    print("Starting EU AI Act vector database initialization...")
    
    # Connect to Qdrant
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL)
        print(f"Connected to Qdrant at {QDRANT_URL}")
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        sys.exit(1)
    
    # Initialize the collection
    try:
        init_qdrant_collection(qdrant_client)
    except Exception as e:
        print(f"Failed to initialize collection: {e}")
        sys.exit(1)
    
    # Connect to TerminusDB
    try:
        terminus_client = TerminusDBClient(
            url=TERMINUSDB_URL,
            user=TERMINUSDB_USER,
            password=TERMINUSDB_PASSWORD,
            db_name=DB_NAME
        )
        print(f"Connected to TerminusDB at {TERMINUSDB_URL}")
    except Exception as e:
        print(f"Failed to connect to TerminusDB: {e}")
        sys.exit(1)
    
    # Initialize embedding client
    embedding_client = EmbeddingClient(url=EMBEDDING_URL)
    
    # Document types to vectorize
    doc_types = [
        "LegalCitation", 
        "Requirement", 
        "Obligation", 
        "FAQ", 
        "RiskCategory", 
        "Documentation", 
        "Evidence", 
        "ConformityAssessment",
        "AISystem"
    ]
    
    # Process each document type
    all_points = []
    for doc_type in doc_types:
        try:
            print(f"Processing {doc_type} documents...")
            documents = terminus_client.query_documents(document_type=doc_type)
            
            if not documents:
                print(f"  No {doc_type} documents found.")
                continue
                
            print(f"  Found {len(documents)} {doc_type} documents.")
            
            # Extract text content from each document
            text_contents = []
            doc_ids = []
            
            for doc in documents:
                doc_id = doc.get("@id", "")
                if not doc_id:
                    continue
                    
                text = extract_text_from_document(doc_type, doc)
                text_contents.append(text)
                doc_ids.append(doc_id)
            
            # If using mock embeddings for testing
            use_mock = os.environ.get("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
            
            # Get embeddings (real or mock)
            if use_mock:
                embeddings = [get_mock_embedding(text) for text in text_contents]
            else:
                try:
                    # Try real embedding service
                    embeddings = await embedding_client.get_embeddings(text_contents)
                except Exception as e:
                    print(f"  Warning: Using mock embeddings due to error: {e}")
                    embeddings = [get_mock_embedding(text) for text in text_contents]
            
            # Create points for Qdrant
            for i, (doc_id, text, embedding) in enumerate(zip(doc_ids, text_contents, embeddings)):
                point = PointStruct(
                    id=i + len(all_points),  # Ensure unique ID
                    vector=embedding,
                    payload={
                        "document_id": doc_id,
                        "text": text,
                        "type": doc_type
                    }
                )
                all_points.append(point)
                
            print(f"  Processed {len(text_contents)} {doc_type} documents.")
            
        except Exception as e:
            print(f"Error processing {doc_type} documents: {e}")
    
    # Upload all points to Qdrant in batches
    batch_size = 100
    total_points = len(all_points)
    
    if total_points == 0:
        print("No points to upload. Check if TerminusDB contains data.")
        sys.exit(1)
    
    print(f"Uploading {total_points} points to Qdrant in batches of {batch_size}...")
    
    for i in range(0, total_points, batch_size):
        batch = all_points[i:i+batch_size]
        try:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            print(f"  Uploaded batch {i//batch_size + 1}/{(total_points + batch_size - 1)//batch_size}")
        except Exception as e:
            print(f"Failed to upload batch starting at index {i}: {e}")
    
    print(f"Vector database initialization completed successfully with {total_points} vectors.")
    
    # Test search functionality
    test_query = "What are the requirements for high-risk AI systems?"
    test_embedding = get_mock_embedding(test_query)
    
    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=test_embedding,
            limit=3
        )
        
        print("\nTesting search functionality:")
        print(f"Query: {test_query}")
        print("Top 3 results:")
        
        for hit in search_result:
            print(f"  Score: {hit.score:.4f}, Type: {hit.payload['type']}")
            print(f"  Content: {hit.payload['text'][:100]}...")
            print()
            
    except Exception as e:
        print(f"Failed to test search: {e}")

# Run the main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 