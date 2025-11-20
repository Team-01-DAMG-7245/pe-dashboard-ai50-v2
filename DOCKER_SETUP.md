# Docker Setup Guide for Team Members

## Prerequisites

1. **Docker Desktop** installed and running
2. **Git** to clone the repository

## Initial Setup (One-Time)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd pe-dashboard-ai50
```

### 2. Create `.env` File
Create a `.env` file in the project root with your OpenAI API key:
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Index the Vector Database (REQUIRED for RAG)
Before using RAG, you need to populate the vector database:
```bash
# Option 1: Run locally (if you have Python environment)
python src/lab4/index_for_rag_all.py

# Option 2: Run in Docker (after building)
docker compose run --rm fastapi python src/lab4/index_for_rag_all.py
```

**Note:** This step is **essential** - without it, RAG will show "0 chunks" and return "Not disclosed" for everything.

### 4. Fix Docker Credential Helper (if needed)
If you get an error about `docker-credential-desktop`:
```bash
# Remove credsStore from Docker config
cat > ~/.docker/config.json << 'EOF'
{
	"auths": {},
	"currentContext": "desktop-linux"
}
EOF
```

## Running the Application

### Build and Start Services
```bash
# Build the Docker images (first time, or after changes)
docker compose build fastapi streamlit

# Start the services
docker compose up fastapi streamlit
```

### Access the Application
- **Streamlit UI**: http://localhost:8501
- **FastAPI API**: http://localhost:8002
- **API Docs**: http://localhost:8002/docs

## Troubleshooting

### RAG Shows "0 chunks"
- Make sure you ran the indexing script (step 3 above)
- Check that `data/vector_db/chroma.sqlite3` exists and has data
- Verify in logs: `docker compose logs fastapi | grep "Collection count"`

### Docker Build Fails
- Ensure Docker Desktop is running
- Check disk space: `docker system df`
- Clean build cache: `docker builder prune -f`

### Credential Helper Error
- See step 4 in "Initial Setup" above

### Vector Database Errors
- If you see "no such column: collections.topic", you need to rebuild with the updated Dockerfile
- Make sure ChromaDB versions match (0.5.0)

## Quick Start (Complete Sequence)
```bash
# 1. Clone and navigate
git clone <repo> && cd pe-dashboard-ai50

# 2. Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env

# 3. Index vector database (IMPORTANT!)
python src/lab4/index_for_rag_all.py

# 4. Build and run
docker compose build fastapi streamlit
docker compose up fastapi streamlit
```

## Optional: AWS S3 Access
If you need S3 access for storing data:
- Configure AWS CLI: `aws configure`
- Or set up credentials in `~/.aws/credentials`

## What Each Service Does
- **fastapi**: Backend API with RAG and structured dashboard endpoints
- **streamlit**: Frontend UI for generating dashboards

