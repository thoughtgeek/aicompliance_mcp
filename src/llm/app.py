#!/usr/bin/env python3
"""
EU AI Act LLM Service
A lightweight API service for factually grounded LLM responses
"""

import os
import logging
import json
import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-service")

# Configuration
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "2000"))
DEFAULT_LLM_PROVIDER = os.environ.get("DEFAULT_LLM_PROVIDER", "openrouter")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "openai/gpt-3.5-turbo")

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Initialize the app
app = FastAPI(
    title="EU AI Act LLM Service",
    description="Lightweight factually grounded LLM generation service",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state
state = {
    "ready": True,
    "startup_time": time.time(),
    "requests_processed": 0,
    "total_tokens_processed": 0,
    "total_processing_time": 0
}

# Request models
class Document(BaseModel):
    """A document used for factual grounding"""
    id: str
    text: str

class GenerateRequest(BaseModel):
    """Request model for generating content"""
    prompt: str
    documents: Optional[List[Document]] = []
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None

class GenerateResponse(BaseModel):
    """Response model for generated content"""
    text: str
    processing_time: float
    model: str
    provider: str

class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    providers: Dict[str, bool]

# Async HTTP client
async def get_http_client():
    """Get an async HTTP client"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

# Base provider class
class LLMProvider:
    """Base class for LLM providers"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.is_available = bool(api_key.strip())
    
    async def generate(
        self,
        prompt: str,
        documents: List[Document],
        temperature: float,
        max_tokens: int,
        model: str,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Generate text based on prompt and documents"""
        raise NotImplementedError("Subclasses must implement generate")
    
    async def health_check(self, client: httpx.AsyncClient) -> bool:
        """Check if the provider is healthy"""
        return self.is_available

# OpenRouter provider class
class OpenRouterProvider(LLMProvider):
    """OpenRouter provider for LLM generation"""
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://openrouter.ai/api/v1"
    
    async def generate(
        self,
        prompt: str,
        documents: List[Document],
        temperature: float,
        max_tokens: int,
        model: str,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Generate text using OpenRouter API"""
        if not self.is_available:
            raise ValueError("OpenRouter API key not configured")
        
        # Format system message with documents if provided
        system_message = "You are a helpful AI assistant. Provide accurate information based on the following context."
        if documents:
            system_message += "\n\nContext:"
            for doc in documents:
                system_message += f"\n\n--- Document ID: {doc.id} ---\n{doc.text}\n---"
        
        # Format the messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://eu-ai-act-compliance.com"  # Replace with your actual domain
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                raise ValueError(f"OpenRouter API error: {response.status_code}")
            
            result = response.json()
            return {
                "text": result["choices"][0]["message"]["content"],
                "model": result.get("model", model),
                "provider": "openrouter"
            }
            
        except Exception as e:
            logger.error(f"OpenRouter generate error: {e}")
            raise ValueError(f"OpenRouter generate error: {e}")
    
    async def health_check(self, client: httpx.AsyncClient) -> bool:
        """Check if OpenRouter is available"""
        if not self.is_available:
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://eu-ai-act-compliance.com"
            }
            
            response = await client.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10.0
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"OpenRouter health check error: {e}")
            return False

# OpenAI provider class
class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def generate(
        self, 
        query: str,
        documents: List[Document],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """Generate a response using OpenAI API"""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        if not client:
            async with httpx.AsyncClient(timeout=60.0) as client:
                return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
        else:
            return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
        
    async def _generate(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: List[Document],
        model: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Internal method for OpenAI generation"""
        context = "\n\n".join([f"Document {i+1}:\n{doc.text}" for i, doc in enumerate(documents)])
        
        if not system_prompt:
            system_prompt = """You are an expert on the EU AI Act regulations. 
            Use ONLY the information in the provided documents to answer the question.
            If the necessary information is not present in the documents, say "I don't have enough information to answer this question."
            Always cite the specific documents you used in your answer."""
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context information:\n{context}\n\nQuestion: {query}"}
        ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = await client.post(self.base_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"OpenAI API error: {response.text}")
        
        result = response.json()
        
        return {
            "text": result["choices"][0]["message"]["content"],
            "model": model,
            "provider": "openai"
        }
    
    async def health_check(self, client: httpx.AsyncClient) -> bool:
        """Check if OpenAI API is available"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = await client.get("https://api.openai.com/v1/models", headers=headers)
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

class AnthropicProvider(LLMProvider):
    """Anthropic API provider"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def generate(
        self, 
        query: str,
        documents: List[Document],
        model: str = "claude-2.1",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """Generate a response using Anthropic API"""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        if not client:
            async with httpx.AsyncClient(timeout=60.0) as client:
                return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
        else:
            return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
    
    async def _generate(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: List[Document],
        model: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Internal method for Anthropic generation"""
        context = "\n\n".join([f"Document {i+1}:\n{doc.text}" for i, doc in enumerate(documents)])
        
        if not system_prompt:
            system_prompt = """You are an expert on the EU AI Act regulations. 
            Use ONLY the information in the provided documents to answer the question.
            If the necessary information is not present in the documents, say "I don't have enough information to answer this question."
            Always cite the specific documents you used in your answer."""
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": f"Context information:\n{context}\n\nQuestion: {query}"
            }],
            "system": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = await client.post(self.base_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Anthropic API error: {response.text}")
        
        result = response.json()
        
        return {
            "text": result["content"][0]["text"],
            "model": model,
            "provider": "anthropic"
        }
    
    async def health_check(self, client: httpx.AsyncClient) -> bool:
        """Check if Anthropic API is available"""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # This is a minimal valid request that should return quickly
            payload = {
                "model": "claude-2.1",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 1
            }
            
            response = await client.post(self.base_url, json=payload, headers=headers)
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False

class CohereProvider(LLMProvider):
    """Cohere API provider"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cohere.ai/v1"
    
    async def generate(
        self, 
        query: str,
        documents: List[Document],
        model: str = "cohere/command-nightly",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """Generate a response using Cohere API"""
        if not self.api_key:
            raise ValueError("Cohere API key not configured")
        
        if not client:
            async with httpx.AsyncClient(timeout=60.0) as client:
                return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
        else:
            return await self._generate(client, query, documents, model, temperature, max_tokens, system_prompt)
    
    async def _generate(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: List[Document],
        model: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Internal method for Cohere generation"""
        context = "\n\n".join([f"Document {i+1}:\n{doc.text}" for i, doc in enumerate(documents)])
        
        if not system_prompt:
            system_prompt = """You are an expert on the EU AI Act regulations. 
            Use ONLY the information in the provided documents to answer the question.
            If the necessary information is not present in the documents, say "I don't have enough information to answer this question."
            Always cite the specific documents you used in your answer."""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "prompt": f"{system_prompt}\n\nContext information:\n{context}\n\nQuestion: {query}",
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = await client.post(f"{self.base_url}/generate", json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Cohere API error: {response.text}")
        
        result = response.json()
        
        return {
            "text": result["text"],
            "model": model,
            "provider": "cohere"
        }
    
    async def health_check(self, client: httpx.AsyncClient) -> bool:
        """Check if Cohere API is available"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = await client.get(f"{self.base_url}/models", headers=headers)
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cohere health check failed: {e}")
            return False

# Load providers
providers = {
    "openrouter": OpenRouterProvider(OPENROUTER_API_KEY),
    "openai": OpenAIProvider(OPENAI_API_KEY),
    "anthropic": AnthropicProvider(ANTHROPIC_API_KEY),
    "cohere": CohereProvider(COHERE_API_KEY),
}

# Routes
@app.get("/")
async def root():
    """Root endpoint with service info"""
    available_providers = {name: provider.is_available for name, provider in providers.items()}
    return {
        "service": "EU AI Act LLM Service",
        "status": "ready" if state["ready"] else "initializing",
        "providers": available_providers,
        "default_provider": DEFAULT_LLM_PROVIDER,
        "default_model": DEFAULT_MODEL,
        "startup_time": state["startup_time"],
        "requests_processed": state["requests_processed"],
        "total_tokens_processed": state["total_tokens_processed"]
    }

@app.get("/health", response_model=HealthResponse)
async def health(client: httpx.AsyncClient = Depends(get_http_client)):
    """Health check endpoint"""
    provider_status = {}
    for name, provider in providers.items():
        is_healthy = await provider.health_check(client)
        provider_status[name] = is_healthy
    
    # Service is healthy if at least one provider is available
    is_healthy = any(provider_status.values())
    
    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        providers=provider_status
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    client: httpx.AsyncClient = Depends(get_http_client)
):
    """Generate content based on prompt and optionally documents"""
    # Update stats
    state["requests_processed"] += 1
    
    # Set defaults
    provider_name = request.provider or DEFAULT_LLM_PROVIDER
    temperature = request.temperature or DEFAULT_TEMPERATURE
    max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS
    model = request.model or DEFAULT_MODEL
    documents = request.documents or []
    
    # Check if provider exists
    if provider_name not in providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider_name} not supported. Available providers: {list(providers.keys())}"
        )
    
    provider = providers[provider_name]
    
    # Check if provider is available
    if not provider.is_available:
        # Try fallback to any available provider
        available_providers = [p for p_name, p in providers.items() if p.is_available]
        if not available_providers:
            raise HTTPException(
                status_code=503,
                detail="No LLM providers available"
            )
        provider = available_providers[0]
        provider_name = [name for name, p in providers.items() if p == provider][0]
    
    # Generate response
    start_time = time.time()
    try:
        result = await provider.generate(
            prompt=request.prompt,
            documents=documents,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            client=client
        )
        processing_time = time.time() - start_time
        
        # Update stats
        state["total_processing_time"] += processing_time
        # Note: We can't easily count tokens here since different providers handle token counting differently
        
        return GenerateResponse(
            text=result["text"],
            processing_time=processing_time,
            model=result.get("model", model),
            provider=result.get("provider", provider_name)
        )
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating content: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info") 