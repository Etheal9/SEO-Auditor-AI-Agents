import streamlit as st
import os
from dotenv import load_dotenv
import time
from agents import seo_audit_graph

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="SEO Auditor AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for "Beautiful" UI ---
st.markdown("""
    <style>
        /* Main Background and Text */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #38bdf8;
            font-weight: 700;
        }
        
        h1 {
            font-size: 3rem;
            text-align: center;
            margin-bottom: 1rem;
            background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Input Field Styling */
        .stTextInput > div > div > input {
            background-color: #334155;
            color: #ffffff;
            border: 1px solid #475569;
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 1.1rem;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }
        
        /* Button Styling */
        .stButton > button {
            background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            font-size: 1.1rem;
            font-weight: 600;
            width: 100%;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
        }
        
        /* Card/Container Styling */
        .css-1r6slb0, .stMarkdown {
            background-color: transparent;
        }
        
        .result-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 24px;
            margin-top: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #334155;
            border-radius: 8px;
            color: #e2e8f0;
        }
        
        /* Status Container */
        .stStatusWidget {
            background-color: #1e293b;
            border: 1px solid #334155;
        }
    </style>
""", unsafe_allow_html=True)

# --- Header Section ---
st.markdown("<h1>SEO Auditor AI Agent</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #94a3b8; font-size: 1.2rem; margin-bottom: 40px;'>Enter a URL below to generate a comprehensive SEO audit report powered by AI.</p>", 
    unsafe_allow_html=True
)

# --- Input Section ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    url_input = st.text_input("Website URL", placeholder="https://example.com", label_visibility="collapsed")
    analyze_btn = st.button("🚀 Run SEO Audit")

# --- Logic & Display ---
if analyze_btn and url_input:
    if not url_input.startswith("http"):
        st.error("Please enter a valid URL starting with http:// or https://")
    else:
        # Container for results
        result_container = st.container()
        
        with result_container:
            try:
                # Status Indicator
                with st.status("🤖 Agents are working...", expanded=True) as status:
                    st.write("🔍 Page Auditor: Scanning website content...")
                    
                    # Initial State
                    initial_state = {
                        "url": url_input, 
                        "page_audit": {}, 
                        "serp_analysis": {}, 
                        "report": "", 
                        "errors": []
                    }
                    
                    # Run the Graph
                    # We can't easily stream updates from the graph unless we use a callback or stream() 
                    # but for now we'll just run it and simulate progress or just wait.
                    # Ideally, we'd use .stream() to get updates, but let's stick to .invoke() for stability as per main.py
                    
                    final_state = seo_audit_graph.invoke(initial_state)
                    
                    # Check progress based on state (simulated since invoke is blocking)
                    if final_state.get("page_audit"):
                        st.write("✅ Page Auditor: Complete")
                        st.write("📊 SERP Analyst: Analyzing competitors...")
                    
                    if final_state.get("serp_analysis"):
                        st.write("✅ SERP Analyst: Complete")
                        st.write("💡 Optimization Advisor: Generating report...")
                        
                    status.update(label="Audit Completed!", state="complete", expanded=False)

                # --- Display Results ---
                
                # 1. Main Report
                if final_state.get("report"):
                    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                    st.markdown("## 📋 Comprehensive SEO Report")
                    st.markdown(final_state["report"])
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Download Button
                    st.download_button(
                        label="📥 Download Report",
                        data=final_state["report"],
                        file_name="seo_audit_report.md",
                        mime="text/markdown"
                    )
                else:
                    st.warning("No report was generated. Please check the errors below.")

                # 2. Errors (if any)
                if final_state.get("errors"):
                    st.error("Errors encountered during audit:")
                    for err in final_state["errors"]:
                        st.write(f"- {err}")

                # 3. Detailed Data (Expanders)
                st.markdown("### 🔍 Detailed Analysis Data")
                
                with st.expander("📄 Raw Page Audit Data"):
                    st.json(final_state.get("page_audit", {}))
                    
                with st.expander("🏆 SERP Competitor Analysis"):
                    st.json(final_state.get("serp_analysis", {}))

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                # Optional: Print traceback to console for debugging
                import traceback
                traceback.print_exc()

# --- Footer ---
st.markdown(
    """
    <div style='text-align: center; margin-top: 50px; padding: 20px; color: #64748b; font-size: 0.9rem;'>
        Powered by LangGraph, Firecrawl, and Google Gemini
    </div>
    """, 
    unsafe_allow_html=True
)
