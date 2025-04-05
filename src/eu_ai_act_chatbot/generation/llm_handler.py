from openai import OpenAI # Use the OpenAI SDK
from typing import List, Dict, Any
import logging
import os

from ..config import OPENROUTER_API_KEY, LLM_MODEL

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Optional: Add your site URL and name for OpenRouter leaderboards
# These should ideally come from config or environment variables
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost") # Replace with your actual site URL if applicable
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME", "EU AI Act Chatbot") # Replace with your actual site name

class LLMHandler:
    """Handles interaction with the LLM via OpenRouter using the OpenAI SDK."""
    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API Key (OPENROUTER_API_KEY) must be set in environment variables.")
        self.api_key = OPENROUTER_API_KEY
        self.model = LLM_MODEL

        # Initialize the OpenAI client configured for OpenRouter
        try:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key,
            )
            logging.info(f"OpenAI client initialized for OpenRouter. Base URL: {OPENROUTER_BASE_URL}, Model: {self.model}")
            # You could potentially add a test call here to verify connectivity, e.g., list models
        except Exception as e:
            logging.exception("Failed to initialize OpenAI client for OpenRouter.")
            raise RuntimeError("OpenAI client initialization failed") from e

    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generates a response using the LLM, informed by the provided context."""
        logging.info(f"Generating LLM response for query: '{query[:50]}...'")
        logging.debug(f"Using context from {len(context)} articles.")

        if not context:
            logging.warning("LLM generation called with no context. Response quality may be poor.")
            return "I couldn't find relevant information in the EU AI Act document to answer your question based on the search. Please try rephrasing your query."

        # Format context for the prompt
        formatted_context = ""
        for article in context:
            article_num = article.get('article', 'N/A')
            title = article.get('title', '')
            content_snippet = article.get('content', '')
            formatted_context += f"--- Start Article {article_num}: {title} ---\\n"
            formatted_context += f"{content_snippet}\\n"
            formatted_context += f"--- End Article {article_num} ---\\n\\n"

        # Create messages for the OpenAI Chat API
        system_message = """
        You are an AI assistant specialized in the EU AI Act. Your primary function is to answer questions based *only* on the provided context from the official EU AI Act document. 
        - Be precise and factual.
        - Cite the specific Article number(s) (e.g., Article 5) that support your answer. 
        - If the answer cannot be found in the provided context, state that clearly. Do not infer or provide information beyond the given text.
        - Structure your answer clearly. Start with the direct answer, followed by supporting details and citations.
        - Do not apologize for not finding information if it's not in the context.
        """
        user_prompt = f"""
        Here is the relevant context from the EU AI Act:

        {formatted_context}

        Based *only* on the context provided above, please answer the following question:

        Question: {query}

        Answer:
        """

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ]

        # Optional headers for OpenRouter ranking
        extra_headers = {
            "HTTP-Referer": YOUR_SITE_URL,
            "X-Title": YOUR_SITE_NAME,
        }

        logging.debug(f"Sending request to OpenRouter via OpenAI SDK. Model: {self.model}")
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.1,
                extra_headers=extra_headers # Pass the optional headers
                # You could add extra_body here for OpenRouter specific features if needed
                # extra_body={ "models": [self.model, "fallback_model_if_needed"] }
            )

            if completion.choices and completion.choices[0].message:
                llm_response = completion.choices[0].message.content.strip()
                finish_reason = completion.choices[0].finish_reason
                logging.info(f"Received response from LLM (Length: {len(llm_response)}). Finish Reason: {finish_reason}")
                # Log usage if available (structure might differ slightly from direct OpenRouter lib)
                if completion.usage:
                     logging.debug(f"Token Usage: {completion.usage}")
                return llm_response
            else:
                logging.error(f"OpenAI SDK response structure unexpected or empty: {completion}")
                return "Error: Received an empty or invalid response from the language model."

        except Exception as e:
            # Catch specific OpenAI exceptions if needed (e.g., openai.APIError)
            logging.exception("Error calling OpenRouter via OpenAI SDK.")
            return f"Error: Failed to generate response due to an API error ({type(e).__name__})."

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    # Ensure environment variables are set correctly (OPENROUTER_API_KEY)
    try:
        llm = LLMHandler()
        print("LLMHandler initialized using OpenAI SDK for OpenRouter.")

        dummy_context = [
             {
                 "article": "6", "title": "Classification rules",
                 "content": "1. High-risk if...\n2. Does not apply if..."
             },
             {
                 "article": "5", "title": "Prohibited Practices",
                 "content": "1. Prohibited: (a) subliminal techniques..."
             }
         ]
        test_query = "What is prohibited according to Article 5?"

        print(f"\nGenerating response for query: '{test_query}'")
        response = llm.generate_response(test_query, dummy_context)
        print("\nLLM Response:")
        print(response)

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except RuntimeError as re:
        print(f"Runtime Error: {re}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}") 