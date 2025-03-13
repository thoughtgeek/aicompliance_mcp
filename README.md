# AI Compliance Documentation Generator Backend

This repository contains the FastAPI backend for the AI Compliance Documentation Generator, a system designed to help AI developers create compliance documentation like model cards and risk assessments through a conversational interface.

## Features

- **Conversational Interface**: Uses LLM to understand user intent and extract relevant information
- **Document State Management**: Tracks document completion status and guides users to provide necessary information
- **Repository Analysis**: Can extract model information directly from GitHub repositories using n8n workflows
- **Multiple Document Types**: Supports EU AI Act Model Cards, US Model Risk Assessments, and general model cards
- **Export Functionality**: Generate documents in PDF, HTML, and Markdown formats

## Architecture

The backend is built with FastAPI and is optimized for deployment to Google Cloud Run. It includes:

- **Hugging Face Inference API Integration**: for processing chat messages with a lightweight LLM
- **Supabase Storage**: for session and document state persistence
- **n8n Integration**: for triggering workflows to analyze repositories
- **Jinja2 + WeasyPrint**: for generating document exports

## API Endpoints

### Chat API
- `POST /api/chat/message`: Process user messages, analyze intent, and update document state

### Sessions API
- `GET /api/sessions/{session_id}`: Get session data
- `GET /api/sessions`: List all sessions
- `DELETE /api/sessions/{session_id}`: Delete a session

### Documents API
- `GET /api/documents/{session_id}/export`: Export a document as PDF, HTML, or Markdown
- `GET /api/documents/templates`: List available document templates
- `GET /api/documents/{session_id}/status`: Get document completion status

## Setup and Installation

### Prerequisites
- Python 3.10+
- [Optional] Docker
- Supabase account
- Hugging Face API key
- n8n.cloud account (for repository analysis)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-doc-generator-backend.git
   cd ai-doc-generator-backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the `.env.example` template:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file with your credentials.

5. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Visit `http://localhost:8000/docs` to access the API documentation.

### Docker Deployment

Build and run with Docker:

```bash
docker build -t ai-doc-generator-backend .
docker run -p 8080:8080 --env-file .env ai-doc-generator-backend
```

### Google Cloud Run Deployment

1. Set up Google Cloud secrets for your credentials:
   ```bash
   gcloud secrets create hf-api-key --data-file=/path/to/hf-api-key.txt
   gcloud secrets create supabase-url --data-file=/path/to/supabase-url.txt
   gcloud secrets create supabase-key --data-file=/path/to/supabase-key.txt
   gcloud secrets create n8n-webhook --data-file=/path/to/n8n-webhook.txt
   ```

2. Deploy using Cloud Build:
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

## Configuration

The application can be configured using environment variables:

- `HF_API_KEY`: Your Hugging Face API key
- `HF_MODEL`: Hugging Face model to use (default: mistralai/Mistral-7B-Instruct-v0.2)
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `N8N_GITHUB_WEBHOOK`: n8n webhook URL for repository analysis

## Testing

Run tests using pytest:

```bash
pytest
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.