# LangGraph: Deep Dive & Concepts

## 1. Why LangGraph? (vs LangChain)

**LangChain** uses "Chains" (DAGs - Directed Acyclic Graphs).
*   Step A -> Step B -> Step C.
*   Good for simple chatbots.
*   **Problem:** What if Step C fails and we need to go back to Step B? Chains can't do loops easily.

**LangGraph** adds **Cycles (Loops)**.
*   Step A -> Step B -> Is result Good?
    *   Yes -> Step C.
    *   No -> Go back to Step A (Retry).
*   This enables "Agentic" behavior: Self-correction, planning, and dynamic routing.

---

## 2. Core Concepts

### A. The State (`TypedDict`)
The "State" is a shared memory dictionary that allows nodes to pass data to each other. Unlike LangChain where data flows pipe-to-pipe, here everyone reads/writes to a central state.

```python
class GraphState(TypedDict):
    question: str
    documents: List[str]
    answer: str
    attempts: int
```

### B. Nodes
A "Node" is just a Python function. It takes the current **State**, does some work (calls LLM, searches DB), and returns an **update** to the State.

```python
def retrieve_node(state: GraphState):
    question = state["question"]
    docs = vector_store.search(question)
    # detailed update:
    return {"documents": docs} 
```

### C. Edges
Edges define the flow.
*   **Normal Edge:** hardcoded path. `workflow.add_edge("node_a", "node_b")` (After A, always go to B).
*   **Conditional Edge:** dynamic path. Used for "Routing".

```python
def check_relevance(state):
    if state["score"] > 0.8:
        return "generate"
    else:
        return "rewrite_query" # Loop back!

workflow.add_conditional_edges(
    "check_docs",   # From this node
    check_relevance, # Run this logic
    {               # Map result to next node
        "generate": "generate_answer",
        "rewrite_query": "rewrite_node"
    }
)
```

---

## 3. Your Project's Graph (NyayamGPT)

Start at **`classify_intent`**.

1.  **Intent Check:** Does user want to chat or search legals?
    *   *Route:* `should_clarify` edge.
2.  **Clarification:** If vague ("I have an issue"), go to `collect_missing_details`.
3.  **Retrieval Leg:** `rewrite_query` -> `expand_query` -> `retrieve_docs`.
4.  **Generation:** `draft_answer`.
5.  **The Loop (Smart Part):** `validate_answer`.
    *   The LLM checks: "Does the draft answer the question using the retrieval?"
    *   *If Bad:* It goes BACK to `rewrite_query` to try searching for different terms.
    *   *If Good:* It proceeds to `simplify_output`.

---

## 4. Compilation

After defining nodes and edges, you must "compile" the graph.

```python
app = workflow.compile()
```

This creates a `Runnable` that you can invoke. LangGraph checks if the graph is valid (no dead ends, etc.).

---

## 5. Checkpointing (Memory)

LangGraph has built-in persistence. If you provide a `checkpointer`, it saves the state **after every step**.

**Why?**
1.  **Human-in-the-loop:** The AI can pause, wait for user approval, and resume.
2.  **Time Travel:** You can debug by looking at the state at step 3 of 10.
3.  **Chat History:** It remembers previous turns in the conversation automatically if configured.

In NyayamGPT, we likely manage history via our SQL `ChatSession` for simplicity, but LangGraph's native memory is powerful for complex multi-turn reasoning.
