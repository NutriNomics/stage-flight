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
python -m pip install --upgrade pip --quiet

# Install requirements if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "Downloading staging"
    pip install tomli --quiet
    pip install requests --quiet
    pip install pyzipper --quiet
    echo "Downloading staging finished"
fi

if [ -f "updater.py" ]; then
    echo "Checking updates..."
    python updater.py --check
    echo "Update finished!"
fi

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt --quiet
    echo "Installing dependencies finished!"
fi

# Run main.py if it exists
if [ -f "main.py" ]; then
    echo "Running main.py..."
    python main.py
else
    echo "main.py not found!"
fi

