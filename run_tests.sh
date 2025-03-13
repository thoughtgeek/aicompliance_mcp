#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the tests with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Return to the original directory
cd $(dirname $0) 