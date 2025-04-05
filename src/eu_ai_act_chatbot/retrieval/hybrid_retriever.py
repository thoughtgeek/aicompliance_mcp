from typing import List, Dict, Any, Set
import re
import logging

from ..storage.vector_store import VectorStore
from ..storage.knowledge_graph import KnowledgeGraph

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HybridRetriever:
    """Performs hybrid search using both vector similarity and knowledge graph lookups."""
    def __init__(self, vector_store: VectorStore, knowledge_graph: KnowledgeGraph):
        if not vector_store or not knowledge_graph:
            raise ValueError("VectorStore and KnowledgeGraph instances must be provided.")
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        logging.info("HybridRetriever initialized.")

    def _extract_keywords(self, query: str, min_length: int = 4) -> List[str]:
        """Extracts meaningful keywords from a query string."""
        # Basic keyword extraction: lowercase, split, remove short words
        # Consider more sophisticated methods (e.g., using NLP libraries like spaCy or NLTK for POS tagging)
        words = re.findall(r'\b\w+\b', query.lower()) # Find word boundaries
        keywords = [word for word in words if len(word) >= min_length and word.isalpha()]
        # Optional: Remove common stop words
        # from nltk.corpus import stopwords
        # stop_words = set(stopwords.words('english'))
        # keywords = [word for word in keywords if word not in stop_words]
        logging.debug(f"Extracted keywords: {keywords} from query: '{query}'")
        return list(set(keywords)) # Return unique keywords

    def search(self, query: str, top_k_vector: int = 5, top_k_graph: int = 5) -> List[Dict[str, Any]]:
        """Performs hybrid search and returns consolidated article context."""
        logging.info(f"Starting hybrid search for query: '{query[:50]}...'")

        if not query:
            logging.warning("Hybrid search called with empty query.")
            return []

        # 1. Vector Search
        logging.debug(f"Performing vector search (top_k={top_k_vector}).")
        vector_results = self.vector_store.search(query, top_k=top_k_vector)

        # Extract article numbers and collect paragraph snippets from vector results
        article_numbers: Set[str] = set()
        vector_context_snippets: Dict[str, List[str]] = {}
        for match in vector_results:
            metadata = match.get('metadata', {})
            article_num = metadata.get('article')
            para_text = metadata.get('text')
            if article_num:
                article_numbers.add(article_num)
                if para_text:
                    if article_num not in vector_context_snippets:
                         vector_context_snippets[article_num] = []
                    # Add a snippet, maybe with score? For now just text.
                    vector_context_snippets[article_num].append(f"[Vector Match Score: {match.get('score'):.3f}] {para_text}")

        logging.info(f"Vector search identified articles: {article_numbers}")

        # 2. Knowledge Graph Search
        logging.debug(f"Performing knowledge graph search (top_k={top_k_graph}).")
        keywords = self._extract_keywords(query)
        if keywords:
            graph_results = self.knowledge_graph.search(keywords, top_k=top_k_graph)
            # Add article numbers from graph results
            for result in graph_results:
                article_num = result.get("article")
                if article_num:
                    article_numbers.add(article_num)
            logging.info(f"Graph search identified additional articles: {article_numbers}")
        else:
            logging.warning("No suitable keywords extracted for graph search.")
            graph_results = []

        # 3. Retrieve Full Article Context from Knowledge Graph
        logging.info(f"Retrieving full context for {len(article_numbers)} identified articles: {article_numbers}")
        final_context: List[Dict[str, Any]] = []
        retrieved_articles = set()

        for article_num in sorted(list(article_numbers)): # Sort for consistent order
             if article_num in retrieved_articles:
                 continue # Avoid fetching the same article multiple times

             logging.debug(f"Fetching full content for Article {article_num} from KG.")
             article_content = self.knowledge_graph.get_article_content(article_num)
             if article_content:
                # Optional: Prepend vector search snippets to the full content for relevance hints
                # snippets = vector_context_snippets.get(article_num, [])
                # if snippets:
                #      article_content['retrieval_snippets'] = snippets

                final_context.append(article_content)
                retrieved_articles.add(article_num)
             else:
                 logging.warning(f"Could not retrieve full content for Article {article_num} from KG, though it was identified in search.")

        logging.info(f"Hybrid search completed. Returning context for {len(final_context)} articles.")
        return final_context 