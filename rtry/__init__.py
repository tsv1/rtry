from functools import partial

from ._errors import CancelledError
from ._retry import Retry
from ._scheduler import AsyncScheduler, Scheduler
from ._timeout import Timeout

__all__ = ("retry", "timeout", "CancelledError",)
__version__ = "1.3.0"

_scheduler = Scheduler()
_async_scheduler = AsyncScheduler()
timeout = partial(Timeout, _scheduler, _async_scheduler)
retry = partial(Retry, timeout)
