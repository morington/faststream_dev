import asyncio

import structlog
from faststream import FastStream
from faststream.nats import NatsBroker, NatsRouter
from faststream.nats.message import NatsMessage

from src.infrastructure.logger.loggers import InitLoggers

logger = structlog.getLogger(InitLoggers.main.name)
router = NatsRouter()

@router.subscriber(subject="test", no_ack=True)
async def sub_test(msg: str, nats_msg: NatsMessage):
    await logger.adebug("New message")
    await logger.ainfo(msg, t_nats_msg=type(nats_msg), nats_msg=nats_msg)
    await nats_msg.ack()

async def main() -> None:
    broker = NatsBroker(
        servers=["nats://127.0.0.1:30114"]
    )
    broker.include_router(router)
    await broker.connect()

    app = FastStream(broker)
    await app.run()

if __name__ == "__main__":
    InitLoggers()
    asyncio.run(main())