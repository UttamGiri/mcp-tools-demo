import asyncio
import os
import json
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

client = None
LINKUP_AVAILABLE = False

try:
    from linkup import LinkupClient

    if linkup_api_key and linkup_api_key.strip():
        try:
            client = LinkupClient(api_key=linkup_api_key)
            LINKUP_AVAILABLE = True
        except Exception:
            client = None
except ImportError:
    LINKUP_AVAILABLE = False

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

        if isinstance(response, dict):
            answer = response.get("answer") or response.get("text")
            if answer:
                return answer
            return json.dumps(response)[:5000]

        # Fallback to string representation (truncate if huge)
        result_str = str(response)
        return result_str[:5000]
    except Exception as e:
        return f"Error performing web search: {str(e)}"

@mcp.tool()
async def query_documents(query: str) -> str:
    """Answer questions using RAG workflow with documents from the data directory."""
    try:
        workflow_result = await rag_workflow.ask(query)
        answer = workflow_result.result if hasattr(workflow_result, 'result') else workflow_result

        # Build complete response from streaming chunks
        if hasattr(answer, 'async_response_gen'):
            full_answer = ""
            async for text_chunk in answer.async_response_gen():
                full_answer += text_chunk
        elif hasattr(answer, 'response'):
            full_answer = str(answer.response)
        else:
            full_answer = str(answer)

        full_answer = full_answer.strip()
        if not full_answer:
            return "No answer generated. Please try a different query."
        return full_answer[:5000]
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    asyncio.run(rag_workflow.load_documents(str(DATA_DIR)))
    mcp.run(transport="stdio")

