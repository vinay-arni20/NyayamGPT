# Vector Databases, RAG, & Embeddings: The Comprehensive Guide

To understand RAG (Retrieval Augmented Generation), you must master 3 things: Embeddings, Vector Stores, and Similarity Search.

---

## 1. Embeddings: The "Magic" of Translation

Computers don't understand text (English/Hindi). They only understand numbers.
**Embeddings** are a technique to convert Text -> List of Numbers (Vector).

*   "King" -> `[0.2, 0.9, 0.1]`
*   "Queen" -> `[0.21, 0.95, 0.15]` (Very similar numbers!)
*   "Apple" -> `[0.8, 0.1, 0.0]` (Very different numbers).

**Key Property:** Semantic Similarity.
In the vector space, words with similar **meanings** are physically close to each other, even if they don't share letters.
*   "Lawyer" and "Attorney" will have a high similarity score.
*   "Bank" (River) and "Bank" (Money) will have different vectors based on context.

**Your Project:**
You use models like `sentence-transformers/all-MiniLM-L6-v2`. It reads a legal section ("Section 302 IPC punishment for murder") and outputs a vector of 384 dimensions (384 floating point numbers).

---

## 2. Vector Databases (ChromaDB / FAISS)

Standard databases (SQL) search by exact match strings (`WHERE text LIKE '%murder%'`).
Vector Databases search by **Nearest Neighbor** in that numeric space.

### FAISS (Facebook AI Similarity Search)
*   **What it is:** A library for efficient similarity search of dense vectors, written in C++.
*   **Pros:** Extremely fast. Can search millions of vectors in milliseconds.
*   **Cons:** It's "In-Memory" (RAM). If app restarts, you lose the index (unless you save it to disk explicitly). It's a library, not a full "Server".
*   **Use case:** When you need raw speed and have a static dataset.

### ChromaDB
*   **What it is:** An open-source Vector Database optimized for developer productivity.
*   **Pros:**
    *   Persistent storage (saves to disk automatically).
    *   Handles metadata filtering (e.g., "Find vectors near 'murder' BUT only where `law = 'IPC'`").
    *   Easy Python API.
*   **Use case:** Building persistent RAG apps where you need to add/update documents over time.

**In NyayamGPT:** We likely use ChromaDB for storing the laws permanently so we don't have to re-index them every time the server starts.

---

## 3. The RAG Workflow (Retrieval Augmented Generation)

**Problem:** Gemini/GPT-4 was trained on data up to 2023. It doesn't know *your* private documents (or might hallucinate specific legal sections).
**Solution:** RAG. Give the LLM the answers and ask it to format them.

### Phase 1: Indexing (The Prep Work)
1.  **Load:** Read PDF/JSON of BNS/IPC.
2.  **Split:** Break text into chunks (e.g., 500 characters). *Why?* Because LLMs have token limits, and we want precise matches.
3.  **Embed:** Pass chunk through Embedding Model -> Get Vector.
4.  **Store:** Save `[Vector, Original Text, Metadata]` into ChromaDB.

### Phase 2: Retrieval (The Live Query)
1.  **User Asks:** "What is the punishment for theft?"
2.  **Embed Query:** Convert question to Vector using the **SAME** model as Phase 1.
3.  **Similarity Search:** ChromaDB finds the top 5 chunks closest to this query vector.
    *   *Result:* Section 378 (Theft), Section 379 (Punishment).
4.  **Augment:** Create a prompt:
    `Context: [Content of Sec 378, Content of Sec 379]`
    `Question: What is punishment for theft?`
5.  **Generate:** Send this prompt to Gemini. Gemini reads the context and answers efficiently.

---

## 4. Key Metrics for Interview

*   **Cosine Similarity:** The math formula used to measure distance between two vectors.
    *   1.0 = Identical direction (Same meaning).
    *   0.0 = Orthogonal (Unrelated).
    *   -1.0 = Opposite.
*   **Dimensions:** The size of the vector. (OpenAI `text-embedding-3-small` is 1536 dims; `all-MiniLM-L6-v2` is 384 dims).
*   **Chunk Overlap:** When splitting text, we often overlap chunks (e.g., Chunk 1: words 1-100, Chunk 2: words 80-180). This ensures we don't cut a sentence in half and lose context at the boundary.
