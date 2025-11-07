# Data Directory

Place your documents here for RAG processing.

## Supported File Types

- PDF files (`.pdf`)
- Text files (`.txt`)
- Markdown files (`.md`)
- Word documents (`.docx`)

## Usage

Documents in this directory will be:
1. Loaded at server startup
2. Split into chunks
3. Embedded into vectors
4. Indexed for semantic search

## Example

```bash
# Add your documents
cp your_document.pdf data/
cp your_notes.txt data/

# Rebuild Docker image
docker build -t mcp-tools-demo .

# Run the server
docker run -it --rm mcp-tools-demo
```

The server will load and index all documents automatically.

