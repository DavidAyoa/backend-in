"""
Standalone WebSocket server implementation
Following pipecat documentation patterns exactly
"""
import asyncio
import structlog
from .pipeline import pipeline
from .config import config

logger = structlog.get_logger()

async def main():
    """Main entry point for the standalone WebSocket server"""
    logger.info("Starting Voice Agent WebSocket Server")
    
    try:
        await pipeline.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await pipeline.stop()
    except Exception as e:
        logger.error("Server error", error=str(e))
        await pipeline.stop()
        raise

if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Run the server
    asyncio.run(main())
