"""
Example MCP client to interact with the linkup-server MCP server.

This demonstrates how to call the MCP server tools from a client application.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path to import mcp_app
sys.path.insert(0, str(Path(__file__).parent.parent))

class MCPClient:
    """Simple MCP client for stdio transport."""
    
    def __init__(self, server_command: list[str]):
        """
        Initialize the MCP client.
        
        Args:
            server_command: Command to start the MCP server (e.g., ["python", "-m", "mcp_app.main"])
        """
        self.server_command = server_command
        self.process = None
        
    async def start(self):
        """Start the MCP server process."""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Read and display startup messages from stderr until server is ready
        print("Waiting for server to start...")
        
        server_ready = False
        
        async def read_stderr_until_ready():
            """Read stderr messages and wait for server to be ready"""
            nonlocal server_ready
            start_time = asyncio.get_event_loop().time()
            max_wait = 30.0  # Wait up to 30 seconds
            
            while self.process and self.process.stderr:
                try:
                    line = await asyncio.wait_for(self.process.stderr.readline(), timeout=1.0)
                    if line:
                        line_text = line.decode().strip()
                        if line_text:  # Only print non-empty lines
                            print(f"[Server]: {line_text}")
                        
                        # Look for indicators that loading is complete
                        if "prompt is loaded" in line_text or "index created" in line_text:
                            # Documents are loaded, server should be ready soon
                            await asyncio.sleep(2)
                            server_ready = True
                            asyncio.create_task(self._continue_reading_stderr())
                            break
                except asyncio.TimeoutError:
                    # Check if we've waited long enough
                    if asyncio.get_event_loop().time() - start_time > max_wait:
                        # Assume server is ready
                        server_ready = True
                        asyncio.create_task(self._continue_reading_stderr())
                        break
                except:
                    break
        
        # Wait for server to be ready
        await read_stderr_until_ready()
        
        if not server_ready:
            # Try anyway - server might be ready
            server_ready = True
            print("[WARN] Could not confirm server ready, attempting connection anyway...")
        
        # Give it a moment
        await asyncio.sleep(1)
        
        # Perform MCP initialization handshake
        await self._initialize()
    
    async def _continue_reading_stderr(self):
        """Continue reading stderr in background"""
        while self.process and self.process.stderr:
            try:
                line = await self.process.stderr.readline()
                if line:
                    print(f"[Server]: {line.decode().strip()}")
            except:
                break
    
    async def _initialize(self):
        """Perform MCP initialization handshake."""
        print("Initializing MCP connection...")
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_json = json.dumps(init_request) + "\n"
        self.process.stdin.write(init_json.encode())
        await self.process.stdin.drain()
        
        # Read initialize response
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=10.0
            )
            line_text = response_line.decode().strip()
            
            if not line_text:
                print("[WARN] Empty initialize response, continuing anyway...")
            else:
                try:
                    init_response = json.loads(line_text)
                    print(f"[INFO] MCP Server: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'unknown')}")
                except json.JSONDecodeError as je:
                    print(f"[WARN] Could not parse initialize response: {je}")
        except asyncio.TimeoutError:
            print("[WARN] Timeout waiting for initialize response, continuing anyway...")
        except Exception as e:
            print(f"[WARN] Failed to initialize: {e}, continuing anyway...")
        
        # Send initialized notification
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        notif_json = json.dumps(initialized_notif) + "\n"
        self.process.stdin.write(notif_json.encode())
        await self.process.stdin.drain()
        
        print("MCP initialization complete!")
        await asyncio.sleep(0.5)  # Small delay
        
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a request to the MCP server.
        
        Args:
            method: MCP method name
            params: Request parameters
            
        Returns:
            Response from the server
        """
        if not self.process:
            await self.start()
            
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response from stdout (should be clean JSON now)
        # Increased timeout for LLM operations which can take longer
        timeout = 60.0 if method == "tools/call" else 10.0
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=timeout
            )
            line_text = response_line.decode().strip()
            
            if not line_text:
                raise RuntimeError("Empty response from server")
                
            response = json.loads(line_text)
            return response
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout waiting for response from server")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {line_text[:100]}... Error: {e}")
    
    async def list_tools(self) -> list[Dict[str, Any]]:
        """List available tools from the MCP server."""
        response = await self.send_request("tools/list")
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool result
        """
        response = await self.send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )
        return response.get("result", {}).get("content", [{}])[0].get("text", "")
    
    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()


async def main():
    """Example usage of the MCP client."""
    # Initialize client - connect to Docker container running MCP server
    # The server should be running in Docker: docker run -it mcp-tools-demo
    # For stdio transport, we need to connect to the running container
    # Note: This example assumes the server is running via Docker
    # You may need to adjust the connection method based on your setup
    client = MCPClient(["docker", "run", "-i", "--rm", "mcp-tools-demo"])
    
    try:
        # Start the server
        await client.start()
        
        # List available tools
        print("\n" + "="*50)
        print("Available tools:")
        print("="*50)
        tools = await client.list_tools()
        for tool in tools:
            print(f"  ✓ {tool.get('name')}: {tool.get('description', 'No description')}")
        print()
        
        print("\n" + "="*50 + "\n")
        
        # Example 1: Web search
        print("Example 1: Web Search")
        print("Query: 'What is Python programming?'")
        search_result = await client.call_tool(
            "search_web",
            {"query": "What is Python programming?"}
        )
        print(f"Result: {search_result[:200]}...")  # Print first 200 chars
        
        print("\n" + "="*50 + "\n")
        
        # Example 2: RAG query (requires documents in data/ directory)
        print("Example 2: RAG Query")
        print("Query: 'Tell me about DeepSeek'")
        try:
            rag_result = await client.call_tool(
                "query_documents",
                {"query": "Tell me about DeepSeek"}
            )
            print(f"Result: {rag_result[:200]}...")  # Print first 200 chars
        except Exception as e:
            print(f"Error: {e}")
            print("Note: Make sure you have documents in the 'data' directory")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())

