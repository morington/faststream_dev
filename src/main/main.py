import asyncio

import structlog
from faststream.nats import NatsBroker

from src.infrastructure.logger.loggers import InitLoggers
from src.main import subs

logger = structlog.getLogger(InitLoggers.main.name)


async def main() -> None:
    await logger.ainfo("Start app")

    broker = NatsBroker(
        servers=["nats://127.0.0.1:30114"]
    )
    broker.include_router(subs.router)
    await broker.connect()

    await broker.publish(
        message="hello world!",
        subject="test"
    )

    #p = broker.publisher(subject="test2")

    # @broker.publisher(subject="test2")
    # async def r() -> str:
    #     result = str(2*2)
    #     await logger.ainfo(result)
    #     return result
    #     # await p.publish(result)
    #
    # await r()


if __name__ == "__main__":
    InitLoggers()
    asyncio.run(main())
