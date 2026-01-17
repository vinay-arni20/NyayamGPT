# FastAPI Deep Dive: Complete Mastery Guide

## Table of Contents
1. [What is FastAPI?](#1-what-is-fastapi)
2. [Asynchronous Programming](#2-asynchronous-programming)
3. [Pydantic Validation](#3-pydantic-validation)
4. [Dependency Injection](#4-dependency-injection)
5. [Middleware](#5-middleware)
6. [Routing & API Organization](#6-routing--api-organization)
7. [Error Handling](#7-error-handling)
8. [Real Project Examples](#8-real-project-examples)

---

## 1. What is FastAPI?

FastAPI is a **modern, high-performance web framework** for building APIs with Python 3.8+ based on **standard Python type hints**.

### Why is it special?

**1. Speed (Performance)**
- One of the **fastest Python frameworks** available
- On par with NodeJS and Go frameworks
- Built on **Starlette** (async web framework) and **Pydantic** (data validation)
- Uses **ASGI** (Asynchronous Server Gateway Interface) instead of WSGI

**2. Auto-Generated Documentation**
- Automatic **Swagger UI** at `/docs`
- Automatic **ReDoc** at `/redoc`
- Based on **OpenAPI** and **JSON Schema** standards
- No manual documentation needed!

**3. Type Safety**
- Leverages Python **Type Hints** (introduced in Python 3.5+)
- Catches bugs at development time (IDE shows errors)
- Better autocomplete in VS Code/PyCharm
- Self-documenting code

### Real-World Analogy
Think of FastAPI as a **smart restaurant system**:
- **Flask/Django** = Traditional kitchen: One chef handles one order at a time
- **FastAPI** = Modern kitchen: Multiple chefs work simultaneously, switching between tasks when waiting for something to cook

---

## 2. Core Concept: Asynchronous Programming (`async` / `await`)

This is the key to its speed.

### Traditional (Sync) vs. Async
*   **Sync (Flask/Django):** A waiter takes an order, gives it to the kitchen, and **stands there waiting** until the food is ready before serving another table. If the kitchen takes 5 mins, the waiter does nothing for 5 mins.
*   **Async (FastAPI):** A waiter takes an order, gives it to the kitchen, and immediately goes to serve another table. When the food is ready, they come back.

### Code Example
```python
import asyncio

# BLOCKS everything for 1 second
def sync_operation():
    time.sleep(1) 

# DOES NOT BLOCK. While waiting, the server handles other requests.
async def async_operation():
    await asyncio.sleep(1)
```

**Interview Answer:** "I use `async def` for my route handlers so that when my API calls the Database or the LLM (which takes time), the server helps other users instead of freezing."

---

## 3. Pydantic: Data Validation

FastAPI doesn't just receive JSON; it validates it into Python objects using Pydantic.

**Why use it?**
*   Guarantees the data is correct.
*   Converts types automatically (String "5" becomes Int 5).
*   Gives clear error messages to the client.

```python
from pydantic import BaseModel, EmailStr

class UserSignup(BaseModel):
    username: str
    email: EmailStr  # Automatic email validation!
    age: int = 18    # Default value

# FastAPI Route
@app.post("/users/")
async def create_user(user: UserSignup):
    # 'user' is already a valid python object here. 
    # If client sent "age": "five", FastAPI returns 422 Error automatically.
    return {"message": f"Created user {user.username}"}
```

---

## 4. Dependency Injection (`Depends`)

This is FastAPI's "Killer Feature". It allows you to declare things required by your route (like a DB session or a User Token) and FastAPI provides them automatically.

### How it works
You define a function that does the setup/teardown logic, and pass it to the route.

```python
# 1. Define the dependency
def get_db():
    db = SessionLocal()
    try:
        yield db  # Give the DB to the route
    finally:
        db.close() # Clean up after route finishes

# 2. Use it in a route
@app.get("/items/")
async def read_items(db: Session = Depends(get_db)):
    # You don't call get_db(). FastAPI calls it, 
    # gives you the result, and cleans up after.
    return db.query(Item).all()
```

**Interview Answer:** "I use `Depends` for managing database sessions and authentication. It makes testing easier because I can override dependencies (mock the DB) during tests."

---

## 5. Middleware

Middleware is code that runs **before** and **after** every single request.

*   **Before:** Check if IP is banned? Start a timer?
*   **Request Processed:** Route handler runs.
*   **After:** Add headers? Log how long it took?

**NyayamGPT Example (`main.py`):**
*   **CORSMiddleware:** Allows your frontend (running on port 5173) to talk to backend (port 8000).
*   **GZipMiddleware:** Compresses large JSON responses (like legal docs) to save bandwidth.

---

## 6. The `APIRouter`

Instead of putting all routes in one file (`main.py`), we splits them.

*   `app/api/routes/auth.py` -> Handles /login, /signup
*   `app/api/routes/search.py` -> Handles /search

In `main.py`:
```python
from app.api.routes import auth, search

app.include_router(auth.router, prefix="/auth")
app.include_router(search.router, prefix="/search")
```
This keeps the code organized.
