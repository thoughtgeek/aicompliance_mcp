# EU AI Act Compliance Chatbot

A chatbot designed to answer questions about the EU AI Act using a hybrid retrieval approach (vector search + knowledge graph).

## Setup

1.  **Install Poetry:** If you don't have Poetry installed, follow the instructions [here](https://python-poetry.org/docs/#installation).
2.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd eu-ai-act-chatbot
    ```
3.  **Install dependencies:**
    ```bash
    poetry install
    ```
4.  **Set up environment variables:**
    - Copy the `.env.example` file to `.env`:
      ```bash
      cp .env .env # Or .env.example if you rename the template
      ```
    - Fill in your API keys and service details in the `.env` file.
5.  **Download the EU AI Act PDF:** Place the PDF file in a `data/` directory (you might need to create it) and name it `eu_ai_act.pdf`.

## Processing Data

To process the EU AI Act document and populate the vector store and knowledge graph:

```bash
poetry shell
python -m scripts.process_eu_ai_act
```

## Running the API

To run the FastAPI application locally:

```bash
poetry shell
uvicorn src.eu_ai_act_chatbot.api.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. You can access the interactive documentation at `http://127.0.0.1:8000/docs`.

## Running Tests

```bash
poetry shell
pytest
```

## Deployment (AWS Lambda)

1.  **Create a deployment package:**
    ```bash
    # Ensure dependencies are installed in the project's virtual env
    poetry install --no-dev

    # Create the package directory
    mkdir package

    # Install dependencies into the package directory
    poetry run pip install --upgrade pip
    poetry run pip install -r <(poetry export -f requirements.txt --without-hashes) --target ./package

    # Copy source code and Lambda handler
    cp -r ./src ./package/
    cp lambda_function.py ./package/

    # Create the zip file
    cd package
    zip -r ../deployment.zip .
    cd ..
    ```
2.  **Upload `deployment.zip`** to your AWS Lambda function.
3.  Ensure the Lambda function's handler is set to `lambda_function.lambda_handler`.
4.  Configure necessary environment variables in the Lambda function settings. 