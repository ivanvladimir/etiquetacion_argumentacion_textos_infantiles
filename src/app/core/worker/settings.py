from arq import Worker
import asyncio
from arq.connections import RedisSettings

from ...core.config import settings
from .functions import sample_background_task, shutdown, startup

REDIS_QUEUE_HOST = settings.REDIS_QUEUE_HOST
REDIS_QUEUE_PORT = settings.REDIS_QUEUE_PORT



class WorkerSettings:
    functions = [sample_background_task]
    redis_settings = RedisSettings(host='redis', port=REDIS_QUEUE_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False

async def main():
    worker = Worker(WorkerSettings)
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
