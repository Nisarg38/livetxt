#!/bin/bash
# Setup script for LiveTxt development environment

set -e

echo "🚀 Setting up LiveTxt development environment..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv is installed: $(uv --version)"
echo ""

# Create virtual environment and install dependencies
echo "📦 Creating virtual environment..."
uv venv

echo ""
echo "✅ Virtual environment created!"
echo ""
echo "🔧 Activate the environment with:"
echo "   source .venv/bin/activate"
echo ""
echo "📚 Or with uv:"
echo "   uv shell"
echo ""
echo "🔑 Don't forget to set your OpenAI API key:"
echo "   export OPENAI_API_KEY=your_key_here"
echo ""
echo "🧪 Install dependencies:"
echo "   uv pip install -e '.[dev]'"
echo ""
echo "📦 Install additional plugins needed for examples:"
echo "   uv pip install livekit-plugins-openai livekit-plugins-deepgram livekit-plugins-cartesia livekit-plugins-silero livekit-plugins-turn-detector python-dotenv"
echo ""
echo "✨ Then run tests:"
echo "   pytest examples/ -v"
echo ""
echo "⚠️  Don't forget to set your OpenAI API key!"
echo "   export OPENAI_API_KEY=your_key_here"

