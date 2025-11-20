from dotenv import load_dotenv
import os
import json

# Load environment variables before importing agents
load_dotenv()

from agents import seo_audit_graph
from tools import load_memory, save_memory

def main(url: str):
    """
    Runs the SEO audit using the LangGraph workflow.
    """
    print(f"Starting SEO audit for: {url}")

    # Load persistent memory (optional usage for now, but good practice)
    # In a more advanced agent, we would inject this into the state.
    memory = load_memory()
    
    # Initial State
    initial_state = {
        "url": url, 
        "page_audit": {}, 
        "serp_analysis": {}, 
        "report": "", 
        "errors": []
    }

    try:
        print("🚀 Initializing LangGraph Workflow...")
        
        # Run the graph
        # .invoke() runs the graph to completion
        final_state = seo_audit_graph.invoke(initial_state)
        
        print("\n✅ Workflow Completed.")
        
        # Display Report
        print("\n" + "="*30)
        print("   SEO AUDIT REPORT")
        print("="*30 + "\n")
        
        if final_state.get("report"):
            print(final_state["report"])
        else:
            print("⚠️ No report was generated.")
            if final_state.get("errors"):
                print("\nErrors encountered:")
                for err in final_state["errors"]:
                    print(f"- {err}")

        # Save Memory (Persistence)
        # We save the final state so we can inspect it later or resume
        save_memory(final_state)
        print(f"\n💾 State saved to memory/state.json")
            
    except Exception as e:
        print(f"❌ An error occurred during the audit: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check API Key
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("⚠️  Warning: FIRECRAWL_API_KEY not found in .env")
    if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: No LLM API Key (GROQ or GEMINI) found in .env")

    # Default URL or User Input
    target_url = "https://www.example.com"
    
    # Simple CLI argument parsing could go here
    import sys
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        
    main(target_url)
