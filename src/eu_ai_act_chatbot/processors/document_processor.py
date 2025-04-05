from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element, Title
import re
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EUAIActProcessor:
    """Processes the EU AI Act PDF to extract structured articles and paragraphs."""
    def __init__(self, file_path: str):
        if not file_path:
            raise ValueError("File path cannot be empty.")
        self.file_path = file_path
        logging.info(f"Initialized EUAIActProcessor with file: {file_path}")

    def process(self) -> List[Dict[str, Any]]:
        """Parses the PDF document and returns a list of structured articles."""
        logging.info(f"Starting PDF processing for {self.file_path}")
        try:
            # Using hi_res strategy for better table and layout detection if needed
            # Consider adding language="eng" if specifically targeting English docs
            elements: List[Element] = partition_pdf(
                self.file_path,
                strategy="hi_res",
                infer_table_structure=True,
                languages=['eng'] # Explicitly setting language
            )
            logging.info(f"Partitioned PDF using 'hi_res' strategy. Found {len(elements)} elements.")
        except ImportError:
             logging.warning("`unstructured[local-inference]` or `unstructured[easy-ocr]` dependencies not found. Cannot use 'hi_res'. Falling back.")
             elements = partition_pdf(self.file_path, strategy="fast")
             logging.info(f"Partitioned PDF using 'fast' strategy. Found {len(elements)} elements.")
        except Exception as e:
            logging.error(f"Error partitioning PDF with 'hi_res': {e}")
            # Fallback to basic strategy if hi_res fails
            try:
                logging.info("Falling back to 'fast' partitioning strategy.")
                elements: List[Element] = partition_pdf(self.file_path, strategy="fast")
                logging.info(f"Partitioned PDF using 'fast' strategy. Found {len(elements)} elements.")
            except Exception as fallback_e:
                 logging.exception("Failed to partition PDF with both 'hi_res' and 'fast' strategies.")
                 raise RuntimeError(f"PDF partitioning failed: {fallback_e}") from fallback_e

        articles: List[Dict[str, Any]] = []
        current_article: Dict[str, Any] | None = None

        for element in elements:
            element_text = element.text.strip()
            if not element_text:
                continue

            # Detect article headers (typically marked as Title)
            # Regex adjusted to be case-insensitive and handle potential variations
            article_match = re.match(r'Article\s+(\d+)\s*[:\-–—]?\s*(.*)', element_text, re.IGNORECASE)

            # Check if element is a Title or if text strongly indicates an Article start
            is_article_title = isinstance(element, Title) or (article_match and len(element_text) < 150) # Heuristic: Titles are usually short

            if article_match and is_article_title:
                if current_article:
                    # Finalize the previous article
                    current_article["content"] = "\\n\\n".join(current_article["content_parts"]) # Join with double newline for readability
                    del current_article["content_parts"] # Remove temporary list
                    articles.append(current_article)
                    logging.debug(f"Completed processing Article {current_article['number']}")

                article_number = article_match.group(1)
                # Capture potential title text after the article number
                article_title_text = article_match.group(2).strip() if article_match.group(2) else element_text

                current_article = {
                    "number": article_number,
                    "title": article_title_text,
                    "content_parts": [], # Temporary list to build full content
                    "paragraphs": []
                }
                logging.info(f"Started processing Article {article_number}: {article_title_text}")
                # Add title itself to content parts if needed, or handle separately
                current_article["content_parts"].append(element_text)

            elif current_article:
                # Add text content to the current article
                current_article["content_parts"].append(element_text)

                # Check for numbered paragraphs at the beginning of the text element
                # This assumes paragraphs start with '1.', '2.', etc. Optional leading parenthesis.
                paragraph_match = re.match(r'^\s*(?:\()?(\d+)(?:\))?\.\s+', element_text)
                if paragraph_match:
                    paragraph_number = paragraph_match.group(1)
                    # Store the paragraph text without the leading number/dot/parenthesis
                    paragraph_text = re.sub(r'^\s*(?:\()?(\d+)(?:\))?\.\s*', '', element_text).strip()
                    if paragraph_text: # Only add if there's actual text after the number
                        current_article["paragraphs"].append({
                            "number": paragraph_number,
                            "text": paragraph_text # Store cleaned text
                        })
                        logging.debug(f"Added Paragraph {paragraph_number} to Article {current_article['number']}")

        # Add the last processed article
        if current_article:
            current_article["content"] = "\\n\\n".join(current_article["content_parts"])
            if "content_parts" in current_article: # Ensure it exists before deleting
                 del current_article["content_parts"]
            articles.append(current_article)
            logging.debug(f"Completed processing final Article {current_article['number']}")


        if not articles:
             logging.warning("No articles were extracted. Check the PDF structure and parsing logic.")
        else:
             logging.info(f"Finished processing. Found {len(articles)} articles.")
        return articles 