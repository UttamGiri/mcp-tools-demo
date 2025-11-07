import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from mcp_app.document_workflow import RAGWorkflow
from mcp.server.fastmcp import FastMCP

# Get project root directory (parent of mcp_app)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Load .env file from project root
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

# Debug: Print that we're loading from the right place
print(f"[DEBUG] Loading .env from: {env_path}", file=sys.stderr)
print(f"[DEBUG] .env exists: {env_path.exists()}", file=sys.stderr)

mcp = FastMCP('linkup-server')

# Initialize LinkupClient with API key from environment
linkup_api_key = os.getenv("LINKUP_API_KEY")
print(f"[DEBUG] LINKUP_API_KEY loaded: {'Yes' if linkup_api_key else 'No'}", file=sys.stderr)
if linkup_api_key:
    print(f"[DEBUG] API Key length: {len(linkup_api_key)} characters", file=sys.stderr)

try:
    # Try different ways to import linkup
    import linkup
    print(f"[DEBUG] Linkup module imported. Available attributes: {dir(linkup)[:5]}...", file=sys.stderr)
    
    # Try to find the client class
    if hasattr(linkup, 'LinkupClient'):
        LinkupClient = linkup.LinkupClient
    elif hasattr(linkup, 'Linkup'):
        LinkupClient = linkup.Linkup
    elif hasattr(linkup, 'Client'):
        LinkupClient = linkup.Client
    else:
        # Use the module directly if it has a search method
        if hasattr(linkup, 'search'):
            LinkupClient = None
            client = linkup
            LINKUP_AVAILABLE = True
            print(f"[INFO] Using linkup module directly", file=sys.stderr)
        else:
            raise ImportError("Could not find LinkupClient or search method in linkup package")
    
    if LinkupClient and linkup_api_key and linkup_api_key.strip():
        client = LinkupClient(api_key=linkup_api_key)
        LINKUP_AVAILABLE = True
        print(f"[INFO] Linkup client initialized successfully", file=sys.stderr)
    elif not LinkupClient:
        # Already set above
        pass
    else:
        LINKUP_AVAILABLE = False
        client = None
        print("[WARN] LINKUP_API_KEY not found in .env file", file=sys.stderr)
except ImportError as e:
    LINKUP_AVAILABLE = False
    client = None
    print(f"[WARN] Linkup package not installed: {e}", file=sys.stderr)
except Exception as e:
    LINKUP_AVAILABLE = False
    client = None
    print(f"[ERROR] Failed to initialize Linkup: {e}", file=sys.stderr)

rag_workflow = RAGWorkflow()

@mcp.tool()
def search_web(query: str) -> str:
    """Perform a web search and return sourced answers for the given query."""
    if not LINKUP_AVAILABLE or client is None:
        return "Error: Linkup web search is not available. Please install linkup package and set LINKUP_API_KEY in .env file."
    try:
        response = client.search(
            query=query,
            depth="standard",
            output_type="sourcedAnswer", 
            structured_output_schema=None,
        )
        # Handle different response types
        if hasattr(response, 'answer'):
            return response.answer
        elif hasattr(response, 'text'):
            return response.text
        elif isinstance(response, dict):
            # Extract answer from dict response
            return response.get('answer', response.get('text', str(response)[:2000]))
        else:
            # Truncate very long responses
            result_str = str(response)
            if len(result_str) > 5000:
                return result_str[:5000] + "\n\n[Response truncated due to length]"
            return result_str
    except Exception as e:
        return f"Error performing web search: {str(e)}"

@mcp.tool()
async def query_documents(query: str) -> str:
    """Answer questions using RAG workflow with documents from the data directory."""
    workflow_result = await rag_workflow.ask(query)
    # Get the actual response from workflow result
    answer = workflow_result.result if hasattr(workflow_result, 'result') else workflow_result
    # Build complete response from streaming chunks
    full_answer = ""
    if hasattr(answer, 'async_response_gen'):
        async for text_chunk in answer.async_response_gen():
            full_answer += text_chunk
    else:
        # Handle non-streaming responses
        full_answer = str(answer)
    return full_answer

if __name__ == "__main__":
    import sys as sys
    # Print to stderr to avoid interfering with MCP stdio protocol
    print(f"Loading documents from: {DATA_DIR}", file=sys.stderr)
    print("Supported formats: PDF, TXT, MD, DOCX, and more...", file=sys.stderr)
    asyncio.run(rag_workflow.load_documents(str(DATA_DIR)))
    print("MCP server starting...", file=sys.stderr)
    mcp.run(transport="stdio")

