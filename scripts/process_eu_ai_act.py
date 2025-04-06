# scripts/process_eu_ai_act.py
import os
import sys
import logging
import time

# Ensure the src directory is in the Python path
# This allows importing modules from src when running the script directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR) # Assumes scripts/ is one level down from project root
sys.path.insert(0, PROJECT_DIR)

# Now we can import from src
from src.eu_ai_act_chatbot.processors.document_processor import EUAIActProcessor
from src.eu_ai_act_chatbot.storage.vector_store import VectorStore
from src.eu_ai_act_chatbot.storage.knowledge_graph import KnowledgeGraph

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
# Assumes the PDF is placed in a 'data' directory at the project root
DEFAULT_PDF_PATH = os.path.join(PROJECT_DIR, "data", "eu_ai_act.pdf")

def main(pdf_path: str = DEFAULT_PDF_PATH):
    """Processes the EU AI Act PDF and loads data into Vector Store and Knowledge Graph."""
    start_time = time.time()
    logger.info("--- Starting EU AI Act Processing Pipeline ---")

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at path: {pdf_path}")
        logger.error("Please ensure the EU AI Act PDF is placed in the 'data' directory and named 'eu_ai_act.pdf'.")
        sys.exit(1) # Exit if the source document is missing

    # 1. Process document using Unstructured
    logger.info(f"Processing document: {pdf_path}")
    try:
        processor = EUAIActProcessor(file_path=pdf_path)
        articles = processor.process()
        if not articles:
            logger.error("No articles were extracted from the document. Exiting.")
            sys.exit(1)
        logger.info(f"Successfully processed {len(articles)} articles from the document.")
    except Exception as e:
        logger.exception("Failed during document processing.")
        sys.exit(1)

    # Initialize storage components
    try:
        logger.info("Initializing Vector Store...")
        vector_store = VectorStore()
        logger.info("Initializing Knowledge Graph...")
        knowledge_graph = KnowledgeGraph()
    except Exception as e:
        logger.exception("Failed to initialize storage components (VectorStore or KnowledgeGraph). Check connections and credentials.")
        # Close KG connection if it was partially initialized
        if 'knowledge_graph' in locals() and hasattr(knowledge_graph, 'close'):
            knowledge_graph.close()
        sys.exit(1)

    # 2. Store in vector database (Pinecone)
    logger.info("Storing processed articles in Vector Store (Pinecone)...")
    try:
        vector_store.store_articles(articles)
        logger.info("Successfully stored articles in the Vector Store.")
    except Exception as e:
        logger.exception("Failed during Vector Store storage.")
        # Continue to KG storage or exit? Decided to continue for now.

    # 3. Store in knowledge graph (Neo4j)
    logger.info("Storing processed articles in Knowledge Graph (Neo4j)...")
    try:
        knowledge_graph.store_articles(articles)
        logger.info("Successfully stored articles in the Knowledge Graph.")
    except Exception as e:
        logger.exception("Failed during Knowledge Graph storage.")
    finally:
        # Ensure Neo4j connection is closed
        logger.info("Closing Knowledge Graph connection.")
        knowledge_graph.close()

    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f"--- EU AI Act Processing Pipeline Finished --- Duration: {total_time:.2f} seconds ---")

if __name__ == "__main__":
    # Allows specifying a different PDF path via command line argument if needed
    pdf_file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF_PATH
    main(pdf_path=pdf_file_path)
