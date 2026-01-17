import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import DatabaseManager
from app.core.logging import logger

async def test_db():
    print("Testing DB connection...")
    try:
        await DatabaseManager.initialize()
        print("DB Initialization successful")
        
        health = await DatabaseManager.health_check()
        print(f"Health check: {health}")
        
    except Exception as e:
        print(f"DB Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db())
