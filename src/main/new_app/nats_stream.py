import asyncio
from datetime import datetime, timedelta
from functools import partial
from typing import Optional

import structlog
from nats.aio.client import Client as NATS
from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy
from nats.errors import TimeoutError as NATSTimeoutError
import ormsgpack

logger: structlog.BoundLogger = structlog.getLogger("NATSClient")


class NATSClient:
    def __init__(self, servers: Optional[list[str]] = None):
        self.nc = NATS()
        self.servers = servers or ["nats://127.0.0.1:4222"]
        self.js = None  # JetStream context
        self.tasks = []  # Список для хранения фоновых задач

    async def connect(self):
        await self.nc.connect(servers=self.servers)
        self.js = self.nc.jetstream()
        await logger.ainfo("Connected to NATS JetStream.")

    async def disconnect(self):
        # Отменяем все фоновые задачи
        for task in self.tasks:
            task.cancel()
        # Ждем, пока все задачи завершатся
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Закрываем соединение
        await self.nc.close()
        await logger.ainfo("Disconnected from NATS.")

    async def create_stream(self, name, subjects):
        # Проверяем, существует ли поток, чтобы избежать ошибок
        try:
            await self.js.stream_info(name)
            await logger.ainfo(f"Stream '{name}' already exists.")
        except Exception:
            await self.js.add_stream(name=name, subjects=subjects)
            await logger.ainfo(f"Stream '{name}' created with subjects {subjects}.")

    async def add_subscription(self, subject, durable_name, callback, delay=50):
        # Создаем ConsumerConfig
        consumer_config = ConsumerConfig(
            durable_name=durable_name,
            ack_policy=AckPolicy.EXPLICIT,
            ack_wait=2 * delay,  # Используем timedelta
            deliver_policy=DeliverPolicy.ALL,  # Начинаем с первого сообщения
        )
        # Создаем Pull-подписку
        pull_sub = await self.js.pull_subscribe(
            subject, durable=durable_name, config=consumer_config
        )
        # Запускаем задачу для обработки сообщений
        task = asyncio.create_task(
            self.process_messages(pull_sub, callback)
        )
        self.tasks.append(task)

    async def process_messages(self, pull_sub, callback):
        try:
            while True:
                try:
                    # Запрашиваем одно сообщение
                    msgs = await pull_sub.fetch(1, timeout=5)
                    for msg in msgs:
                        await callback(msg)  # Передаем msg в коллбек
                except NATSTimeoutError:
                    # Нет новых сообщений, продолжаем цикл
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Задача была отменена, выходим из цикла
            pass
        finally:
            await pull_sub.unsubscribe()

    async def publish(self, subject, message):
        await logger.adebug("Send message", message=message, subject=subject)
        data = ormsgpack.packb(message)
        await self.js.publish(subject, data)


async def main():
    nats_client = NATSClient(servers=["nats://localhost:4222"])
    await nats_client.connect()

    # Создаем поток (Stream) с нужным subject
    await nats_client.create_stream(name="TestStream", subjects=["TestSubject"])

    # Список для хранения временных меток обработки сообщений
    timestamps = []

    # Пример функции коллбека с записью времени
    async def example_callback(msg, x: int):
        await asyncio.sleep(5)
        data = ormsgpack.unpackb(msg.data)
        print(f"Received message: {data} x={x}")
        # Проверяем успешность обработки

        await msg.ack()

    x = 5

    # Добавляем подписку с задержкой в 5 секунд
    await nats_client.add_subscription(
        subject="TestSubject",
        durable_name="TestSubjectConsumer",
        callback=partial(example_callback, x=x),
    )
    await nats_client.add_subscription(
        subject="TestSubject",
        durable_name="TestSubjectConsumer",
        callback=partial(example_callback, x=x),
    )

    # Публикуем несколько сообщений
    for i in range(10):
        await nats_client.publish("TestSubject", {"text": f"Hello World {i + 1}!", "result": True if 1 == 2 else False})

    # Ждем завершения обработки всех сообщений
    await asyncio.sleep(100)  # Даем время на обработку всех сообщений

    await nats_client.disconnect()

    # Выводим временные метки
    print("\nTimestamps of message processing:")
    for timestamp in timestamps:
        print(timestamp.strftime('%H:%M:%S'))


if __name__ == "__main__":
    asyncio.run(main())