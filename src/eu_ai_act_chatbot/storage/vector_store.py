from pinecone import Pinecone, ServerlessSpec, PodSpec
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import time

from ..config import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT, # Note: Environment might be deprecated for Serverless
    EMBEDDING_MODEL,
    VECTOR_INDEX_NAME
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
UPSERT_BATCH_SIZE = 100
# Specify the Pinecone environment (cloud and region) if using Serverless
# Example: cloud='aws', region='us-east-1'
# These should ideally come from config or environment variables
PINECONE_CLOUD = 'aws' # Or 'gcp', 'azure' - Replace with your cloud
PINECONE_REGION = 'us-east-1' # Replace with your region

class VectorStore:
    """Handles interactions with the Pinecone vector store."""
    def __init__(self):
        if not all([PINECONE_API_KEY, PINECONE_ENVIRONMENT]):
            raise ValueError("Pinecone API Key and Environment must be set.")

        logging.info(f"Initializing VectorStore for index '{VECTOR_INDEX_NAME}'")
        logging.info(f"Using embedding model: {EMBEDDING_MODEL}")

        # Initialize embedding model
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logging.info(f"Embedding model loaded. Dimension: {self.dimension}")
        except Exception as e:
            logging.exception("Failed to load SentenceTransformer model.")
            raise RuntimeError(f"Failed to load model {EMBEDDING_MODEL}") from e

        # Initialize Pinecone client (v3 syntax)
        try:
            self.pc = Pinecone(api_key=PINECONE_API_KEY)
            self._create_index_if_not_exists()
            self.index = self.pc.Index(VECTOR_INDEX_NAME)
            logging.info(f"Successfully connected to Pinecone index '{VECTOR_INDEX_NAME}'.")
            # Optional: Log index stats
            try:
                 stats = self.index.describe_index_stats()
                 logging.info(f"Index stats: {stats}")
            except Exception as stat_e:
                 logging.warning(f"Could not retrieve index stats: {stat_e}")

        except Exception as e:
            logging.exception("Failed to initialize Pinecone connection.")
            raise RuntimeError("Pinecone initialization failed") from e

    def _create_index_if_not_exists(self):
        """Creates the Pinecone index if it doesn't already exist."""
        # Get list of all indexes
        indexes = self.pc.list_indexes()

        # In Pinecone SDK v3, list_indexes() returns a list of index names directly
        if VECTOR_INDEX_NAME not in indexes:
            logging.info(f"Index '{VECTOR_INDEX_NAME}' not found. Creating index...")
            try:
                # Choose spec based on environment requirements (Serverless vs Pod-based)
                # Using Serverless as an example, adjust if using Pods
                self.pc.create_index(
                    name=VECTOR_INDEX_NAME,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=PINECONE_CLOUD,
                        region=PINECONE_REGION
                    )
                    # If using Pods:
                    # spec=PodSpec(
                    #     environment=PINECONE_ENVIRONMENT, # Required for Pods
                    #     pod_type="p1.x1", # Example pod type
                    #     pods=1
                    # )
                )
                # Wait for index to be ready
                while not self.pc.describe_index(VECTOR_INDEX_NAME).status['ready']:
                    logging.info("Waiting for index to become ready...")
                    time.sleep(5)
                logging.info(f"Index '{VECTOR_INDEX_NAME}' created successfully.")
            except Exception as e:
                logging.exception(f"Failed to create Pinecone index '{VECTOR_INDEX_NAME}'.")
                raise RuntimeError("Index creation failed") from e
        else:
            logging.info(f"Index '{VECTOR_INDEX_NAME}' already exists.")

    def store_articles(self, articles: List[Dict[str, Any]]) -> None:
        """Stores article paragraphs as vectors in Pinecone."""
        logging.info(f"Starting to store {len(articles)} articles in Pinecone.")
        vectors_to_upsert = []
        processed_paragraphs = 0

        for article in articles:
            article_number = article.get("number", "N/A")
            article_title = article.get("title", "N/A")

            if not article.get("paragraphs"):
                logging.warning(f"Article {article_number} has no paragraphs to store.")
                continue

            for para in article["paragraphs"]:
                para_number = para.get("number", "N/A")
                text = para.get("text", "")

                if not text:
                    logging.warning(f"Paragraph {para_number} in Article {article_number} has empty text. Skipping.")
                    continue

                try:
                    # Encode text
                    embedding = self.model.encode(text).tolist() # Ensure it's a list

                    # Prepare metadata - ensure values are suitable types (str, int, float, bool, list[str])
                    metadata = {
                        "article": str(article_number),
                        "title": str(article_title)[:512], # Truncate title if needed
                        "paragraph": str(para_number),
                        "text": text[:1000]  # Truncate text for metadata, Pinecone has limits
                    }

                    # Create vector record for upsert (v3 uses dictionary format)
                    vector_id = f"article_{article_number}_para_{para_number}"
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": metadata
                    })
                    processed_paragraphs += 1

                    # Batch upsert to Pinecone
                    if len(vectors_to_upsert) >= UPSERT_BATCH_SIZE:
                        logging.info(f"Upserting batch of {len(vectors_to_upsert)} vectors...")
                        self._upsert_batch(vectors_to_upsert)
                        vectors_to_upsert = []  # Clear for next batch

                except Exception as e:
                    logging.error(f"Error processing paragraph {para_number} in Article {article_number}: {e}", exc_info=True)
                    # Decide whether to skip or raise the error

        # Upsert any remaining vectors
        if vectors_to_upsert:
            logging.info(f"Upserting final batch of {len(vectors_to_upsert)} vectors...")
            self._upsert_batch(vectors_to_upsert)

        logging.info(f"Finished storing articles. Upserted {processed_paragraphs} paragraphs.")

    def _upsert_batch(self, vectors: List[Dict[str, Any]]):
        """Helper method to upsert a batch of vectors with retry logic."""
        try:
            upsert_response = self.index.upsert(vectors=vectors)
            logging.debug(f"Upsert response: {upsert_response}")
            if upsert_response.upserted_count != len(vectors):
                 logging.warning(f"Mismatch in upsert count: expected {len(vectors)}, got {upsert_response.upserted_count}")
        except Exception as e:
            logging.exception(f"Failed to upsert batch of {len(vectors)} vectors.")
            # Implement retry logic here if needed

    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Searches vectors by similarity to the query, with optional filtering."""
        if not query:
            logging.warning("Search query is empty.")
            return []

        logging.info(f"Performing vector search for query: '{query[:50]}...' with top_k={top_k}")
        try:
            query_embedding = self.model.encode(query).tolist()

            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict # Add filter if provided
            )

            logging.info(f"Vector search returned {len(results.get('matches', []))} matches.")
            return results.get("matches", []) # Return matches list or empty list
        except Exception as e:
            logging.exception("Error during vector search.")
            return [] # Return empty list on error

    def delete_index(self):
        """Deletes the Pinecone index. Use with caution!"""
        logging.warning(f"Attempting to delete Pinecone index '{VECTOR_INDEX_NAME}'!")
        try:
            self.pc.delete_index(VECTOR_INDEX_NAME)
            logging.info(f"Index '{VECTOR_INDEX_NAME}' deleted successfully.")
        except Exception as e:
            logging.exception(f"Failed to delete index '{VECTOR_INDEX_NAME}'.")

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    # This block will only run when the script is executed directly
    # Ensure environment variables are set correctly before running
    try:
        store = VectorStore()
        print("VectorStore initialized.")

        # Example search
        search_results = store.search("What are the requirements for high-risk AI systems?")
        print("\nSearch Results:")
        if search_results:
            for match in search_results:
                print(f"  Score: {match.get('score'):.4f}")
                print(f"  Metadata: {match.get('metadata')}")
                # print(f"  Text Snippet: {match.get('metadata', {}).get('text', '')[:100]}...")
                print("---")
        else:
            print("  No results found.")

        # Example: Delete index (Uncomment cautiously!)
        # print("\nAttempting to delete index...")
        # store.delete_index()

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except RuntimeError as re:
        print(f"Runtime Error: {re}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}") 