from asyncio import sleep as async_sleep
from time import sleep as sync_sleep


class ignore_exception:
    def __init__(self, exception, delay):
        self._exception = exception
        self._delay = delay

    def __enter__(self):
        pass

    async def __aenter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, self._exception):
            sync_sleep(self._delay)
            return True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, self._exception):
            await async_sleep(self._delay)
            return True
