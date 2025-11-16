# Environment Variables Setup

This document describes the required environment variables for Project ORBIT.

## Creating .env File

Create a `.env` file in the project root with the following variables:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key-here

# AWS S3 Configuration
AWS_BUCKET_NAME=quanta-ai50-data
# AWS credentials should be configured via AWS CLI or IAM role
# Run: aws configure

# MCP Server Configuration (Phase 4 - Assignment 5)
MCP_SERVER_URL=http://localhost:9000
MCP_API_KEY=optional-mcp-api-key

# Agent Configuration (Phase 4 - Assignment 5)
AGENT_TIMEOUT=30
AGENT_RETRY_ATTEMPTS=3

# Airflow Configuration (if running locally)
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Vector DB Configuration
VECTOR_DB_PATH=./data/vector_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Dashboard Generation Configuration
DASHBOARD_OUTPUT_DIR=./data/dashboards
MAX_DASHBOARD_TOKENS=2000
DASHBOARD_TEMPERATURE=0.7
```

## Required Variables

### Minimum Required
- `OPENAI_API_KEY`: Your OpenAI API key for LLM calls
- `AWS_BUCKET_NAME`: S3 bucket name for cloud storage (default: `quanta-ai50-data`)

### Optional but Recommended
- `MCP_SERVER_URL`: URL of MCP server (default: `http://localhost:9000`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Docker Environment

When running with Docker Compose, environment variables can be set in:
1. `.env` file (loaded automatically by docker-compose)
2. `docker-compose.yml` environment section
3. System environment variables

## Airflow Environment

Airflow services in docker-compose automatically load environment variables from:
- `.env` file in project root
- Environment variables set in `docker-compose.yml`

## Notes

- Never commit `.env` file to version control
- Use `.env.example` as a template (if available)
- For production, use secrets management (AWS Secrets Manager, etc.)

