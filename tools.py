import os
import json
import traceback
from typing import List, Dict, Any, Optional, Type, Callable
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# LangChain Imports
#
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool as tool_decorator
from langchain_core.utils.function_calling import convert_to_openai_tool

# Search Tools
from duckduckgo_search import DDGS

# --- 1. Tool Definitions ---

class GoogleSearch:
    """
    Google Search tool using DuckDuckGo as a backend.
    """
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Performs a search and returns a list of results.
        """
        print(f"  [Search] Searching for: {query}")
        results = []
        try:
            # ddgs.text returns a generator, so we listify it
            search_results = list(self.ddgs.text(query, max_results=10))
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
        except Exception as e:
            print(f"  [Search Error] {e}")
        return results

google_search_instance = GoogleSearch()

# We wrap this as a standalone function for LangChain to bind easily
def google_search(query: str) -> str:
    """
    Performs a web search for the given query and returns the top results as a JSON string.
    """
    results = google_search_instance.search(query)
    return json.dumps(results)


# Firecrawl Tool
# Re-implementing firecrawl_toolset to use the direct library if available, or mock.
try:
    from firecrawl import FirecrawlApp
    
    class FirecrawlTool:
        def __init__(self):
            self.app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

        def scrape(self, url: str) -> str:
            """
            Scrapes the provided URL to extract markdown content.
            """
            print(f"  [Firecrawl] Scraping {url}...")
            try:
                params = {
                    "formats": ["markdown", "html"],
                    "onlyMainContent": True,
                    "timeout": 90000
                }
                scrape_result = self.app.scrape_url(url, params=params)
                return json.dumps(scrape_result)
            except Exception as e:
                print(f"  [Firecrawl Error] {e}")
                return json.dumps({"error": str(e)})

    firecrawl_instance = None
    
    def firecrawl_scrape(url: str) -> str:
        """
        Scrapes a website URL and returns the content in markdown format.
        """
        global firecrawl_instance
        if firecrawl_instance is None:
             firecrawl_instance = FirecrawlTool()
        return firecrawl_instance.scrape(url)

    firecrawl_toolset = firecrawl_scrape 

except ImportError:
    print("Warning: firecrawl-py not installed or failed to import.")
    def firecrawl_toolset(url: str) -> str:
        return json.dumps({"error": "Firecrawl library not available."})


# --- 2. Unified LLM Agent (LangChain Powered) ---

class LlmAgent:
    def __init__(self, name: str, model: str, description: str, instruction: str, tools: List[Callable] = None, output_schema: Type[BaseModel] = None, output_key: str = None):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.tools = tools or []
        self.output_schema = output_schema
        self.output_key = output_key
        
        # --- Dynamic LLM Selection ---
        self.llm = self._get_llm_client(model)
        
        # Bind tools if supported
        if self.tools:
            # Convert python functions to LangChain tools
            self.lc_tools = [tool_decorator(t) for t in self.tools]
            self.llm_with_tools = self.llm.bind_tools(self.lc_tools)
        else:
            self.llm_with_tools = self.llm

    def _get_llm_client(self, requested_model: str):
        """
        Selects the best available LLM backend based on .env keys.
        Currently only supports Gemini via Google GenAI.
        """
        
        # 2. Gemini (Google)
        if os.getenv("GEMINI_API_KEY"):
            print(f"  [Init] Agent '{self.name}' using Gemini.")
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0
            )
            
        else:
            raise RuntimeError("No valid LLM API key found (GEMINI). Check .env.")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n--- Running Agent: {self.name} ---")
        
        # Construct Prompt
        prompt_text = f"Input Data: {json.dumps(input_data, indent=2)}\n\nPlease process this input according to your instructions."
        messages = [
            SystemMessage(content=self.instruction),
            HumanMessage(content=prompt_text)
        ]
        
        try:
            # Invoke LLM
            response = self.llm_with_tools.invoke(messages)
            
            # Handle Tool Calls (Simple Loop)
            # Note: In a full LangGraph, this would be a node loop. 
            # Here we do a simple local loop for the agent's turn.
            if response.tool_calls:
                print(f"  [Tool Call] {len(response.tool_calls)} tool(s) called.")
                messages.append(response) # Add AI message with tool calls
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Find the matching tool function
                    selected_tool = next((t for t in self.lc_tools if t.name == tool_name), None)
                    
                    if selected_tool:
                        print(f"  [Executing] {tool_name} with {tool_args}")
                        tool_output = selected_tool.invoke(tool_args)
                        messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                    else:
                        print(f"  [Error] Tool {tool_name} not found.")
                        messages.append(ToolMessage(tool_call_id=tool_call["id"], content="Error: Tool not found"))
                
                # Get final response after tools
                final_response = self.llm_with_tools.invoke(messages)
                output_text = final_response.content
            else:
                output_text = response.content

            # Parse Output
            if self.output_schema:
                try:
                    # Clean markdown code blocks if present
                    cleaned_text = str(output_text).replace("```json", "").replace("```", "").strip()
                    json_data = json.loads(cleaned_text)
                    validated_data = self.output_schema(**json_data)
                    if self.output_key:
                        return {self.output_key: validated_data.model_dump()}
                    return validated_data.model_dump()
                except Exception as e:
                    print(f"  [Error] JSON Validation failed: {e}")
                    return {"error": "Failed to parse JSON", "raw_output": output_text}
            else:
                if self.output_key:
                    return {self.output_key: output_text}
                return {"output": output_text}

        except Exception as e:
            print(f"  [Error] Agent execution failed: {e}")
            traceback.print_exc()
            return {"error": str(e)}


# --- 3. Resilience & Memory Helpers ---

def run_with_retries(func, *args, **kwargs):
    """
    Executes a function with exponential backoff retries.
    """
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def wrapper():
        return func(*args, **kwargs)
    
    try:
        return wrapper()
    except Exception as e:
        print(f"  [Retry Failed] Function {func.__name__} failed after retries: {e}")
        raise e

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory", "state.json")

def load_memory() -> Dict[str, Any]:
    """Loads persistent state from JSON file."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"  [Memory] Failed to load memory: {e}")
    return {}

def save_memory(state: Dict[str, Any]):
    """Saves state to JSON file."""
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"  [Memory] Failed to save memory: {e}")

# Export tools for agents.py
# Note: agents.py expects these to be callables or list of callables
# In the new LlmAgent, we pass the raw functions, and it converts them.
google_search_tool = google_search
