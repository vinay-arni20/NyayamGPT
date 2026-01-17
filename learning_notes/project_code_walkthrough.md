# NyayamGPT - Comprehensive Code Walkthrough

This guide explains **your specific project implementation** line-by-line. Use this to demonstrate deep knowledge of your codebase during the interview.

---

## Module 1: Entry Point (`app/main.py`)

This is where the application starts.

### 1. The Lifespan Manager (Startup/Shutdown)
Instead of running setup code globally (which slows down imports), we use `lifespan`.

**Code Snippet:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # 1. Startup Logic
    logger.info("Starting NyayamGPT")
    setup_tracing()          # Start OpenTelemetry
    await DatabaseManager.initialize() # Connect to Postgres via SQLAlchemy
    
    # 2. Background Task (Non-Blocking)
    import asyncio
    asyncio.create_task(initialize_vector_store()) 
    
    yield  # Application runs here...
    
    # 3. Shutdown Logic
    await close_cache_service()
    await DatabaseManager.shutdown()
```

**Interview Explanation:**
"I used the `lifespan` context manager. Before the first request is handled, I initialize the DB and start Tracing. Critically, I load the **Vector Store in a background task** (`asyncio.create_task`) so the server starts instantly without waiting for the heavy AI models to load into memory."

### 2. Middleware (The "Guards")
```python
app = FastAPI(title="NyayamGPT")
app.add_middleware(CORSMiddleware, allow_origins=["*"]) # Allow React Frontend
app.add_middleware(GZipMiddleware) # Compress large JSON responses
```

**Why GZip?**
"Legal documents are large text blocks. GZip compresses them, reducing the JSON size by ~70%, making the app feel faster on slow networks."

---

## Module 2: Authentication (`app/auth/dependencies.py`)

How do we secure endpoints?

### 1. `get_current_user` Dependency
This function checks the JWT token on every request.

**Code Snippet:**
```python
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    # 1. Check if token exists
    if not credentials:
        return None
    
    token = credentials.credentials
    # 2. Decode Token (Verify Signature)
    payload = decode_token(token, token_type="access")
    
    # 3. Check Blacklist (Logout feature)
    jti = payload.get("jti") # Unique Token ID
    if await crud.is_token_blacklisted(db, jti):
        logger.warning("Blacklisted token used")
        return None
        
    # 4. Return User object
    return await crud.get_user_by_id(db, payload.get("sub"))
```

**Real Life Example:**
"When a user logs out, we can't 'delete' the token from their phone. So, we add the token's ID (`jti`) to a **Blacklist** in Redis/DB. This function checks that list before accepting the token."

---

## Module 3: The AI Brain (`app/agents/graph.py`)

This explains how LangGraph orchestrates the logic.

### 1. Conditional Routing
We don't just run A -> B -> C. We decide where to go.

**Code Snippet:**
```python
workflow = StateGraph(GraphState)

# Verify if we need to ask user for more info
workflow.add_conditional_edges(
    "classify_intent",
    should_clarify,
    {
        "clarify": "collect_missing_details", # Go to Q&A mode
        "draft": "draft_document",           # Go to drafting mode
        "continue": "rewrite_query"          # Go to RAG mode
    }
)
```

**Interview Explanation:**
"This is the **Router Pattern**. After the user speaks, the `classify_intent` node runs. Based on its output, `should_clarify` acts as a switch statement to direct the flow. If the user says 'Hello', we don't search the Vector DB; we just route to a greeting node."

---

## Module 4: Node Logic (`app/agents/nodes.py`)

This contains the actual work functions.

### 1. Vector Search + Re-ranking Strategy
**Code Snippet:**
```python
def _format_docs_as_context(docs: list[SearchResult]) -> str:
    # Filter out low quality results
    relevant_docs = [doc for doc in docs if doc.score >= MIN_RELEVANCE_SCORE]
    
    if not relevant_docs:
        return "No relevant documents found."
        
    # Format for LLM
    context_parts = []
    for doc in relevant_docs:
        context_parts.append(
            f"[Document] (Relevance: {doc.score:.2f})\n"
            f"Law: {doc.metadata.law}\n"
            f"Section: {doc.metadata.section}\n"
            f"Content: {doc.text}\n"
        )
    return "\n---\n".join(context_parts)
```

**Key Concepts:**
*   **Thresholding:** `doc.score >= MIN_RELEVANCE_SCORE` (0.3). If the similarity is too low, we discard it to prevent confusing the LLM with irrelevant laws.
*   **Context Injection:** We explicitly label `[Document]` so Gemini knows these are external facts, not its own training data.

---

## Module 5: External Services (`app/services/gemini_client.py`)

Wrapper for Google's API.

### 1. Key Rotation & Caching
**Code Snippet:**
```python
class GeminiClient:
    def __init__(self):
        self.api_keys = settings.all_gemini_keys
        self.cache = FileCache() # Simple JSON cache

    def get_completion(self, prompt):
        # 1. Check Cache first
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached: return cached
        
        # 2. Call API (with failover)
        try:
            return api.generate(prompt)
        except RateLimitError:
            self.rotate_key() # Switch to next API Key
            return self.retry()
```

**Interview Explanation:**
"To handle production loads: 1) I implemented **Client-Side Caching**—if the same question is asked, I return the cached answer instantly. 2) I implemented **Key Rotation**—if one Gemini API key hits the free tier limit, the code automatically switches to the next key in the list."

---

## Module 6: Database Models (`app/db/models.py`)

### 1. The Chat Session Schema
**Code Snippet:**
```python
class ChatSession(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan" # If Session deleted, delete messages too
    )
```

**ORM Concept:**
"I used **SQLAlchemy 2.0** style (`Mapped[]`). The `cascade='all, delete-orphan'` is crucial—it ensures data integrity. If a user deletes a chat history, the database automatically cleans up all the messages inside it so we don't have 'orphan' data."

---

## Summary for Interview

When showing your project:
1.  **Start at `main.py`:** "Here is how I boot up the async server."
2.  **Go to `graph.py`:** "This is the brain. It's not just a script; it's a State Machine."
3.  **Show `nodes.py`:** "Here is the RAG logic with relevance filtering."
4.  **Show `gemini_client.py`:** "Here is my robust wrapper with multiple API keys."
