# NyayamGPT Backend - Comprehensive Interview Guide

This guide covers the entire backend architecture, workflow, and technologies used in the **NyayamGPT** project. Use this to prepare for your TCS interview.

---

## 1. High-Level Architecture

The backend is built using **FastAPI**, a high-performance Python web framework, and uses **LangGraph** to orchestrate the AI logic.

### Architecture Diagram (Mermaid)

```mermaid
graph TD
    Client[Frontend / User] -->|HTTP Request| API[FastAPI Server]
    
    subgraph "Backend Infrastructure"
        API -->|Auth Check| Auth[Authentication (JWT)]
        API -->|Rate Limit| Limiter[Rate Limiter]
        
        API -->|Route Request| Agent[LangGraph Agent Controller]
        
        subgraph "AI Processing (LangGraph)"
            Agent --> Classify[Intent Classification]
            Classify -->|Legal Query| RAG_Flow
            Classify -->|General/Clarify| Direct_Resp
            
            subgraph "RAG Pipeline"
                RAG_Flow --> Rewrite[Query Rewrite & Expansion]
                Rewrite --> Retrieve[Vector Store Retrieval]
                Rewrite --> WebSearch[Web Search (DuckDuckGo)]
                Retrieve & WebSearch --> Augment[Context Augmentation]
                Augment --> Generate[LLM Generation (Gemini)]
                Generate --> Validate[Validation & Simplification]
            end
        end
        
        Retrieve <--> VectorDB[(ChromaDB / FAISS)]
        VectorDB <--> Embeddings[Embedding Model]
        
        Agent -->|Save History| DB[(PostgreSQL / SQL DB)]
    end
    
    Agent -->|JSON Response| Client
```

---

## 2. Tech Stack & Justifications (Why did you use...?)

| Technology | Usage | Why this choice? |
| :--- | :--- | :--- |
| **FastAPI** | Web Framework | Async support (high concurrency for AI calls), automatic docs (Swagger UI), Pydantic validation. |
| **LangGraph** | AI Orchestration | Unlike linear chains, it allows **loops** (retry if validation fails) and **conditional branching** (ask for clarification vs. answer directly). |
| **Google Gemini** | LLM Model | Cost-effective, large context window (handling long legal docs), good reasoning capabilities. |
| **ChromaDB / FAISS** | Vector Database | Efficient semantic search to find relevant legal sections (IPC, CrPC) from thousands of documents. |
| **PostgreSQL** | Primary Database | Relational integrity for Users, Chat Sessions, and structured data. |

---

## 3. Code Structure & Organization

**Question:** "How did you structure your backend code?"

**Answer:**
"I followed a **Modular Architecture** separating concerns into distinct directories. This makes the codebase maintainable and testable."

*   `app/api/`: **Controllers** - Handles HTTP requests and Validations.
*   `app/core/`: **Configuration** - Settings, Logging, Security (things used everywhere).
*   `app/services/`: **External Services** - Wrappers for Gemini API, Web Search, etc.
*   `app/agents/`: **Business Logic** - The complex AI workflows (LangGraph).
*   `app/rag/`: **Data Layer** - Vector store operations, embeddings.
*   `app/db/`: **Persistence** - SQL Models and Database Sessions.

This separation ensures that if I change the Database (e.g., SQLite to Postgres), I only touch `app/db`, not the API routes.

---

## 4. The "Life of a Request" (Workflow)

**Question:** "Walk me through what happens when a user asks a legal question."

**Answer:**
1.  **Entry:** The request hits `app/main.py`. Middleware handles CORS, GZip compression, and Request ID generation.
2.  **Protection:** `RateLimiter` ensures the user hasn't exceeded their request limit.
3.  **Authentication:** `app/auth/dependencies.py` verifies the JWT token (if logged in).
4.  **Orchestration (LangGraph):** The request is passed to `app/agents/graph.py`.
5.  **Intent:** The AI first checks: Is this a legal question? Do I need more info?
    *   *If unclear:* It routes to `node_collect_missing_details` and asks the user for clarification.
    *   *If clear:* It proceeds to `node_retrieve_docs`.
6.  **Retrieval (RAG):**
    *   The query is converted to a vector (embedding).
    *   We search the Vector Store for matching laws (e.g., "Section 302 IPC").
    *   *Optional:* We fetch latest case laws via Web Search.
7.  **Generation:** The retrieved context + user query is sent to Gemini (LLM) to draft an answer.
8.  **Validation:** The answer is checked. Is it accurate? Is it safe?
9.  **Formatting:** The answer is simplified (removing complex jargon) and citations are extracted.
10. **Storage:** The Q&A pair is saved to the SQL Database (`ChatSession`).
11. **Response:** Steps are returned to the frontend.

---

## 4. Deep Dive: The AI Agent (LangGraph)

**File:** `backend/app/agents/graph.py`

This is the brain of the application. It's a **State Graph**.

### The Graph State
We maintain a state object (`GraphState`) through the process:
```python
class GraphState(TypedDict):
    question: str           # Original user question
    rewritten_question: str # Optimized for search
    intent: str             # "legal_query", "greeting", etc.
    documents: List[Document] # Retrieved laws
    generation: str         # The draft answer
    ...
```

### Key Nodes (Steps)
1.  **Classify Query:** Decides if RAG (database search) is strictly needed or if it's general knowledge.
2.  **Rewrite Query:** "My husband hit me" -> "Legal remedies for domestic violence under DV Act 2005".
3.  **Retrieve:** Fetches actual legal text.
4.  **Draft:** Generates the answer.
5.  **Validate:** (Self-Correction) The LLM critiques its own answer. If bad, it loops back to re-generate. **This is a key differentiator.**

---

## 5. RAG (Retrieval-Augmented Generation)

**Question:** "How does your RAG implementation work?"

**Answer:**
"We use a standard retrieval pipeline but enriched with metadata."

1.  **Ingestion:** We load JSONs of Indian Laws (BNS, IPC).
2.  **Chunking:** We split text into meaningful chunks (e.g., per Section).
3.  **Embedding:** We use `sentence-transformers` (HuggingFace) to convert text to vectors.
4.  **Storage:** Vectors are stored in **ChromaDB**.
5.  **Retrieval:** We use Cosine Similarity to find the top-k most relevant sections.
6.  **Re-ranking:** (Ideally) We re-rank results to ensure the most relevant law is at the top.

---

## 6. Database Schema (PostgreSQL)

**File:** `backend/app/db/models.py`

*   **Users Table:** (`id`, `email`, `hashed_password`)
*   **ChatSession:** (`id`, `user_id`, `created_at`) - Represents one conversation thread.
*   **ChatMessage:** (`id`, `session_id`, `role` [user/assistant], `content`, `citations`) - The actual history.

**Relationships:**
*   One User -> Many ChatSessions.
*   One ChatSession -> Many ChatMessages.

---

## 7. Authentication & Security

*   **JWT (JSON Web Tokens):** Stateless authentication. The server signs a token; the client sends it in the header (`Authorization: Bearer <token>`).
*   **Password Hashing:** We use `bcrypt` or `argon2`. **Never store plain text passwords.**
*   **Environment Variables:** All secrets (API Keys, DB URL) are stored in `.env`, loaded via `pydantic-settings`.

---

## 8. Common Interview Questions (Q&A)

**Q1: How do you handle slow responses from the LLM?**
*   **Ans:** We use **Async/Await** in Python so the server isn't blocked while waiting for Gemini. We can also stream the response (Server-Sent Events) to the frontend so the user sees text appearing character-by-character (if implemented), or at least we provide a loading state.

**Q2: How do you prevent the AI from hallucinating (making up laws)?**
*   **Ans:** We use **RAG**. The prompt strictly instructs the LLM: *"Answer ONLY based on the provided context. If you don't know, say you don't know."* Plus, we have a **Validation Node** in LangGraph that checks if the generated answer is supported by the retrieved documents.

**Q3: Why did you choose LangGraph over LangChain chains?**
*   **Ans:** LangChain chains are often linear (A -> B -> C). Real-world conversations are messy. LangGraph allows **cycles** (A -> B -> Check -> A) and complex conditional logic, which is essential for a robust agent that can self-correct.

**Q4: How do you scale this?**
*   **Ans:**
    1.  **Stateless API:** We can run multiple instances of the FastAPI server behind a Load Balancer (Nginx) to handle increased traffic.
    2.  **Vector DB:** We can use a cloud vector DB (Pinecone/Milvus) instead of local ChromaDB for massive datasets.
    3.  **Database Optimization:** Using read replicas for PostgreSQL to handle more read queries, and optimizing indexes.

**Q5: Difficult challenge faced?**
*   **Ans:** "Tuning the retrieval was hard. Searching for 'murder' didn't always return 'Section 302'. We improved this by using **Query Expansion** (generating synonyms) and **Hybrid Search** (combining keyword search with semantic search)."

---

## 9. General Backend Concepts (Bonus Prep)

Here are rapid-fire concepts you might be asked, related to this project:

*   **ACID Properties:** Atomicity, Consistency, Isolation, Durability. (Important for your SQL DB).
*   **REST vs. GraphQL:** This project uses REST (FastAPI). REST is standard, cacheable, and simpler for this use case.
*   **Dependency Injection:** FastAPI uses this heavily (e.g., `Depends(get_db)`). It allows us to swap dependencies (like using a Mock DB for testing) easily.
*   **Asynchronous Programming (Async/Await):** Python's `asyncio` allows the server to handle thousands of requests concurrently by not blocking the thread while waiting for I/O (like DB or API calls).
*   **Vector Embeddings:** A way to represent text as numbers (arrays of floats) where similar meanings have similar numbers (close distance).

---

## 10. Preparation Checklist

- [ ] **Review `main.py`:** Understand the `lifespan` event (startup/shutdown logic).
- [ ] **Review `graph.py`:** Be able to draw the node flow on a whiteboard.
- [ ] **Review `models.py`:** Know your table structure.
- [ ] **Review `vectorstore.py`:** Understand how you insert and query vectors.

**Good Luck! You have built a sophisticated system using modern AI patterns.**
