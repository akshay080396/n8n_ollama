#!/bin/bash

# Start Ollama server in the background
echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$! # Store the PID of the background process

# Wait for Ollama server to be truly ready before pulling models
echo "Waiting for Ollama API to become responsive..."
ATTEMPTS=0
MAX_ATTEMPTS=60 # Roughly 5 minutes at 5-second intervals (adjust if your pull takes longer)
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 5
  ATTEMPTS=$((ATTEMPTS+1))
  if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    echo "Ollama API did not become responsive within the expected time. Exiting."
    kill $OLLAMA_PID # Kill the background ollama serve process
    exit 1
  fi
done
echo "Ollama API is responsive."

# Determine which model to use (default to GPT-NeoX 20B if not provided)
MODEL="${OLLAMA_MODEL:-gpt-oss:20b}"

# Check if the model already exists before pulling
# This prevents re-downloading on subsequent restarts
if ! ollama list | grep -q "$MODEL"; then
  echo "Model '$MODEL' not found. Pulling (this may take a while)..."
  ollama pull "$MODEL"
  if [ $? -ne 0 ]; then
    echo "Failed to pull model '$MODEL'. Check logs for details and ensure sufficient resources."
    kill $OLLAMA_PID # Kill the background ollama serve process
    exit 1
  fi
  echo "Model '$MODEL' pulled successfully."
else
  echo "Model '$MODEL' already exists in the volume."
fi

# Wait for the background ollama serve process to keep the container alive
echo "Ollama container setup complete. Keeping server running."
wait $OLLAMA_PID