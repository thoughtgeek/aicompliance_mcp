FROM python:3.9-slim

WORKDIR /app

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy schema and data import files
COPY src/schema /app/src/schema
COPY src/data_import /app/src/data_import

# Make the import script executable
RUN chmod +x /app/src/data_import/import_euaiact_data.py

# Set the entrypoint
ENTRYPOINT ["python", "/app/src/data_import/import_euaiact_data.py"] 