import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection():
    url = "sqlite+aiosqlite:///./nyayamgpt.db"
    logger.info(f"Testing connection to {url}")
    
    try:
        engine = create_async_engine(url, echo=True)
        logger.info("Engine created")
        
        async with engine.connect() as conn:
            logger.info("Connection acquired")
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"Query result: {result.scalar()}")
            
        await engine.dispose()
        logger.info("Engine disposed")
        
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
