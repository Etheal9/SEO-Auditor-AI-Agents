# SEO Auditor AI Agent

This project implements a multi-agent system using LangGraph to perform a comprehensive SEO audit on a given URL. The system is composed of three specialized agents that work in sequence to analyze a webpage, research its competitors, and generate actionable recommendations.

## Target Audience

This project is designed for:
- **SEO Professionals** looking to automate comprehensive website audits
- **Digital Marketers** who need competitive SERP analysis and optimization insights
- **AI/ML Engineers** interested in learning multi-agent system architecture with LangGraph
- **Python Developers** exploring practical applications of LLM-powered agents and tool integration

## System Design Architecture

The system is designed using a layered architecture that separates concerns, making it modular and easier to maintain.

- **Presentation Layer (UI):** The user interface is a web application built with **Streamlit** (`app.py`). Its role is to accept the target URL from the user, trigger the agent workflow, and display the final report and any intermediate data or errors in a user-friendly format.

- **Orchestration Layer:** This layer is managed by **LangGraph** (`agents.py`). It defines the workflow as a state graph where each node represents a step in the audit process. It is responsible for:
    - Managing the overall `AgentState`.
    - Calling the correct agent for each step.
    - Routing the flow of data from one agent to the next.
    - Aggregating results and errors.

- **Agent Layer:** This layer consists of specialized **LLM-powered agents** (`agents.py`), each with a distinct role:
    - `PageAuditorAgent`: Audits the on-page SEO of the given URL.
    - `SerpAnalystAgent`: Researches competitors on the search engine results page.
    - `OptimizationAdvisorAgent`: Synthesizes data from the other agents to create the final report.
    
    Each agent is an instance of the `LlmAgent` class (`tools.py`), which encapsulates the logic for interacting with the LLM, calling tools, and validating output.

- **Tool Layer:** This layer provides the agents with the capabilities to interact with the outside world (`tools.py`). The tools are:
    - `firecrawl_toolset`: Scrapes web content.
    - `google_search_tool`: Performs Google searches to gather SERP data.
    
    These tools are designed to be simple functions that agents can invoke as needed.

- **Data/State Layer:** This layer defines the structure of the data that flows through the system. It consists of:
    - **Pydantic Schemas** (`schemas.py`): These define the expected data structures for agent inputs and outputs, ensuring data integrity.
    - **AgentState** (`agents.py`): A TypedDict that represents the in-memory state of the workflow at any given time.
    - **Persistent Storage** (`tools.py`): A simple JSON file (`memory/state.json`) for saving the final state of a workflow run, which is useful for debugging.

This layered approach ensures that each part of the system has a clear responsibility, which simplifies development, testing, and future modifications.

## System Design Diagram

```
+--------------------------------------------------------------------------+
|                                  User                                    |
+----------------------------------+---------------------------------------+
                                   |
                                   v
+----------------------------------+---------------------------------------+
|                      Presentation Layer (Streamlit UI)                     |
|                              (app.py)                                    |
|            - Receives URL                                                |
|            - Displays final report                                       |
+----------------------------------+---------------------------------------+
                                   |
                                   v
+----------------------------------+---------------------------------------+
|                    Orchestration Layer (LangGraph)                       |
|                             (agents.py)                                  |
|            - Manages AgentState                                          |
|            - Executes workflow graph                                     |
+----------------------------------+---------------------------------------+
                                   |
                                   |
+----------------------------------v---------------------------------------+
|                            Agent Layer                                   |
|                                                                          |
|  +-----------------+      +-----------------+      +-------------------+ |
|  | PageAuditorAgent|----->| SerpAnalystAgent|----->|OptimizationAdvisor| |
|  +-----------------+      +-----------------+      +-------------------+ |
|          |                      |                          |             |
+----------+----------------------|--------------------------+-------------+
           |                      |                          |
           v                      v                          v
+----------+----------------------|--------------------------+-------------+
|       Tool Layer                |                          |             |
|    (tools.py)                   |                          |             |
|                                 |                          |             |
|  +-----------------+ <----------+                          |             |
|  | google_search   |                                        |             |
|  +-----------------+                                        |             |
|                                                             |             |
|  +-----------------+ <--------------------------------------+             |
|  | firecrawl_tool  |                                        |             |
|  +-----------------+ <--------------------------------------+             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## Repository Structure

```
SEO Aduit WEEK 2/
├── agents.py              # LangGraph workflow definition and agent orchestration
├── tools.py               # LLM agent class, tool implementations (Firecrawl, Google Search)
├── schemas.py             # Pydantic data models for validation
├── app.py                 # Streamlit web UI for interactive SEO audits
├── main.py                # CLI entry point for running audits from command line
├── prompts/               # Agent instruction prompts (page_auditor.txt, serp_analyst.txt, etc.)
├── memory/                # Persistent state storage (state.json)
├── requirements.txt       # Python dependencies
├── .env                   # API keys and environment variables (not tracked in git)
└── README.md              # This file
```

## Project Architecture and Design

This section details the core architectural and design decisions of the agent system.

### 1. Scoping and Objective

*   **Single Primary Goal:** The agent's primary goal is to perform a comprehensive SEO audit of a given URL.
*   **Specific Measurable Task:** The agent must take a URL as input and produce a detailed SEO report in Markdown format. This report should include an on-page audit, SERP analysis, and actionable optimization recommendations.

### 2. Workflow

*   **Workflow:** The workflow is a sequence of three main steps, executed in a specific order:
    1.  `page_auditor`: Scrapes the URL and performs an on-page audit.
    2.  `serp_analyst`: Takes the primary keyword from the page audit and analyzes the Search Engine Results Page (SERP).
    3.  `optimization_advisor`: Synthesizes the information from the previous two steps to generate a final report.
*   **Dynamic Reasoning:** While the high-level workflow is fixed, the agent's "reasoning" is dynamic within each step. Each agent (e.g., `PageAuditorAgent`) is an LLM that uses tools (`firecrawl_toolset`, `google_search_tool`) to gather information and then uses its own reasoning to fulfill its specific instructions (defined in the `prompts` files). The output of one agent dynamically influences the input and actions of the next. For example, if no primary keyword is found, the SERP analysis is skipped.

### 3. Output

*   **User's Desired Answer:** The user wants to see a comprehensive, well-structured SEO report that is easy to read and provides actionable advice. The final output is a single Markdown string.
*   **Definition of Done:** The task is "done" when the `optimization_advisor` agent successfully generates the final report string and the workflow finishes.
*   **Success/Failure Criteria:**
    *   **Success:** The workflow completes, and the `report` key in the final state contains a non-empty Markdown string.
    *   **Failure:** The workflow ends with an empty `report` and/or the `errors` list in the state contains one or more error messages. This can happen if an agent fails, a tool call fails, or data validation (using Pydantic schemas) fails.

### 4. API Keys

*   **Management:** API keys (for Firecrawl, Gemini, etc.) are managed using a `.env` file in the project's root directory. The `python-dotenv` library is used to load these keys into the environment variables.
*   **Permissions & Rate Limits:** The code itself does not define or manage permissions or rate limits. These are determined by the external services being used (e.g., Firecrawl, Google AI). The `run_with_retries` function in `tools.py` provides some resilience against transient network errors or rate-limiting issues by retrying failed operations with exponential backoff.

### 5. State/Memory

*   **State Memory:** The application uses two forms of memory:
    1.  **In-Memory State (LangGraph):** During a single run, the state is managed in memory by the `AgentState` object. This object accumulates data (`page_audit`, `serp_analysis`, `report`) and errors as the graph executes.
    2.  **Persistent Memory:** After a run, the final state object is saved to `memory/state.json`. This is a simple form of persistence that saves the entire final state, not just the message history. It can be used for debugging or potentially for resuming a workflow in a more advanced implementation.

### 6. Agent Architecture (Brain)

*   **Topology:** The agent's "brain" is a directed acyclic graph (DAG) built with LangGraph. It's a structured workflow, not a simple "think-act" loop. The topology is `page_auditor -> serp_analyst -> optimization_advisor -> END`.
*   **Complexity:** It's more complex than a simple loop. It has a clear, linear path, but it includes conditional logic (e.g., skipping SERP analysis). It does not currently have the ability to backtrack, but LangGraph's architecture would allow for cycles and more complex branching if needed. There is no built-in mechanism for asking for human help.

### 7. Error Handling

*   **Tool Failure:** Tool failures are handled in a few ways:
    1.  **Retries:** The `run_with_retries` function automatically retries a function call (like an agent's `run` method) up to 3 times if it fails.
    2.  **Error Propagation:** If a node (e.g., `page_auditor_node`) or an agent's internal logic fails, it catches the exception and adds an error message to the `errors` list in the `AgentState`. The workflow continues to the next step, but the subsequent nodes will likely have incomplete data.
    3.  **Graceful Degradation:** The agents are designed to be robust. For example, the `optimization_advisor` will still run even if it doesn't receive `serp_analysis` data; its report will just be less comprehensive. It does not give up, but rather informs the user of the failure in the final output.

### 8. Validation

*   **Correctness:** You can know if the agent is working correctly by:
    1.  **Checking the Final Output:** The primary indicator is the presence of a high-quality report in the final output and an empty `errors` list.
    2.  **Pydantic Schemas:** The `schemas.py` file defines strict data structures (e.g., `PageAuditOutput`, `SerpAnalysis`). The `LlmAgent` class validates the LLM's JSON output against these schemas. If the output doesn't conform, it's flagged as an error. This ensures the data passed between agents is structured and correct.
    3.  **Logs:** The application prints status updates to the console for each node that runs, which helps in tracking the agent's progress and identifying where a failure might have occurred.

---

## Prerequisites

Before installing and running this project, ensure you have:

### Required Knowledge
- Basic understanding of Python programming
- Familiarity with command-line interfaces
- Basic knowledge of SEO concepts (keywords, SERP, on-page optimization)

### System Requirements
- **Operating System:** Windows, macOS, or Linux
- **Python Version:** Python 3.9 or higher
- **Memory:** Minimum 4GB RAM recommended
- **Internet Connection:** Required for API calls to Firecrawl and LLM services

### API Keys Required
- **Firecrawl API Key:** For web scraping functionality ([Get it here](https://firecrawl.dev))
- **LLM API Key:** Either:
  - **Google Gemini API Key** ([Get it here](https://ai.google.dev))
  - **Groq API Key** ([Get it here](https://groq.com))

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Etheal9/SEO-Auditor-AI-Agents.git
cd "SEO Aduit WEEK 2"
```

### Step 2: Create a Virtual Environment

We recommend using a virtual environment for dependency isolation:

**Using venv (built-in):**
```bash
python -m venv .venv

# Activate on Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate on macOS/Linux
source .venv/bin/activate
```

**Using Conda:**
```bash
conda create -n seo-auditor python=3.10
conda activate seo-auditor
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example (if provided) or create manually
touch .env
```

Add your API keys to the `.env` file:

```env
# Required: Firecrawl API Key
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# Required: At least one LLM API key
GEMINI_API_KEY=your_gemini_api_key_here
# OR
GROQ_API_KEY=your_groq_api_key_here

# Optional: LangSmith tracing (for debugging)
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_TRACING=true
```

**Important:** Never commit your `.env` file to version control. It's already included in `.gitignore`.

---

## Usage

### Option 1: Streamlit Web UI (Recommended)

Launch the interactive web interface:

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

**Using the UI:**
1. Enter the target website URL in the input field
2. Click **"🚀 Run SEO Audit"**
3. Wait for the agents to complete their analysis
4. Review the comprehensive SEO report
5. Download the report as a Markdown file using the download button

### Option 2: Command-Line Interface

Run an audit directly from the terminal:

```bash
# Using the default URL
python main.py

# Specify a custom URL
python main.py https://example.com
```

**Output:**
- The final SEO report will be printed to the console
- The complete state (including all intermediate data) will be saved to `memory/state.json`

### Example Output

The system generates a comprehensive Markdown report containing:

- **On-Page SEO Audit:** Title tags, meta descriptions, heading structure, keyword usage, content quality
- **SERP Competitor Analysis:** Top-ranking competitors, their optimization strategies, content gaps
- **Actionable Recommendations:** Prioritized list of improvements with specific implementation guidance

---

## Code Examples

### Running a Programmatic Audit

```python
from agents import seo_audit_graph

# Define initial state
initial_state = {
    "url": "https://example.com",
    "page_audit": {},
    "serp_analysis": {},
    "report": "",
    "errors": []
}

# Execute the workflow
final_state = seo_audit_graph.invoke(initial_state)

# Access the results
print(final_state["report"])
print(f"Errors: {final_state['errors']}")
```

### Customizing Agent Prompts

Agent instructions are stored in the `prompts/` directory. To customize agent behavior:

1. Edit the relevant prompt file (e.g., `prompts/page_auditor.txt`)
2. Restart the application
3. The agents will use your updated instructions

---

## Testing

Currently, this project does not include automated tests. To verify functionality:

### Manual Testing Checklist

1. **Test the Streamlit UI:**
   ```bash
   streamlit run app.py
   ```
   - Enter a valid URL and verify the report is generated
   - Check that errors are displayed appropriately for invalid URLs

2. **Test the CLI:**
   ```bash
   python main.py https://example.com
   ```
   - Verify the report is printed to console
   - Check that `memory/state.json` is created/updated

3. **Test with Different URLs:**
   - Try various website types (blogs, e-commerce, corporate sites)
   - Test with URLs that may have SEO issues

### Future Testing Plans

We plan to add:
- Unit tests for individual agent functions
- Integration tests for the full workflow
- Mock API responses for offline testing

---

## License

This project is licensed under the **MIT License**.

You are free to use, modify, and distribute this software for personal or commercial purposes. See the [LICENSE](LICENSE) file for full details.

---

## Contributing

We welcome contributions from the community! Here's how you can help:

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and commit them:
   ```bash
   git commit -m "Add: description of your changes"
   ```
4. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request** with a clear description of your changes

### Contribution Guidelines

- Follow existing code style and conventions
- Add comments to complex logic
- Update documentation for any new features
- Test your changes thoroughly before submitting

### Areas for Contribution

- Adding new SEO analysis features
- Improving agent prompts for better results
- Adding support for additional LLM providers
- Writing unit and integration tests
- Improving error handling and logging
- Enhancing the UI/UX

---

## Changelog

### Version 1.0.0 (Current)
- Initial release with multi-agent SEO audit system
- Three specialized agents: PageAuditor, SerpAnalyst, OptimizationAdvisor
- Streamlit web UI and CLI interface
- Support for Gemini and Groq LLM backends
- Firecrawl integration for web scraping
- DuckDuckGo search for SERP analysis
- Persistent state storage
- Retry logic with exponential backoff

---

## Maintainer Contact

**Project Maintainer:** Etheal9

- **GitHub:** [@Etheal9](https://github.com/Etheal9)
- **Repository:** [SEO-Auditor-AI-Agents](https://github.com/Etheal9/SEO-Auditor-AI-Agents)

For questions, issues, or feature requests:
- Open an issue on GitHub
- Start a discussion in the repository's Discussions tab

---

**Built with ❤️ using LangGraph, Streamlit, and Google Gemini**
