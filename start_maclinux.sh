#!/bin/bash

# Define virtual environment directory
VENV_DIR="env"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python -m venv "$VENV_DIR"
    echo "Virtual environment setup complete!"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip (optional but recommended)
python -m pip install --upgrade pip

# Install requirements if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "Downloading staging"
    pip install tomli
    pip install requests
    pip install pyzipper
    python staging.py
    rm staging.py
fi

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "Update finished!"
fi

# Run main.py if it exists
if [ -f "main.py" ]; then
    echo "Running main.py..."
    python main.py
else
    echo "main.py not found!"
fi

