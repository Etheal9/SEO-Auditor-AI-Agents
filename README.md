# SEO Auditor AI Agent

This project implements a multi-agent system using LangGraph to perform a comprehensive SEO audit on a given URL. The system is composed of three specialized agents that work in sequence to analyze a webpage, research its competitors, and generate actionable recommendations.

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
