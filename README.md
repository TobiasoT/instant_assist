# Instant Assist - AI Conversational System

A Python-based conversational AI system that combines real-time audio processing, agent-based task management, and vector-based document retrieval to provide intelligent, context-aware responses.

## Features

- **Real-time Audio Processing**: LiveKit integration for live audio streaming with AssemblyAI transcription
- **Agentic Task Management**: Multi-agent system with intelligent task routing and relevance scoring
- **Vector-based RAG**: FAISS-powered document retrieval with cached embeddings for fast context lookup
- **Multi-LLM Support**: OpenAI GPT and Google Gemini integration
- **Web Interface**: FastAPI-based dashboard with real-time summary board
- **File Upload & Processing**: Automatic document ingestion and indexing

## Quick Start

### Prerequisites

- Python 3.8+
- API keys for:
  - OpenAI
  - Google Gemini
  - AssemblyAI
  - LiveKit

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd coding_challange
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys:
```bash
cp .env.template .env
# Edit .env with your API keys
```

4. Run the application:
```bash
python source/web_app/app.py
```

5. Visit `http://localhost:8000` to access the web interface

## Architecture

### Core Components

- **Web Application** (`source/web_app/`): FastAPI server with lifecycle management
- **LiveKit Integration** (`source/live_kit/`): Real-time audio/video communication
- **Agent System** (`source/agentic_tasks/`): Task management and agent coordination
- **Vector Store** (`source/cached_vector_store/`): Document embeddings and retrieval
- **Chat System** (`source/chat/`): Message processing and state management

### Key Files

- `source/web_app/app.py` - Main FastAPI application
- `source/locations_and_config.py` - Configuration and path management
- `source/global_models.py` - LLM model configurations
- `source/agentic_tasks/agent_pool.py` - Agent lifecycle management
- `source/cached_vector_store/vector_store.py` - FAISS-based document search

## Configuration

The system uses `resources/config.json` for configuration, with environment variable override support:

```json
{
  "livekit_ws_url": "wss://your-livekit-url",
  "livekit_api_key": "your-api-key",
  "livekit_api_secret": "your-api-secret",
  "assemblyai_api_key": "your-assemblyai-key",
  "gemini_api_key": "your-gemini-key",
  "openai_api_key": "your-openai-key"
}
```

## Usage

### Web Interface

1. **Main Dashboard** (`/`): File upload, prompt processing, and navigation
2. **LiveKit Chat** (`/livekit`): Real-time audio conversation interface
3. **Summary Board** (`/summary_board`): Agent task results and conversation summaries

### File Upload

Upload documents through the web interface to automatically:
- Extract and chunk content
- Generate embeddings
- Update the vector store index
- Make content available for agent queries

### Agent Interaction

The system automatically:
- Routes queries to relevant agents
- Scores agent relevance
- Manages task lifecycle
- Provides context-aware responses

## Development

### Running Tests

```bash
python source/examples/first_dry_test.py
python source/web_app/test_runs/run_live_kit.py
```

### Development Commands

```bash
# Run main web application
python source/web_app/app.py

# Run LiveKit server standalone
python source/live_kit/server.py

# Test agent creation
python source/examples/test_new_agent_creation.py
```

## Planned Improvements

### Architecture Enhancements

- **Global Variable Elimination**: Refactor global state management to use dependency injection and proper state containers
- **Enhanced Agent System**: Implement more sophisticated agent types with specialized capabilities and improved coordination
- **Better State Management**: Replace global variables with proper state management patterns
- **Improved Error Handling**: Add comprehensive error handling and recovery mechanisms
- **Performance Optimization**: Optimize async operations and reduce blocking calls

### Code Quality

- **Type Safety**: Add comprehensive type hints throughout the codebase
- **Testing**: Implement proper unit and integration test suites
- **Documentation**: Expand inline documentation and API documentation
- **Configuration Management**: Improve configuration validation and management
- **Logging**: Enhance logging with structured logging and better error tracking

### Features

- **Agent Specialization**: Add domain-specific agents for different types of queries
- **Improved RAG**: Enhanced document chunking and retrieval strategies
- **Real-time Collaboration**: Better multi-user support and session management
- **Analytics**: Add usage analytics and performance monitoring
- **Scalability**: Prepare architecture for horizontal scaling

## Project Structure

```
coding_challange/
├── source/
│   ├── web_app/           # FastAPI application
│   ├── live_kit/          # LiveKit integration
│   ├── agentic_tasks/     # Agent management
│   ├── cached_vector_store/ # Vector storage
│   ├── chat/              # Message processing
│   ├── agents/            # Agent implementations
│   └── pydantic_models/   # Data models
├── resources/
│   ├── templates/         # HTML templates
│   ├── static/           # CSS/JS assets
│   └── config.json       # Configuration
├── data/                 # Runtime data and caches
└── requirements.txt      # Python dependencies
```

## Contributing

This project is under development. Current focus areas:
1. Removing global variables and improving state management
2. Enhancing the agent system with better coordination
3. Improving async operation handling
4. Adding comprehensive testing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Technical Notes

- Built with FastAPI for high-performance async web serving
- Uses FAISS for efficient vector similarity search
- Implements async/await patterns throughout for non-blocking operations
- Supports multiple LLM providers with unified interface
- Real-time communication via WebSockets and LiveKit

---

**Note**: This is an active development project. The architecture is being continuously improved with focus on removing global state dependencies and implementing better agent coordination patterns.