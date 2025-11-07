import nest_asyncio
import os
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.settings import Settings
from llama_index.core.workflow import Event, Context, Workflow, StartEvent, StopEvent, step
from llama_index.core.schema import NodeWithScore
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.response_synthesizers import CompactAndRefine

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class RetrievalResult(Event):
    """Event containing retrieved document nodes"""
    nodes: list[NodeWithScore]
    query: str

class RAGWorkflow(Workflow):
    def __init__(self, model_name=None, embedding_model=None):
        super().__init__()
        # Get configuration from environment variables with defaults
        # Using gemma:2b as default (smaller, faster model)
        model_name = model_name or os.getenv("OLLAMA_MODEL", "gemma:2b")
        embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Setup language model and embeddings
        self.llm = Ollama(model=model_name, base_url=ollama_host)
        self.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        
        # Apply settings globally
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        
        self.index = None

    @step
    async def process_documents(self, ctx: Context, ev: StartEvent) -> StopEvent | None:
        """Load and index documents from the specified directory."""
        dir_path = ev.get("dirname")
        if not dir_path:
            return None
        # SimpleDirectoryReader automatically detects and handles:
        # - PDF files (.pdf)
        # - Text files (.txt)
        # - Markdown files (.md)
        # - Word documents (.docx)
        # - And other supported formats
        try:
            import sys
            doc_list = SimpleDirectoryReader(dir_path).load_data()
            if not doc_list:
                print(f"Warning: No documents found in {dir_path}", file=sys.stderr)
                return None
            print(f"Loaded {len(doc_list)} document(s) from {dir_path}", file=sys.stderr)
            self.index = VectorStoreIndex.from_documents(documents=doc_list)
            print("Document index created successfully", file=sys.stderr)
            return StopEvent(result=self.index)
        except Exception as e:
            print(f"Error loading documents: {e}", file=sys.stderr)
            raise

    @step
    async def find_context(self, ctx: Context, ev: StartEvent) -> RetrievalResult | None:
        """Find relevant document sections for the query."""
        user_query = ev.get("query")
        doc_index = ev.get("index") or self.index
        if not user_query:
            return None
        if doc_index is None:
            import sys
            print("Document index not available. Please load documents first.", file=sys.stderr)
            return None
        doc_retriever = doc_index.as_retriever(similarity_top_k=2)
        relevant_nodes = await doc_retriever.aretrieve(user_query)
        # Store query for next step - using event to pass data
        return RetrievalResult(nodes=relevant_nodes, query=user_query)

    @step
    async def generate_answer(self, ctx: Context, ev: RetrievalResult) -> StopEvent:
        """Create a response based on retrieved context."""
        response_builder = CompactAndRefine(streaming=True, verbose=True)
        # Get query from the event
        user_query = ev.query
        final_response = await response_builder.asynthesize(user_query, nodes=ev.nodes)
        return StopEvent(result=final_response)

    async def ask(self, question: str):
        """Process a question and return an answer using RAG."""
        if self.index is None:
            raise ValueError("Documents must be loaded first. Call load_documents before querying.")
        
        workflow_output = await self.run(query=question, index=self.index)
        return workflow_output

    async def load_documents(self, directory: str):
        """Initialize the document index from files in the given directory."""
        workflow_output = await self.run(dirname=directory)
        self.index = workflow_output
        return workflow_output

# Demo usage
async def main():
    # Create workflow instance
    doc_workflow = RAGWorkflow()
    
    # Load document collection
    await doc_workflow.load_documents("data")
    
    # Ask a question
    answer = await doc_workflow.ask("How was DeepSeekR1 trained?")
    
    # Display the answer
    async for text_part in answer.async_response_gen():
        print(text_part, end="", flush=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

