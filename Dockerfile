# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and source code
COPY requirements.txt .
## Do not copy .env files; use environment variables in Docker UI or CLI
COPY goodreads_list.py main.py /app/
COPY src /app/src

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command
CMD ["python", "main.py"]
