#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Function to check if port 5001 is in use
check_port() {
    if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
        echo "Port 5001 is already in use. Please close any other applications using this port."
        exit 1
    fi
}

# Check port before starting
check_port

# Start the Flask server in the background
echo "Starting server..."
python src/api/app.py --port 5001 &
SERVER_PID=$!

# Wait for the server to start
sleep 2

# Open the default web browser
echo "Opening demo in your web browser..."
open "http://localhost:5001"

# Function to clean up when the script is terminated
cleanup() {
    echo "Shutting down server..."
    kill $SERVER_PID
    exit 0
}

# Set up trap to catch termination signal
trap cleanup INT TERM

# Keep the script running
echo "Demo is running. Press Ctrl+C to stop."
wait $SERVER_PID 