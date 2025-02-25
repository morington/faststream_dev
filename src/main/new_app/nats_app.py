import asyncio
from typing import Optional

import structlog
from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy
from nats.errors import TimeoutError as NATSTimeoutError
import ormsgpack

from src.infrastructure.logger.loggers import InitLoggers

logger = structlog.getLogger(InitLoggers.main.name)


class NATSKeyValueClient:
    def __init__(self, servers: Optional[list[str]] = None):
        self.nc = Client()
        self.servers = servers or ["nats://127.0.0.1:30114"]
        self.js = None  # Контекст JetStream
        self.kv = None  # Экземпляр KV-бакета
        self.watch_task = None  # Фоновая задача для отслеживания изменений

    async def connect(self):
        await self.nc.connect(servers=self.servers)
        self.js = self.nc.jetstream()
        await logger.ainfo("Connected to NATS JetStream.")

    async def disconnect(self):
        if self.watch_task:
            self.watch_task.cancel()
            await asyncio.gather(self.watch_task, return_exceptions=True)
        await self.nc.close()
        await logger.ainfo("Disconnected from NATS.")

    async def put_value(self, key: str, value):
        data = ormsgpack.packb(value)
        await self.kv.put(key, data)
        await logger.adebug("Put key-value", key=key, value=value)

    async def get_value(self, key: str):
        entry = await self.kv.get(key)
        value = ormsgpack.unpackb(entry.value)
        await logger.adebug("Got key-value", key=key, value=value)
        return value

    # async def watch_bucket(self, callback):
    #     # Функция для наблюдения за всеми изменениями в бакете
    #
    #     async def watch():
    #         await logger.adebug("Create new watch", callback=callback.__name__)
    #         async for entry in await self.kv.watchall():
    #             await logger.adebug(entry)
    #             await callback(entry)
    #     self.watch_task = asyncio.create_task(watch())

    async def watch_bucket(self, bucket_name, callback):
        await logger.adebug("Create new watch", callback=callback.__name__)
        # Используем имя бакета, сохранённое при создании/получении KV
        subject = f"$KV.{bucket_name}.>"
        consumer_config = ConsumerConfig(
            durable_name=f"{bucket_name}_watcher",
            ack_policy=AckPolicy.EXPLICIT,
            deliver_policy=DeliverPolicy.ALL  # Получаем только новые сообщения
        )
        # Создаем подписку на изменения в бакете (он реализован как стрим)
        sub = await self.js.subscribe(
            subject,
            durable=f"{bucket_name}_watcher",
            config=consumer_config
        )

        async def watch():
            async for msg in sub.messages:
                # await logger.adebug("Received update", msg=msg)
                await callback(msg)

        self.watch_task = asyncio.create_task(watch())


async def main():
    nats_client = NATSKeyValueClient(servers=["nats://localhost:30114"])
    await nats_client.connect()

    # Создаём или получаем KV-бакет с именем "TestBucket"
    bucket_name = "TestBucket"
    # await nats_client.create_bucket(bucket_name)

    # Пример функции-колбэка, вызываемой при изменениях в бакете
    async def example_callback(msg: Msg):
        print(f"{msg.data}")
        await msg.ack()

    # Запускаем наблюдение за изменениями в бакете
    await nats_client.watch_bucket(bucket_name, example_callback)

    # Даем время на получение уведомлений наблюдателя
    await asyncio.Event().wait()

    await nats_client.disconnect()


if __name__ == "__main__":
    InitLoggers()
    asyncio.run(main())
