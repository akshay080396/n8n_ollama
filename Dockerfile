# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for psycopg2 (PostgreSQL adapter)
# and curl for Ollama healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    # Clean up APT when done to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
# This is a common pattern to leverage Docker's layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
# app.py will be mounted from the host by docker-compose, but
# a COPY here ensures the image is self-contained if run directly.
# However, for live editing with docker-compose, the volume mount takes precedence.
COPY app.py .

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application
# Use the environment variables passed from docker-compose
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]