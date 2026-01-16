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

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting OCR Tool..."
python ocr_app.py


