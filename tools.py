import os
import json
# Conditional import for Gemini or Groq
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from groq import Groq
except ImportError:
    Groq = None
from duckduckgo_search import DDGS
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import traceback

# Configure Gemini
# Configure the appropriate LLM client based on available keys
if os.getenv("GROQ_API_KEY") and Groq:
    # Groq client will be instantiated per LlmAgent instance
    pass
elif os.getenv("GEMINI_API_KEY") and genai:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
else:
    raise RuntimeError("No valid LLM API key found. Set either GROQ_API_KEY or GEMINI_API_KEY.")

class AgentTool:
    """
    Wrapper for tools to be used by agents.
    """
    def __init__(self, func):
        self.func = func
        self.name = func.__name__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

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
            # max_results=10 to match the requirement
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

google_search = GoogleSearch()

# Mock MCPToolset for now since we don't have a full MCP client implementation in this context
# In a real scenario, this would connect to an MCP server.
# We will wrap the firecrawl tool if possible, or mock it if the user doesn't have the server running.
# Given the environment, we'll assume we can't easily spawn an MCP server subprocess here without more setup.
# However, the original code imported MCPToolset. We will replace it with a placeholder or a direct API call if possible.
# For this fix, we will create a mock class that warns if used, or tries to use the API directly if key is present.
# Actually, let's try to implement a basic wrapper if the user has the library, but since we are fixing the code,
# let's stick to a simple implementation that can be extended.

class MCPToolset:
    def __init__(self, connection_params, tool_filter):
        self.connection_params = connection_params
        self.tool_filter = tool_filter

    def __call__(self, *args, **kwargs):
        # This is a placeholder. In a real app, this would invoke the MCP tool.
        # For the purpose of this "fix", we might need to mock the firecrawl output 
        # OR implement a direct API call if the user has the key.
        # Let's assume for now we just return a mock response if called, 
        # or we can try to use the firecrawl-py library directly if installed.
        pass

class StdioServerParameters:
    def __init__(self, command, args, env):
        self.command = command
        self.args = args
        self.env = env

# Re-implementing firecrawl_toolset to use the direct library if available, or mock.
# The original code used `firecrawl-mcp`. We'll switch to `firecrawl-py` as per requirements.
try:
    from firecrawl import FirecrawlApp
    
    class FirecrawlTool:
        def __init__(self):
            self.app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

        def scrape(self, url: str, formats: List[str] = None, onlyMainContent: bool = True, timeout: int = 90000):
            print(f"  [Firecrawl] Scraping {url}...")
            try:
                # Map parameters to firecrawl-py expected format
                params = {
                    "formats": formats or ["markdown", "html"],
                    "onlyMainContent": onlyMainContent,
                    "timeout": timeout
                }
                scrape_result = self.app.scrape_url(url, params=params)
                return scrape_result
            except Exception as e:
                print(f"  [Firecrawl Error] {e}")
                return {"error": str(e)}

    firecrawl_instance = None
    
    def firecrawl_scrape(url: str, formats: List[str] = None, onlyMainContent: bool = True, timeout: int = 90000):
        global firecrawl_instance
        if firecrawl_instance is None:
             firecrawl_instance = FirecrawlTool()
        return firecrawl_instance.scrape(url, formats, onlyMainContent, timeout)

    firecrawl_toolset = firecrawl_scrape # Expose as a function

except ImportError:
    print("Warning: firecrawl-py not installed or failed to import.")
    def firecrawl_toolset(*args, **kwargs):
        return {"error": "Firecrawl library not available."}


class LlmAgent:
    def __init__(self, name: str, model: str, description: str, instruction: str, tools: List[Any] = None, output_schema: Type[BaseModel] = None, output_key: str = None):
        self.name = name
        self.model_name = model
        self.description = description
        self.instruction = instruction
        self.tools = tools or []
        self.output_schema = output_schema
        self.output_key = output_key
        
        # Initialize Gemini model
        # We map the model name to a valid Gemini model if needed, or use the one provided.
        # "gemini-2.5-flash" might not exist, defaulting to "gemini-1.5-flash" or "gemini-pro" if needed.
        # But let's trust the user's string or fallback.
        valid_model = "gemini-1.5-flash" # Fallback
        if "gemini" in model:
             valid_model = model # Try to use what's given, or let it fail if invalid
        
        # Prepare tools for Gemini
        self.gemini_tools = []
        for tool in self.tools:
            if isinstance(tool, AgentTool):
                self.gemini_tools.append(tool.func)
            elif callable(tool):
                self.gemini_tools.append(tool)
            elif hasattr(tool, 'search'): # Handle GoogleSearch object
                self.gemini_tools.append(tool.search)

        # Initialize model based on available backend
        # CRITICAL FIX: Groq implementation here does NOT support tool calling.
        # If tools are provided, we MUST use Gemini if available.
        use_groq = False
        if os.getenv("GROQ_API_KEY") and Groq:
            use_groq = True
            # If this agent needs tools, check if we can use Gemini instead
            if self.tools and genai and os.getenv("GEMINI_API_KEY"):
                print(f"  [Info] Agent {self.name} has tools. Preferring Gemini over Groq for tool support.")
                use_groq = False
        
        if use_groq:
            # Groq path (no native tool calling in this simple implementation)
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            self.model_name = "llama3-70b-8192" # Use a better model than the placeholder
        elif genai:
            self.model = genai.GenerativeModel(
                model_name=valid_model,
                tools=self.gemini_tools if self.gemini_tools else None,
                system_instruction=instruction
            )
        else:
            raise RuntimeError("No LLM backend available.")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n--- Running Agent: {self.name} ---")
        
        # Construct prompt from input
        prompt = f"Input Data: {json.dumps(input_data, indent=2)}\n\nPlease process this input according to your instructions."
        
        # Groq path (no tool calling support)
        if hasattr(self, "groq_client"):
            try:
                response = self.groq_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.instruction},
                              {"role": "user", "content": prompt}]
                )
                output_text = response.choices[0].message.content
            except Exception as e:
                print(f"  [Error] Groq request failed: {e}")
                return {"error": str(e)}
        else:
            # Gemini path (original behavior with tool calling)
            try:
                chat = self.model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(prompt)
                output_text = response.text
            except Exception as e:
                print(f"  [Error] Agent execution failed: {e}")
                return {"error": str(e)}
        # Parse output (common for both backends)
        if self.output_schema:
            try:
                cleaned_text = output_text.replace("```json", "").replace("```", "").strip()
                json_data = json.loads(cleaned_text)
                validated_data = self.output_schema(**json_data)
                if self.output_key:
                    return {self.output_key: validated_data.model_dump()}
                return validated_data.model_dump()
            except json.JSONDecodeError:
                print(f"  [Error] Failed to parse JSON output from {self.name}")
                print(f"  [Raw Output] {output_text}")
                return {"error": "Failed to parse JSON", "raw_output": output_text}
            except Exception as e:
                print(f"  [Error] Validation failed: {e}")
                return {"error": str(e), "raw_output": output_text}
        else:
            if self.output_key:
                return {self.output_key: output_text}
            return {"output": output_text}

class SequentialAgent:
    def __init__(self, name: str, description: str, sub_agents: List[LlmAgent]):
        self.name = name
        self.description = description
        self.sub_agents = sub_agents

    def run(self, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        print(f"Starting Sequential Workflow: {self.name}")
        state = initial_input.copy()
        
        for agent in self.sub_agents:
            agent_output = agent.run(state)
            
            # Update state with agent output
            if isinstance(agent_output, dict):
                state.update(agent_output)
            else:
                # Should not happen with current LlmAgent implementation
                state[agent.name] = agent_output
                
        return state

# Helper for the search agent in tools.py (original file had this)
search_executor_agent = LlmAgent(
    name="perform_google_search",
    model="gemini-1.5-flash",
    description="Executes Google searches for provided queries and returns structured results.",
    instruction="""The latest user message contains the keyword to search.
     - Call google_search with that exact query and fetch the top organic results (aim for 10).
     - Respond with JSON text containing the query and an array of result objects (title, url, snippet). Use an empty array when nothing is returned.
     - No additional commentary—return JSON only.""",
    tools=[google_search],
)

google_search_tool = AgentTool(search_executor_agent.run) # Wrap the run method? 
# Actually, the original code used `google_search_tool` as a tool passed to `SerpAnalystAgent`.
# But `SerpAnalystAgent` instruction says "Call perform_google_search tool".
# So we should expose the search function directly or the agent.
# Let's expose the `google_search.search` method as the tool for `SerpAnalystAgent`.
# The `search_executor_agent` seems redundant if we just use the tool directly.
# But let's keep `google_search_tool` as a callable that `SerpAnalystAgent` can use.
# Wait, `SerpAnalystAgent` uses `google_search_tool`.
# If `google_search_tool` is an `AgentTool` wrapping `search_executor_agent`, then calling it runs the agent.
# Let's simplify: `SerpAnalystAgent` needs a tool to search. `google_search.search` is that tool.
# So let's redefine `google_search_tool` to be `google_search.search`.

google_search_tool = google_search.search

# --- Resilience & Memory Helpers ---

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
        traceback.print_exc()
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

