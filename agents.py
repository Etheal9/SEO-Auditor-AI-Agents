import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Union
from langgraph.graph import StateGraph, END
from tools import firecrawl_toolset, google_search_tool, LlmAgent, run_with_retries
from schemas import PageAuditOutput, SerpAnalysis

# --- 1. State Definition ---
class AgentState(TypedDict):
    url: str
    page_audit: Annotated[Dict[str, Any], "Merge page audit data"]
    serp_analysis: Annotated[Dict[str, Any], "Merge serp analysis data"]
    report: Annotated[str, "Final report"]
    errors: Annotated[List[str], "Accumulate errors"]

# --- 2. Helper: Load Prompts ---
def load_prompt(name: str) -> str:
    try:
        path = os.path.join(os.path.dirname(__file__), "prompts", f"{name}.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt {name}: {e}")
        return ""

# --- 3. Agent Instantiation ---
# We initialize agents with prompts loaded from files.
# Note: LlmAgent handles the LLM backend (Gemini/Groq) internally.

page_auditor_agent = LlmAgent(
    name="PageAuditorAgent",
    model="gemini-1.5-flash",
    description="Scrapes and audits the page.",
    instruction=load_prompt("page_auditor"),
    tools=[firecrawl_toolset],
    output_schema=PageAuditOutput,
    output_key="page_audit"
)

serp_analyst_agent = LlmAgent(
    name="SerpAnalystAgent",
    model="gemini-1.5-flash",
    description="Analyzes SERP competitors.",
    instruction=load_prompt("serp_analyst"),
    tools=[google_search_tool],
    output_schema=SerpAnalysis,
    output_key="serp_analysis"
)

optimization_advisor_agent = LlmAgent(
    name="OptimizationAdvisorAgent",
    model="gemini-1.5-flash",
    description="Generates the final report.",
    instruction=load_prompt("optimization_advisor"),
    tools=[], # Pure synthesis
    output_key="report" # Returns string
)

# --- 4. Nodes (with Retries & Checkpoints) ---

def page_auditor_node(state: AgentState):
    print("\n--- [Node] Page Auditor ---")
    try:
        # Run with retries
        result = run_with_retries(page_auditor_agent.run, {"url": state["url"]})
        
        # Checkpoint / Validation is handled by LlmAgent's output_schema (Pydantic)
        # If it returns a dict with "error", we handle it.
        if "error" in result:
            return {"errors": [f"PageAuditor Error: {result['error']}"]}
            
        return result # Returns {"page_audit": ...}
    except Exception as e:
        return {"errors": [f"PageAuditor Exception: {str(e)}"]}

def serp_analyst_node(state: AgentState):
    print("\n--- [Node] SERP Analyst ---")
    # Conditional Logic: Check if we have a primary keyword
    audit_data = state.get("page_audit", {})
    primary_keyword = audit_data.get("target_keywords", {}).get("primary_keyword")
    
    if not primary_keyword:
        print("  [Warning] No primary keyword found. Skipping SERP analysis.")
        return {"serp_analysis": {"error": "No primary keyword found"}}

    try:
        # Pass the whole audit state so the agent can see the keyword
        result = run_with_retries(serp_analyst_agent.run, {"page_audit": audit_data})
        
        if "error" in result:
             return {"errors": [f"SerpAnalyst Error: {result['error']}"]}
             
        return result # Returns {"serp_analysis": ...}
    except Exception as e:
        return {"errors": [f"SerpAnalyst Exception: {str(e)}"]}

def optimization_advisor_node(state: AgentState):
    print("\n--- [Node] Optimization Advisor ---")
    try:
        # Pass all accumulated state
        input_data = {
            "page_audit": state.get("page_audit"),
            "serp_analysis": state.get("serp_analysis")
        }
        result = run_with_retries(optimization_advisor_agent.run, input_data)
        
        if "error" in result:
            return {"errors": [f"Advisor Error: {result['error']}"]}
            
        return result # Returns {"report": ...}
    except Exception as e:
        return {"errors": [f"Advisor Exception: {str(e)}"]}

# --- 5. Graph Definition ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("page_auditor", page_auditor_node)
workflow.add_node("serp_analyst", serp_analyst_node)
workflow.add_node("optimization_advisor", optimization_advisor_node)

# Add Edges
workflow.set_entry_point("page_auditor")

# Conditional Routing: If Auditor fails, stop or go to end?
# For now, we linearize but we could add a "router" node.
# Let's keep it simple: Auditor -> Analyst -> Advisor
# But if Auditor errors, maybe skip to Advisor (who will say "I have no data")?
# Let's just flow through. The nodes handle missing data gracefully (Robustness).

workflow.add_edge("page_auditor", "serp_analyst")
workflow.add_edge("serp_analyst", "optimization_advisor")
workflow.add_edge("optimization_advisor", END)

# Compile
app = workflow.compile()

# Expose for main.py
seo_audit_graph = app