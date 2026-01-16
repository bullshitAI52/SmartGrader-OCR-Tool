#!/bin/bash
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "🚀 Checking environment..."
if [ ! -f "requirements.txt" ]; then
    echo "⚠️ requirements.txt not found!"
    exit 1
fi

echo "📦 Installing dependencies (if needed)..."
pip install -r requirements.txt > /dev/null 2>&1

echo "🚀 Starting Batch Processor..."
python batch_app.py

echo ""
read -p "Press any key to exit..."
