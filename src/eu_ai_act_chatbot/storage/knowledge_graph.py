from neo4j import GraphDatabase, Driver, Session, Transaction, Result
import re
from typing import List, Dict, Any, Optional
import logging

from ..config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KnowledgeGraph:
    """Handles interactions with the Neo4j knowledge graph."""
    def __init__(self):
        if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
            raise ValueError("Neo4j URI, Username, and Password must be set.")

        logging.info(f"Initializing KnowledgeGraph connection to: {NEO4J_URI}")
        try:
            self.driver: Driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            # Verify connection
            self.driver.verify_connectivity()
            logging.info("Successfully connected to Neo4j.")
            self._ensure_constraints()
        except Exception as e:
            logging.exception("Failed to initialize Neo4j connection.")
            raise RuntimeError("Neo4j connection failed") from e

    def close(self):
        """Closes the Neo4j driver connection."""
        if self.driver:
            logging.info("Closing Neo4j connection.")
            self.driver.close()

    def _ensure_constraints(self):
        """Ensures necessary constraints are created in the database."""
        constraints = [
            "CREATE CONSTRAINT unique_article_number IF NOT EXISTS FOR (a:Article) REQUIRE a.number IS UNIQUE",
            "CREATE CONSTRAINT unique_paragraph_id IF NOT EXISTS FOR (p:Paragraph) REQUIRE p.id IS UNIQUE"
        ]
        try:
            with self.driver.session(database="neo4j") as session: # Use default database 'neo4j'
                for constraint in constraints:
                    logging.info(f"Applying constraint: {constraint}")
                    session.run(constraint)
                logging.info("Database constraints ensured.")
        except Exception as e:
            logging.exception("Failed to ensure database constraints.")
            # Decide if this should be a fatal error

    def store_articles(self, articles: List[Dict[str, Any]]) -> None:
        """Stores articles and their relationships in Neo4j."""
        logging.info(f"Starting to store {len(articles)} articles in Neo4j.")
        processed_articles = 0
        processed_paragraphs = 0
        processed_refs = 0

        # Using managed transactions for robustness
        try:
            with self.driver.session(database="neo4j") as session: # Use default database 'neo4j'
                 # Store nodes (Articles, Paragraphs)
                nodes_result = session.execute_write(self._create_article_and_paragraph_nodes, articles)
                processed_articles += nodes_result["articles_created"]
                processed_paragraphs += nodes_result["paragraphs_created"]

                # Store relationships (REFERENCES)
                refs_result = session.execute_write(self._create_cross_references, articles)
                processed_refs += refs_result["references_created"]

            logging.info(f"Finished storing data in Neo4j. Processed: {processed_articles} articles, {processed_paragraphs} paragraphs, {processed_refs} references.")
        except Exception as e:
            logging.exception("Error during Neo4j data storage transaction.")
            # Handle transaction error (e.g., rollback is automatic with execute_write failure)

    @staticmethod
    def _create_article_and_paragraph_nodes(tx: Transaction, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Transaction function to create Article and Paragraph nodes."""
        articles_created = 0
        paragraphs_created = 0
        # Create Article nodes
        for article in articles:
            article_number = article.get("number")
            article_title = article.get("title", "")
            if not article_number:
                logging.warning(f"Skipping article with missing number: {article}")
                continue

            # Using MERGE ensures we don't create duplicates based on the constraint
            article_query = """
                MERGE (a:Article {number: $number})
                ON CREATE SET a.title = $title
                ON MATCH SET a.title = $title // Update title if article exists
            """
            tx.run(article_query, number=article_number, title=article_title)
            articles_created += 1 # Counts merges/creates

            # Create Paragraph nodes and CONTAINS relationships
            for para in article.get("paragraphs", []):
                para_number = para.get("number")
                para_text = para.get("text", "")
                if not para_number or not para_text:
                     logging.warning(f"Skipping paragraph in Article {article_number} with missing number/text: {para}")
                     continue

                para_id = f"article_{article_number}_para_{para_number}"
                para_query = """
                    MATCH (a:Article {number: $article_number})
                    MERGE (p:Paragraph {id: $para_id})
                    ON CREATE SET p.number = $para_number, p.text = $text
                    ON MATCH SET p.number = $para_number, p.text = $text // Update if paragraph exists
                    MERGE (a)-[:CONTAINS]->(p)
                """
                tx.run(para_query,
                    article_number=article_number,
                    para_id=para_id,
                    para_number=para_number,
                    text=para_text
                )
                paragraphs_created += 1 # Counts merges/creates
        return {"articles_created": articles_created, "paragraphs_created": paragraphs_created}

    @staticmethod
    def _create_cross_references(tx: Transaction, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Transaction function to create REFERENCES relationships between paragraphs and articles."""
        references_created = 0
        # Create cross-references
        for article in articles:
            article_number = article.get("number")
            if not article_number:
                 continue # Should have been logged previously

            for para in article.get("paragraphs", []):
                para_number = para.get("number")
                para_text = para.get("text", "")
                if not para_number or not para_text:
                     continue # Should have been logged previously

                para_id = f"article_{article_number}_para_{para_number}"

                # Look for references like "Article 123"
                # Using a more specific regex to avoid matching numbers in other contexts
                refs = re.findall(r'[Aa]rticle\s+(\d+)', para_text)
                unique_refs = set(refs)

                for ref_number in unique_refs:
                    if ref_number != article_number:  # Don't self-reference article
                        ref_query = """
                            MATCH (p1:Paragraph {id: $para_id})
                            MATCH (a2:Article {number: $ref_number})
                            MERGE (p1)-[r:REFERENCES]->(a2)
                        """
                        result = tx.run(ref_query,
                            para_id=para_id,
                            ref_number=ref_number
                        )
                        # Check if a relationship was actually created (or merged)
                        # This might vary based on Neo4j version and driver specifics
                        # For simplicity, we count every potential merge attempt
                        references_created += 1
                        logging.debug(f"Created reference from Para {para_id} to Article {ref_number}")
        return {"references_created": references_created}

    def search(self, keywords: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches the knowledge graph for paragraphs containing keywords."""
        if not keywords:
            logging.warning("Knowledge graph search called with no keywords.")
            return []

        logging.info(f"Performing graph search for keywords: {keywords} with limit {top_k}")
        results = []

        # Using read transaction for safety
        try:
            with self.driver.session(database="neo4j") as session:
                result: Result = session.execute_read(self._execute_keyword_search, keywords, top_k)
                for record in result:
                    results.append({
                        "article": record["article"],
                        "title": record["title"],
                        "paragraph_number": record["paragraph_number"], # Include paragraph number
                        "text": record["text"]
                    })
            logging.info(f"Graph search returned {len(results)} results.")
        except Exception as e:
            logging.exception("Error during knowledge graph keyword search.")

        return results

    @staticmethod
    def _execute_keyword_search(tx: Transaction, keywords: List[str], limit: int) -> Result:
        """Transaction function for executing the keyword search query."""
        # Use parameterization for keywords to prevent injection vulnerabilities
        # Create a condition for each keyword using CONTAINS
        keyword_conditions = " OR ".join([f"p.text CONTAINS ${f'keyword_{i}'}" for i in range(len(keywords))])

        # Create the parameter dictionary
        parameters = {f"keyword_{i}": keyword for i, keyword in enumerate(keywords)}
        parameters['limit'] = limit

        query = f"""
            MATCH (a:Article)-[:CONTAINS]->(p:Paragraph)
            WHERE {keyword_conditions}
            RETURN a.number as article, a.title as title, p.number as paragraph_number, p.text as text
            ORDER BY article, paragraph_number // Optional ordering
            LIMIT $limit
        """
        logging.debug(f"Executing Cypher: {query} with params: {parameters}")
        return tx.run(query, parameters)

    def get_article_content(self, article_number: str) -> Optional[Dict[str, Any]]:
        """Retrieves the full content (title and paragraphs) of a specific article."""
        logging.info(f"Retrieving full content for Article {article_number}.")
        if not article_number:
            logging.warning("get_article_content called with empty article_number.")
            return None

        # Using read transaction
        try:
            with self.driver.session(database="neo4j") as session:
                 record = session.execute_read(self._execute_get_article, article_number)
                 if record:
                     logging.info(f"Found content for Article {article_number}.")
                     return {
                         "article": article_number,
                         "title": record["title"],
                         "content": "\n\n".join(record["paragraphs"]) # Join paragraphs for full text
                     }
                 else:
                     logging.warning(f"Article {article_number} not found in knowledge graph.")
                     return None
        except Exception as e:
            logging.exception(f"Error retrieving content for Article {article_number}.")
            return None

    @staticmethod
    def _execute_get_article(tx: Transaction, number: str) -> Optional[Dict[str, Any]]:
        """Transaction function to get article details."""
        query = """
            MATCH (a:Article {number: $number})-[:CONTAINS]->(p:Paragraph)
            RETURN a.title as title, collect(p.text) as paragraphs
            ORDER BY toInteger(p.number) // Ensure paragraphs are ordered numerically
        """
        # Note: The query above relies on p.number being stored as a string.
        # If p.number is stored as an integer, use `ORDER BY p.number` directly.
        # The `collect()` aggregation handles the ordering before collection.
        # Let's adjust the Cypher for potentially better paragraph ordering within the collection
        query_ordered = """
            MATCH (a:Article {number: $number})-[:CONTAINS]->(p:Paragraph)
            WITH a, p ORDER BY toInteger(p.number) // Order paragraphs before collecting
            RETURN a.title as title, collect(p.text) as paragraphs
        """
        parameters = {"number": number}
        logging.debug(f"Executing Cypher: {query_ordered} with params: {parameters}")
        result = tx.run(query_ordered, parameters)
        return result.single() # Returns a single record or None

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    # Ensure environment variables are set correctly before running
    try:
        kg = KnowledgeGraph()
        print("KnowledgeGraph initialized.")

        # Example: Search for keywords
        search_results = kg.search(["risk", "system"], top_k=3)
        print("\nKeyword Search Results ('risk', 'system'):")
        if search_results:
            for res in search_results:
                print(f"  Article {res['article']} (Para {res['paragraph_number']}): {res['text'][:100]}...")
        else:
            print("  No results found.")

        # Example: Get content for a specific article (replace '6' with a valid article number)
        article_num_to_get = '6' 
        print(f"\nGetting content for Article {article_num_to_get}:")
        content = kg.get_article_content(article_num_to_get)
        if content:
            print(f"  Title: {content['title']}")
            print(f"  Content Snippet: {content['content'][:200]}...")
        else:
            print(f"  Article {article_num_to_get} not found.")

        kg.close()
        print("\nKnowledgeGraph connection closed.")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except RuntimeError as re:
        print(f"Runtime Error: {re}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}") 