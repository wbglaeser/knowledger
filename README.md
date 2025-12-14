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
- **Entity Linking** - Merge duplicate entities (e.g., "Mozart" and "Wolfgang Amadeus Mozart")
- **Password Protected** - HTTP Basic Authentication

### 🤖 AI Features
- **Smart Categorization** - Suggests relevant categories based on content
- **Entity Recognition** - Identifies people, places, organizations, and concepts
- **Date Extraction** - Parses dates in various formats (YYYY-MM-DD, YYYY-MM, YYYY)
- **Source Detection** - Identifies information sources
- **Voice Transcription** - Converts voice messages to text using Whisper
- **Quiz Generation** - Creates contextual questions with plausible answer options

## Setup

### Option 1: Docker (If Docker is installed)

1. **Install Docker** (if not already installed):
   - macOS: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - Linux: [Docker Engine](https://docs.docker.com/engine/install/)

2. **Configure environment** - Create `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   WEB_USERNAME=admin
   WEB_PASSWORD=your_secure_password
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize database** (first time only):
   ```bash
   docker-compose exec web-ui uv run python -c "from src.database import init_db; init_db()"
   ```

Access the web UI at `http://localhost:8000`

**Useful commands:**
```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Option 2: Local Development (No Docker needed)

1. **Install dependencies** (using [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```

2. **Configure environment** - Create `.env` file (same as above)

3. **Initialize database**:
   ```bash
   uv run python -c "from src.database import init_db; init_db()"
   ```

4. **Start services** (in separate terminals):
   ```bash
   # Terminal 1: Telegram Bot
   uv run python src/main.py
   
   # Terminal 2: Web UI
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

### Merging Duplicate Entities

If the AI extracts similar entities with different names (e.g., "Mozart" and "Wolfgang Amadeus Mozart"):

1. Go to the entity detail page (e.g., `/entities/Mozart`)
2. Use the "Merge Entity" form at the bottom
3. Select the target entity to merge into (e.g., "Wolfgang Amadeus Mozart")
4. All ibits will be transferred to the target entity
5. The merged entity becomes an alias (shown but hidden from main lists)
6. The graph will now show all connections under the primary entity

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
