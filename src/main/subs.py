import asyncio
import sys

import structlog
from dishka import make_async_container, AsyncContainer, FromDishka
from dishka.integrations.faststream import setup_dishka, FastStreamProvider, inject
from faststream import FastStream, context
from faststream.nats import NatsBroker, NatsRouter, KvWatch
from faststream.nats.annotations import NatsMessage
from faststream import ContextRepo

from src.infrastructure.logger.loggers import InitLoggers
# from src.main.di import ConfigProvider#, t_config

logger = structlog.getLogger(InitLoggers.main.name)
router = NatsRouter()

# @router.subscriber(subject="test", no_ack=True)
# async def sub_test(msg: str, nats_msg: NatsMessage):
#     await logger.adebug("New message")
#     await logger.ainfo(msg, t_nats_msg=type(nats_msg), nats_msg=nats_msg)
#     # await nats_msg.ack()
#
#     return "New test2 msg"

@router.subscriber(
    subject="result",
    kv_watch=KvWatch(bucket="miniapp")
)
@inject
async def miniapp_sub(new_value: int, config: FromDishka[ContextRepo]):
    await logger.ainfo(new_value, t_config=type(config), c=config)
    config.set_global("result", new_value)

##########
async def miniapp(container: AsyncContainer):
    config = await container.get(ContextRepo)

    while True:
        await asyncio.sleep(1)
        await logger.ainfo("App", result=config.get("result"))
##########

async def main() -> None:
    container = make_async_container(FastStreamProvider())

    broker = NatsBroker(
        servers=["nats://127.0.0.1:30114"]
    )
    broker.include_router(router)
    await broker.connect()

    app = FastStream(broker)
    setup_dishka(container=container, app=app, auto_inject=True)

    try:
        await asyncio.gather(app.run(), miniapp(container))
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    InitLoggers()
    asyncio.run(main())