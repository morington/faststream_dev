import asyncio

import structlog

from src.infrastructure.logger.loggers import InitLoggers

logger = structlog.getLogger(InitLoggers.main.name)


async def main():
    await logger.ainfo("Start app")


if __name__ == "__main__":
    asyncio.run(main())
