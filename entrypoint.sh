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

# Check if the llama3 model already exists before pulling
# This prevents re-downloading on subsequent restarts
if ! ollama list | grep -q "llama3"; then
  echo "llama3 model not found. Pulling llama3 model (this may take a while)..."
  ollama pull llama3
  if [ $? -ne 0 ]; then
    echo "Failed to pull llama3 model. Check logs for details and ensure sufficient RAM."
    kill $OLLAMA_PID # Kill the background ollama serve process
    exit 1
  fi
  echo "llama3 model pulled successfully."
else
  echo "llama3 model already exists in the volume."
fi

# Wait for the background ollama serve process to keep the container alive
echo "Ollama container setup complete. Keeping server running."
wait $OLLAMA_PID