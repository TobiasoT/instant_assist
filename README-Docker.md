# Docker Deployment Guide

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` with your API keys:**
   ```bash
   nano .env
   ```
   Fill in your actual API keys for:
   - `LIVEKIT_WS_URL` - Your LiveKit WebSocket URL
   - `ASSEMBLYAI_API_KEY` - AssemblyAI API key for transcription
   - `GEMINI_API_KEY` - Google Gemini API key
   - `OPENAI_API_KEY` - OpenAI API key for embeddings and LLM

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Main app: http://localhost:8000
   - 

## Alternative: Direct Docker Run

```bash
docker build -t ai-app .

docker run -d \
  -p 8000:8000 -p 8080:8080 \
  -e LIVEKIT_WS_URL="wss://your-instance.livekit.cloud" \
  -e ASSEMBLYAI_API_KEY="your_key" \
  -e GEMINI_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_key" \
  -v ai_embeddings:/app/data/embeddings_cache \
  -v ai_faiss:/app/source/cached_vector_store/muell/faiss_idx \
  -v ai_query_cache:/app/source/cached_vector_store/muell \
  --name ai-app ai-app
```
 
## Persistent Storage

The following directories are persisted as Docker volumes:
- `/app/data/embeddings_cache` - OpenAI embedding cache
- `/app/data/category_queries` - Query categorization cache
- `/app/data/persistence` - General persistence directory

## Stopping the Application

```bash
docker-compose down
```

To remove all data volumes:
```bash
docker-compose down -v
```