import PyPDF2
import re
from typing import List, Dict, Any
import logging

# Setup logging if not configured elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EUAIActProcessor:
    """Processes the EU AI Act PDF using PyPDF2 to extract structured articles.

    Note: This implementation is simpler than using unstructured and might be less
    robust for complex layouts or scanned PDFs.
    """
    def __init__(self, file_path: str):
        if not file_path:
            raise ValueError("File path cannot be empty.")
        self.file_path = file_path
        self.logger = logging.getLogger(__name__) # Use standard logging
        self.logger.info(f"Initialized EUAIActProcessor (PyPDF2) with file: {file_path}")

    def process(self) -> List[Dict[str, Any]]:
        """Process EU AI Act document and extract structured articles using PyPDF2"""
        self.logger.info(f"Processing EU AI Act with PyPDF2: {self.file_path}")

        articles: List[Dict[str, Any]] = []
        current_article: Dict[str, Any] | None = None
        full_doc_text = ""

        try:
            with open(self.file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                self.logger.info(f"PDF has {len(reader.pages)} pages.")

                # Extract text from all pages first
                for page_num in range(len(reader.pages)):
                    try:
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            full_doc_text += page_text + "\n" # Add newline between pages
                        else:
                             self.logger.warning(f"Could not extract text from page {page_num + 1}")
                    except Exception as page_exc:
                         self.logger.error(f"Error processing page {page_num + 1}: {page_exc}")

            if not full_doc_text:
                 self.logger.error("Failed to extract any text from the PDF.")
                 return []

            # Process the extracted text line by line
            lines = full_doc_text.split('\n')
            paragraph_buffer = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue # Skip empty lines

                # Detect article headers (might need refinement based on actual PDF format)
                # This regex looks for "Article" followed by digits, potentially at the line start
                article_match = re.match(r'Article\s+(\d+)\s*(.*)', line, re.IGNORECASE)

                # Heuristic: Assume a line starting with "Article X" is a new article title
                if article_match:
                    if current_article:
                        # Finalize previous article content
                        current_article['content'] = "\n".join(current_article['content_parts'])
                        del current_article['content_parts']
                        articles.append(current_article)

                    article_number = article_match.group(1)
                    article_title_text = article_match.group(2).strip() if article_match.group(2) else line
                    self.logger.info(f"Found Article {article_number}: {article_title_text}")

                    current_article = {
                        "number": article_number,
                        "title": article_title_text,
                        "content_parts": [line], # Store lines to join later for full content
                        "paragraphs": []
                    }
                    paragraph_buffer = [] # Reset buffer for new article

                elif current_article:
                    # Add line to the current article's full content parts
                    current_article["content_parts"].append(line)

                    # Check for numbered paragraphs (e.g., "1. ...", "(1)..." )
                    paragraph_match = re.match(r'^\s*(?:\()?(\d+)(?:\))?\.\s+(.*)', line)
                    if paragraph_match:
                        # If we were buffering lines for a paragraph, store the previous one
                        if paragraph_buffer:
                             # Reconstruct paragraph text (simple join)
                             para_text_reconstructed = " ".join(paragraph_buffer).strip()
                             # Extract number from the *start* of the buffer if possible (more robust)
                             prev_para_match = re.match(r'^\s*(?:\()?(\d+)(?:\))?\.\s+(.*)', paragraph_buffer[0])
                             if prev_para_match:
                                 prev_para_num = prev_para_match.group(1)
                                 current_article["paragraphs"].append({
                                     "number": prev_para_num,
                                     "text": para_text_reconstructed
                                 })
                                 self.logger.debug(f"Stored buffered Paragraph {prev_para_num} in Article {current_article['number']}")

                        # Start a new paragraph buffer with the current line
                        paragraph_buffer = [line]

                    elif paragraph_buffer:
                         # If the line doesn't start a new numbered paragraph, append to buffer
                         paragraph_buffer.append(line)
                    # else: line is part of general content, not a numbered paragraph start

            # Add the last buffered paragraph if any
            if current_article and paragraph_buffer:
                para_text_reconstructed = " ".join(paragraph_buffer).strip()
                prev_para_match = re.match(r'^\s*(?:\()?(\d+)(?:\))?\.\s+(.*)', paragraph_buffer[0])
                if prev_para_match:
                    prev_para_num = prev_para_match.group(1)
                    current_article["paragraphs"].append({
                        "number": prev_para_num,
                        "text": para_text_reconstructed
                    })
                    self.logger.debug(f"Stored final buffered Paragraph {prev_para_num} in Article {current_article['number']}")

            # Add the last processed article
            if current_article:
                 current_article['content'] = "\n".join(current_article['content_parts'])
                 if 'content_parts' in current_article: # Ensure deletion safety
                     del current_article['content_parts']
                 articles.append(current_article)

            self.logger.info(f"Extracted {len(articles)} articles using PyPDF2.")
            if not articles:
                 self.logger.warning("No articles extracted. Check PDF content and parsing logic.")
            # You might want to inspect the first few articles/paragraphs here for sanity check
            # if articles:
            #     self.logger.debug(f"First extracted article preview: {str(articles[0])[:500]}...")

            return articles

        except FileNotFoundError:
            self.logger.exception(f"Error: PDF file not found at {self.file_path}")
            raise
        except PyPDF2.errors.PdfReadError as pdf_err:
            self.logger.exception(f"Error reading PDF file {self.file_path}: {pdf_err}")
            raise RuntimeError(f"Failed to read PDF: {pdf_err}") from pdf_err
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred during PyPDF2 processing: {e}")
            raise # Re-raise unexpected errors 