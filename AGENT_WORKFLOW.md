# NyayamGPT - Pure Agent Workflow (Logic Flow)

This diagram represents **only the decision-making logic** inside the AI Agent (LangGraph). It excludes databases, APIs, and frontend code to focus strictly on how the AI "thinks."

---

## The AI Reasoning Graph

```mermaid
flowchart TD
    %% Define Styles
    classDef decision fill:#ffecb3,stroke:#ff6f00,stroke-width:2px,rx:10,ry:10;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,rx:5,ry:5;
    classDef terminal fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,rx:5,ry:5,color:#000;
    classDef action fill:#fff9c4,stroke:#fbc02d,stroke-dasharray: 5 5;

    %% Entry Point
    Start([User Input]) --> Classify[Intent Classification]:::process

    %% Step 1: Intent Routing
    Classify --> CheckIntent{What is the<br/>User Intent?}:::decision
    
    CheckIntent --"Ambiguous Info"--> Clarify[Collect Missing Details]:::process
    CheckIntent --"Draft Legal Doc"--> DraftDoc[Draft Document]:::process
    CheckIntent --"Legal Question"--> Rewrite[Query Rewriter]:::process

    %% Clarification / Drafting Endpoints
    Clarify --> Finalize
    DraftDoc --> Finalize

    %% Step 2: Information Gathering (The RAG Pipeline)
    Rewrite --> ClassifyRAG[Classify RAG Type]:::process
    ClassifyRAG --"General/Specific"--> Expand[Query Expansion]:::process
    Expand --"Generate 3 Variations"--> Retrieve[Retrieve Docs]:::process
    
    %% Step 3: Knowledge Check
    Retrieve --> CheckKnowledge{Context<br/>Sufficient?}:::decision
    
    CheckKnowledge --"No (Recent Case)"--> WebSearch[Search Case Law<br/>(DuckDuckGo)]:::process
    CheckKnowledge --"Yes (In Vector DB)"--> DraftAns
    
    WebSearch --> DraftAns[Draft Initial Answer]:::process

    %% Step 4: Safety & Validation Loop
    DraftAns --> CheckSafety{High Risk<br/>Topic?}:::decision
    
    CheckSafety --"Yes (e.g. Crime)"--> Validate[Validation Agent]:::process
    CheckSafety --"No"--> Simplify
    
    Validate --> Severity[Severity Check]:::process
    Severity --"Corrected Logic"--> Simplify[Simplify Output]:::process

    %% Step 5: Final Polish
    Simplify --> Extract[Extract Citations]:::process
    Extract --> Resolve[Resolve URLs]:::process
    Resolve --"Add Web Links"--> Finalize[Finalize Response]:::terminal

    %% End
    Finalize --> End([End])
```

---

## Step-by-Step Walkthrough

### 1. The Gatekeeper (Intent)
Every request starts at **`Intent Classification`**. The agent analyses if the user is:
*   Asking a legal question (*go to reasoning*).
*   Asking to write a document like a generic rental agreement (*go to drafter*).
*   Just saying "Hello" or giving vague info (*go to clarification*).

### 2. The Researcher (RAG)
If it's a question, we don't just search for the user's words.
*   **`Query Rewriter`**: Converts "police hit me" to "relevant BNS sections for police brutality".
*   **`Query Expansion`**: Generates 3-5 variations of that query to catch different legal terms.
*   **`Retrieve Docs`**: Fetches the most similar legal texts from our database.

### 3. The Fallback (Web Search)
The **`CheckKnowledge`** decision node is critical.
*   If the database has the answer (e.g., standard penal code), we proceed.
*   If the retrieval score is low (data missing) or the query requires *recent* case law (post-2024), the agent triggers **`Search Case Law`** to go online.

### 4. The Supervisor (Validation)
This is a unique safety feature.
*   **`CheckSafety`**: If the draft answer mentions "arrest," "bail," or "imprisonment," we flag it as high-risk.
*   **`Validation Agent`**: A separate prompt reads the draft to ensure we haven't swapped the Victim and the Accused (a common AI error).
*   **`Severity Check`**: Ensures we aren't recommending a "Death Penalty" for a minor traffic offense.

### 5. The Librarian (Citations)
Before sending the answer:
*   **`Extract Citations`**: Scans the text for "Section 302".
*   **`Resolve URLs`**: Adds clickable links (e.g., to IndianKanoon.org) so the user can verify the law themselves.

---

## 3. Conceptual Code Snippets

This section shows the *code patterns* used to implement the graph above.

### A. The State (Memory)
This dictionary is passed between every node. It holds the "Memory" of the current conversation turn.

```python
# app/agents/types.py
class GraphState(TypedDict, total=False):
    query: str                   # User's input
    intent: str                  # "LEGAL_QUERY", "DRAFTING", etc.
    retrieved_docs: list         # Docs found in vector DB
    local_docs_sufficient: bool  # Decision flag for Web Search
    draft_answer: str            # The LLM's rough draft
    final_answer: str            # The polished response
    is_valid: bool               # Did it pass safety checks?
```

### B. Defining the Graph (Architecture)
This is where we wire up the "brain" using `LangGraph`.

```python
# app/agents/graph.py
def create_legal_assistant_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    
    # 1. Add "Worker" Nodes
    workflow.add_node("classify_intent", node_classify_intent)
    workflow.add_node("retrieve_docs", node_retrieve_docs)
    workflow.add_node("search_case_law", node_search_case_law) # Web Search
    workflow.add_node("draft_answer", node_draft_answer)
    
    # 2. Add "Router" Edges (Conditional Logic)
    # If docs are good -> Draft. If docs are bad -> Search Web.
    workflow.add_conditional_edges(
        "retrieve_docs",
        should_search_web,  # The decision function
        {
            "draft": "draft_answer",
            "search": "search_case_law"
        }
    )
    
    return workflow.compile()
```

### C. The Decision Function (Router Logic)
This simple function decides which path to take based on the state.

```python
# app/agents/nodes.py
def should_search_web(state: GraphState) -> str:
    """Decides if we need to use DuckDuckGo."""
    if state.get("local_docs_sufficient", False):
        return "draft"   # Go to drafting
    return "search"      # Go to web search
```

### D. A Worker Node (The Logic)
Each node is just a Python function that takes `state` and returns `updates`.

```python
# app/agents/nodes.py
async def node_classify_intent(state: GraphState) -> GraphState:
    query = state["query"]
    
    # Call LLM to classify
    result = await llm_classify(query)
    
    return {
        **state,
        "intent": result["intent"], # e.g., "LEGAL_QUERY"
        "needs_clarification": result["needs_clarification"]
    }
```
