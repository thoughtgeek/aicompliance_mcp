# lambda_function.py
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    # Attempt to import the Mangum handler from the FastAPI app
    # Ensure this path matches your deployment structure within the Lambda package
    from src.eu_ai_act_chatbot.api.main import handler as fastapi_handler
    logger.info("Successfully imported FastAPI handler via Mangum.")
except ImportError as e:
    logger.exception("Failed to import FastAPI handler. Ensure 'src' directory and main.py are in the deployment package and Mangum is installed.")
    # Define a fallback handler to return an error if import fails
    def fallback_handler(event, context):
        return {
            'statusCode': 500,
            'body': 'Error: Could not load the FastAPI application handler.',
            'headers': {'Content-Type': 'text/plain'}
        }
    fastapi_handler = fallback_handler
except Exception as e:
    logger.exception(f"An unexpected error occurred during handler import: {e}")
    def unexpected_error_handler(event, context):
        return {
            'statusCode': 500,
            'body': f'Error: An unexpected error occurred during import ({type(e).__name__}).',
            'headers': {'Content-Type': 'text/plain'}
        }
    fastapi_handler = unexpected_error_handler

def lambda_handler(event, context):
    """AWS Lambda entry point.

    Passes the incoming event and context to the Mangum handler,
    which translates API Gateway events into ASGI requests for FastAPI.
    """
    if not fastapi_handler:
        logger.error("FastAPI handler is not available.")
        return {
            'statusCode': 500,
            'body': 'Internal Server Error: Application handler not loaded.',
            'headers': {'Content-Type': 'text/plain'}
        }

    # Log the incoming event structure (optional, for debugging)
    # Be cautious about logging sensitive information from the event
    # logger.debug(f"Received event: {event}")

    # Call the Mangum handler
    return fastapi_handler(event, context) 