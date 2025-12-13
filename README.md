# Knowledger

An intelligent knowledge management system that captures, categorizes, and quizzes you on information through Telegram and a web interface.

## Features

### 📱 Telegram Bot
- **Text & Voice Input** - Send text messages or voice notes to store information ("ibits")
- **AI-Powered Extraction** - Automatically extracts categories, entities, dates, and sources using OpenAI
- **Quiz System** - Get AI-generated multiple-choice questions to test your knowledge
- **Commands**:
  - `/start` - Welcome message
  - `/list` - View ibits, categories, or entities
  - `/quiz` - Get a quiz question
  - `/edit` - Edit an ibit
  - `/delete` - Remove an ibit
  - `/addcat` - Add categories to an ibit
  - `/filterentity` - Filter ibits by entity

### 🌐 Web Interface
- **Dashboard** - View statistics and browse all data
- **Interactive Graph** - Visualize connections between ibits, categories, entities, dates, and sources
- **Quiz Page** - Take interactive quizzes with immediate feedback
- **Full CRUD** - Edit ibit text, source, categories, entities, and dates
- **Password Protected** - HTTP Basic Authentication

### 🤖 AI Features
- **Smart Categorization** - Suggests relevant categories based on content
- **Entity Recognition** - Identifies people, places, organizations, and concepts
- **Date Extraction** - Parses dates in various formats (YYYY-MM-DD, YYYY-MM, YYYY)
- **Source Detection** - Identifies information sources
- **Voice Transcription** - Converts voice messages to text using Whisper
- **Quiz Generation** - Creates contextual questions with plausible answer options

## Setup

1. **Install dependencies** (using [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```

2. **Configure environment** - Create `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   WEB_USERNAME=admin
   WEB_PASSWORD=your_secure_password
   ```

3. **Initialize database**:
   ```bash
   uv run python -c "from src.database import init_db; init_db()"
   ```

## Usage

### Start the Telegram Bot
```bash
uv run python src/main.py
```

### Start the Web UI
```bash
uv run python src/web_ui.py
```
Access at `http://localhost:8000`

### Example Interactions

**Text message:**
```
The Berlin Wall fell on November 9, 1989, marking the end of the Cold War according to Wikipedia
```

**AI extracts:**
- Categories: `history`, `cold war`
- Entities: `Berlin Wall`, `Cold War`
- Dates: `1989-11-09`
- Source: `Wikipedia`

## Tech Stack

- **Python 3.14** with `uv` package manager
- **SQLite** + SQLAlchemy for data storage
- **python-telegram-bot** for Telegram integration
- **FastAPI** + Jinja2 for web interface
- **OpenAI API** (GPT-4o-mini + Whisper) for AI features
- **pyvis** for graph visualization

## Database Schema

- **Ibit** - Core information unit with text and source
- **Category** - Topical classifications
- **Entity** - Named entities (people, places, concepts)
- **Date** - Temporal references
- Many-to-many relationships between all entities

## License

MIT
