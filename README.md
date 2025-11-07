# MCP Tools Demo

A Model Context Protocol (MCP) server that provides web search and RAG (Retrieval-Augmented Generation) capabilities using LlamaIndex and Linkup.

## Features

- **Web Search**: Search the web using Linkup API with sourced answers
- **RAG Workflow**: Query documents using a RAG pipeline with Ollama and HuggingFace embeddings
- **MCP Protocol**: Standard MCP server implementation using FastMCP

## Prerequisites

- [Docker](https://www.docker.com/) installed and running
- Python 3.10 or higher (for test client only)
- [Ollama](https://ollama.ai/) installed and running on host (for local LLM)
- Linkup API key (for web search)
- Documents in the `data/` directory (for RAG functionality)

## Installation

### Build Docker Image

```bash
# Build the Docker image
docker build -t mcp-tools-demo .
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your configuration:
   ```env
   LINKUP_API_KEY=your_linkup_api_key_here
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=gemma:2b
   EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
   DATA_DIR=./data
   ```

3. Ensure Ollama is running:
   ```bash
   ollama serve
   ```

4. Pull the required model:
   ```bash
   ollama pull gemma:2b
   ```
   Note: Using `gemma:2b` (smaller, faster). You can also use `llama3.2` if you have more memory.

5. Add documents to the `data/` directory for RAG functionality.

## Usage

### Quick Start

1. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your LINKUP_API_KEY
   ```

2. **Ensure Ollama is running on host:**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # If not running, start it:
   ollama serve
   
   # Pull required model (if not already installed):
   ollama pull gemma:2b
   ```

3. **Add documents to data directory:**
   ```bash
   # Place your PDFs, text files, etc. in the data/ directory
   # Example: cp your_document.pdf data/
   ```

4. **Run the MCP Server using Docker:**
   ```bash
   docker run -it --rm mcp-tools-demo
   ```

   You should see:
   ```
   Loading documents from: /app/data
   Supported formats: PDF, TXT, MD, DOCX, and more...
   Loaded 1 document(s) from /app/data
   Document index created successfully
   MCP server starting...
   ```

### Running the MCP Server (Docker Only)

The MCP server **must** be run using Docker:

```bash
docker run -it --rm mcp-tools-demo
```

**Note:** 
- The `.env` file and `data/` directory are copied into the Docker image during build
- **Important:** Rebuild the image if you change `.env` or add/change documents: `docker build -t mcp-tools-demo .`

**What happens:**
- Loads all documents from `data/` directory (PDFs, TXT, MD, etc.)
- Extracts text and generates embeddings
- Creates a searchable vector index
- Starts MCP server on stdio transport
- Ready to accept queries from clients

**Note:** 
- The server will block and wait for MCP protocol messages. Use Ctrl+C to stop.
- Make sure Ollama is running on your host machine (not in Docker)
- The container connects to host Ollama via `host.docker.internal:11434`

### Running the Test Client (Python)

The test client runs directly with Python (not Docker):

**First, install dependencies:**
```bash
pip install -r requirements.txt
```

**Then run the test client:**
```bash
python -m test_mcp_client.client_example
```

**Note:** Make sure the MCP server (Docker container) is running before starting the test client.

This demonstrates:
- Listing available tools
- Calling the `search_web` tool for web searches
- Calling the `query_documents` tool for RAG queries

**Expected output:**
```
Available tools:
  - search_web: Perform a web search and return sourced answers...
  - query_documents: Answer questions using RAG workflow...

Example 1: Web Search
Query: 'What is Python programming?'
Result: [Search results...]

Example 2: RAG Query
Query: 'Tell me about DeepSeek'
Result: [Answer based on your documents...]
```

### Available Tools

#### `search_web`

Perform a web search and return sourced answers.

**Parameters:**
- `query` (str): The search query

**Example:**
```python
result = await client.call_tool("search_web", {"query": "What is Python?"})
```

#### `query_documents`

Answer questions using RAG workflow with documents from the data directory.

**Parameters:**
- `query` (str): The question to answer

**Example:**
```python
result = await client.call_tool("query_documents", {"query": "Tell me about DeepSeek"})
```

## Project Structure

```
.
├── mcp_app/                    # MCP application package
│   ├── __init__.py
│   ├── main.py                 # MCP server with tool definitions
│   └── document_workflow.py     # RAG workflow implementation
├── test_mcp_client/            # Test client package
│   ├── __init__.py
│   └── client_example.py        # Example MCP client
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── .env.example                # Environment variables template
├── README.md                   # This file
└── data/                       # Directory for documents (create this)
```

## Development

### Setting up Development Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Run linter
ruff check .

# Format code
black .

# Type checking
mypy .
```

### Running Tests

```bash
pytest
```

## Architecture

### RAG Workflow

The RAG workflow consists of three steps:

1. **Process Documents**: Load and index documents from a directory
2. **Find Context**: Retrieve relevant document sections for a query
3. **Generate Answer**: Synthesize a response using retrieved context

### MCP Server

The server uses FastMCP for easy tool registration and stdio transport for communication.

## Troubleshooting

### Ollama Connection Issues

- Ensure Ollama is running on host: `ollama serve`
- Docker container uses `http://host.docker.internal:11434` to connect to host Ollama
- Verify connection: `curl http://localhost:11434/api/tags` (from host)

### Document Index Issues

- Ensure documents exist in the `data/` directory
- Check that the directory path in `.env` is correct
- The index is created on server startup

### Linkup API Issues

- Verify your API key is set in `.env`
- Check your Linkup API quota and limits

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [LlamaIndex](https://www.llamaindex.ai/) for RAG capabilities
- [Ollama](https://ollama.ai/) for local LLM inference
- [Linkup](https://linkup.ai/) for web search
- [MCP](https://modelcontextprotocol.io/) for the protocol specification

# mcp-tools-demo
