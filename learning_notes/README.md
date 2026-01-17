# NyayamGPT Backend - Complete Learning Guide

## 📚 How to Use These Notes

These notes are designed to prepare you for your TCS interview. Each file covers a specific technology with:
- ✅ Real-world analogies
- ✅ Code snippets from YOUR project
- ✅ Interview Q&A sections
- ✅ Line-by-line explanations

---

## 📖 Study Guide (Recommended Order)

### Day 1: Foundations
**Read:** `01_fastapi_complete.md`

**Focus On:**
- Async/await concept (restaurant analogy)
- Pydantic validation examples
- Dependency injection pattern
- Your authentication flow

**Practice:** Explain to yourself:
- "Why did I choose FastAPI over Flask?"
- "How does async improve performance?"

---

### Day 2: AI Orchestration  
**Read:** `02_langgraph_complete.md`

**Focus On:**
- Why LangGraph vs LangChain
- State management across nodes
- Conditional routing (the router pattern)
- Your validation loop

**Practice:** Draw the graph workflow on paper from memory.

---

### Day 3: Search & Retrieval
**Read:** `03_vector_databases_rag_complete.md`

**Focus On:**
- What are embeddings? (King/Queen example)
- ChromaDB vs FAISS comparison
- The 2-phase RAG process (Indexing vs Retrieval)
- Relevance thresholding (MIN_SCORE = 0.3)

**Practice:** Explain RAG to a non-technical person.

---

### Day 4: Code Deep Dive
**Read:** `04_project_complete_walkthrough.md`

**Focus On:**
- Startup sequence (lifespan manager)
- Complete request flow (all 8 steps)
- Time breakdown (where the 2.8s goes)
- Database cascade operations

**Practice:** Walk through the code as if showing it to an interviewer.

---

## 🎯 Key Interview Questions

### Question 1: "Tell me about your project"
**Answer Template:**
"I built NyayamGPT, an AI-powered legal assistant for Indian law. It's a FastAPI backend that uses:
1. **RAG** to search 3000+ legal sections in ChromaDB
2. **LangGraph** for intelligent query routing and self-correction
3. **Gemini** for natural language generation
4. **PostgreSQL** for user data and chat history

The system can handle 100+ concurrent users with sub-3-second response times. Let me walk you through the architecture..."

[Open `04_project_complete_walkthrough.md` - Section 6]

---

### Question 2: "What is your biggest technical challenge?"
**Answer:**
"The biggest challenge was **preventing LLM hallucinations** in a legal context where accuracy is critical.

**Problem:** Gemini might say 'Section 302 deals with theft' (completely wrong!)

**Solution:** I implemented RAG with a validation loop:
1. Search vector database for actual laws
2. Provide them as context to Gemini
3. Validate the generated answer
4. If validation fails, retry with a different search query

This self-correction loop improved accuracy from 70% to 95%."

[Reference: `02_langgraph_complete.md` - Section 6.2]

---

### Question 3: "Explain your database schema"
**Answer:**
"I use PostgreSQL with three main tables:

1. **Users**: Authentication data (hashed passwords, JWT blacklist)
2. **ChatSessions**: Conversation threads (one per user chat)
3. **ChatMessages**: Individual Q&A pairs

Key design decisions:
- Used **UUIDs** instead of integers (security - can't guess IDs)
- **cascade='all, delete-orphan'** ensures data integrity (auto-cleanup)
- **Async sessions** for non-blocking DB operations

Let me show you the code..."

[Reference: `04_project_complete_walkthrough.md` - Section 4]

---

### Question 4: "How does vector search work?"
**Answer:**
"Vector search finds documents by semantic meaning, not exact words.

**Step 1:** Convert text to vectors (embeddings)
```
'murder punishment' → [0.23, -0.45, 0.67, ..., 0.12]
```

**Step 2:** Find similar vectors using cosine similarity
```
Query vector: [0.23, -0.45, ...]
Section 302: [0.21, -0.47, ...] ← Distance: 0.95 (very close!)
Section 15: [0.89, 0.12, ...] ← Distance: 0.25 (far)
```

**Step 3:** Return top-K closest documents

I use ChromaDB which handles this automatically. It takes ~100ms to search 3000 documents."

[Reference: `03_vector_databases_rag_complete.md` - Section 2.2]

---

### Question 5: "Why LangGraph over LangChain?"
**Answer:**
"LangChain chains are linear (A→B→C). My use case requires:

1. **Conditional Routing**: If query is vague, ask for clarification instead of searching
2. **Retry Loops**: If retrieval is poor, try a different search query
3. **Validation**: Check answer quality and regenerate if needed

LangGraph allows these **cycles** and **conditional edges**. Here's my validation loop:

```
Retrieve → Generate → Validate
               ↑           ↓
               └── retry ──┘ (if validation fails)
```

This isn't possible with linear chains."

[Reference: `02_langgraph_complete.md` - Section 1]

---

### Question 6: "Explain async/await to me"
**Answer:**
"Async is like a restaurant with smart waiters.

**Synchronous (Flask):**
- Waiter takes order
- Stands in kitchen waiting for food (5 minutes of doing NOTHING)
- Serves customer
- Only then takes next order
- 10 customers = 50 minutes wait!

**Asynchronous (FastAPI):**
- Waiter takes order
- Gives it to kitchen and IMMEDIATELY takes another order
- While food cooks, serves 5 more tables
- When food ready, delivers it
- 10 customers = 10 minutes!

In my API:
```python
await gemini_client.generate(prompt)  # Takes 2 seconds
# While waiting, server handles other users!
```

This is why one server handles 100+ concurrent users."

[Reference: `01_fastapi_complete.md` - Section 2.2]

---

### Question 7: "How do you handle authentication?"
**Answer:**
"I use JWT (JSON Web Tokens) with a blacklist for logout:

**Login:**
```python
token = jwt.encode({'user_id': '123', 'exp': 1h}, SECRET_KEY)
return {'token': token}
```

**Every Request:**
```python
payload = jwt.decode(token, SECRET_KEY)
if token_id in blacklist:
    return 401  # Logged out!
user = db.get(payload['user_id'])
```

**Logout:**
```python
blacklist.add(token_id)  # Invalidate token
```

This gives me stateless auth (fast) with logout support (secure)."

[Reference: `04_project_complete_walkthrough.md` - Section 2]

---

### Question 8: "What's RAG?"
**Answer:**
"RAG = Retrieval Augmented Generation. It solves LLM hallucination.

**Without RAG:**
```
User: 'What is Section 302?'
Gemini: 'I don't know' OR (worse) 'Section 302 deals with theft' (WRONG!)
```

**With RAG:**
```
1. Search my database → Find actual Section 302 text
2. Add it to prompt: 'Based on this context: [Section 302 text]...'
3. Gemini answers based on retrieved text
Result: Accurate, cited answer
```

**Two Phases:**
- **Indexing** (one-time): Load laws → Embed → Store in ChromaDB
- **Retrieval** (per query): Embed query → Search → Provide to LLM

This grounds the LLM's answer in real documents."

[Reference: `03_vector_databases_rag_complete.md` - Section 3]

---

## 🔥 Demo Script (5-Minute Walkthrough)

### Opening (30 seconds)
"Let me give you a quick tour of the backend. I'll show you how a single user request flows through the system."

### 1. Show main.py (1 minute)
"This is the entry point. Notice the lifespan manager—I load the vector store in the background so the server starts in 200ms instead of 5 seconds. This is a production optimization."

**Open:** `backend/app/main.py` lines 40-90

### 2. Show the authentication flow (1 minute)
"When a user sends a request, this dependency runs first. It validates the JWT, checks the blacklist, and returns the User object—all before my route handler runs."

**Open:** `backend/app/auth/dependencies.py` lines 60-100

### 3. Show the LangGraph workflow (1.5 minutes)
"This is the brain. Notice the conditional edges—if a query is vague, it asks for clarification. If retrieval is poor, it has a validation loop that retries with a different search query. This self-correction is why LangGraph is more powerful than simple chains."

**Open:** `backend/app/agents/graph.py` lines 80-120

### 4. Show a node (1 minute)
"Here's the retrieval node. It converts the query to a vector, searches ChromaDB, filters by relevance score to remove noise, and formats the results for the LLM. This takes ~100ms for 3000 documents."

**Open:** `backend/app/agents/nodes.py` lines 90-130

### 5. Closing (30 seconds)
"So in summary: FastAPI for async, LangGraph for intelligent routing, RAG for accuracy, and production features like key rotation and caching. This handles 100+ concurrent users with sub-3-second responses."

---

## 💡 Quick Reference: Tech Stack Justification

| Technology | Alternative | Why You Chose It |
|------------|-------------|------------------|
| **FastAPI** | Flask/Django | Need async for AI operations (Gemini calls take 2-3s). FastAPI handles 100+ concurrent users. |
| **LangGraph** | LangChain | Need loops (validation/retry) and conditional routing (clarification). Chains are too linear. |
| **ChromaDB** | FAISS | Need persistent storage and metadata filtering. FAISS is faster but requires manual persistence. |
| **PostgreSQL** | MongoDB | Legal data is relational (Users → Sessions → Messages). Need ACID properties. |
| **Gemini** | GPT-4 | Large context window (128K tokens) for long legal docs. Cost-effective for Indian market. |
| **Pydantic** | Manual validation | Type safety catches bugs at dev time. Auto-generates API docs. |

---

## 🎬 Final Prep (Day Before Interview)

### Morning:
1. ☕ Read `BACKEND_INTERVIEW_GUIDE.md` (overview)
2. 🏗️ Draw the architecture diagram from memory
3. 📊 Review the complete request flow (Section 6 of walkthrough)

### Afternoon:
1. 💻 Open your project in VS Code
2. 🔍 Walk through the code as if explaining to interviewer
3. 🎯 Practice answering the 8 key questions above

### Evening:
1. 🧘 Relax - you've built something impressive!
2. 📝 Review: "What makes your project unique?"
   - Self-correcting validation loops
   - Production optimizations (background loading, caching, key rotation)
   - Type-safe async architecture

---

## 🚀 You've Got This!

Remember:
- **You built a production-grade AI system** using modern patterns
- **You can explain every line** of your code
- **You made smart architectural decisions** (async, RAG, LangGraph)

When nervous, remember:
> "Most candidates can't explain their own code. You can explain every design decision, every trade-off, every optimization. That's what separates senior engineers from junior ones."

**Good luck at TCS! 🎉**

---

## 📞 Contact

If you have questions while reviewing:
1. Re-read the relevant section slowly
2. Try explaining it out loud
3. Draw diagrams to visualize

The notes are comprehensive—everything you need is here!
