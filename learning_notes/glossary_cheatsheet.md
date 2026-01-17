# General Interview Cheatsheet: Glossary

A quick reference for terms you might encounter.

## Backend
*   **CRUD:** Create, Read, Update, Delete (Basic DB operations).
*   **ORM (SQLAlchemy):** Object Relational Mapper. Converts Python Classes (`User`) to SQL Tables (`users`). Lets you write python code instead of raw SQL queries.
*   **JWT (JSON Web Token):** A secure string ("headers.payload.signature") given to logged-in users. They send it in the header to prove who they are. Be stateless (server doesn't remember logged in users, just verifies the signature).
*   **Trace/Span (OpenTelemetry):**
    *   **Trace:** The journey of a single request through the whole system.
    *   **Span:** A single unit of work (e.g., "DB Query", "Gemini Call") within that trace. Used for debugging slowness.

## AI / LLM
*   **Hallucination:** When an LLM confidently states a fact that is false. RAG prevents this.
*   **Context Window:** The limit of how much text an LLM can read at once (e.g., 128k tokens).
*   **Token:** A piece of a word. roughly 0.75 words. 1000 tokens ≈ 750 words.
*   **Temperature:** A setting (0.0 to 1.0).
    *   0.0 = Deterministic, factual, boring. (We use this for Legal RAG).
    *   0.8 = Creative, random. (Good for poetry).
*   **Zero-Shot vs Few-Shot Prompting:**
    *   **Zero-Shot:** "Translate this to French: Hello." (No examples given).
    *   **Few-Shot:** "Translate like this: Dog->Chien, Cat->Chat. Now translate: Hello." (Examples given to guide style).

## Python
*   **Virtual Environment (venv/conda):** An isolated folder with specific library versions for *this* project, so it doesn't conflict with other projects on your laptop.
*   **Type Hits (`def func(x: int) -> str`):** Optional in Python, but enforces discipline and helps IDEs (VS Code) give autocomplete. FastAPI requires them.
*   **Decorator (`@app.get`):** A function that wraps another function to add behavior (like registering a route or logging).
