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

mcp = FastMCP('linkup-server')

# Initialize LinkupClient with API key from environment
linkup_api_key = os.getenv("LINKUP_API_KEY")

try:
    import linkup
    
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
        else:
            raise ImportError("Could not find LinkupClient or search method in linkup package")
    
    if LinkupClient and linkup_api_key and linkup_api_key.strip():
        client = LinkupClient(api_key=linkup_api_key)
        LINKUP_AVAILABLE = True
    elif not LinkupClient:
        pass
    else:
        LINKUP_AVAILABLE = False
        client = None
except (ImportError, Exception):
    LINKUP_AVAILABLE = False
    client = None

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
    try:
        workflow_result = await rag_workflow.ask(query)
        # Get the actual response from workflow result
        answer = workflow_result.result if hasattr(workflow_result, 'result') else workflow_result
        # Build complete response from streaming chunks
        full_answer = ""
        if hasattr(answer, 'async_response_gen'):
            async for text_chunk in answer.async_response_gen():
                full_answer += text_chunk
        elif hasattr(answer, 'response'):
            # Some responses have a 'response' attribute
            full_answer = str(answer.response)
        else:
            # Handle non-streaming responses
            full_answer = str(answer)
        
        if not full_answer or full_answer.strip() == "":
            return "No answer generated. Please try a different query."
        return full_answer
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    asyncio.run(rag_workflow.load_documents(str(DATA_DIR)))
    mcp.run(transport="stdio")

