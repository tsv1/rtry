from functools import partial

from ._error import CancelledError
from ._retry import Retry
from ._scheduler import Scheduler
from ._timeout import Timeout


__all__ = ("retry", "timeout", "CancelledError")
__version__ = "1.0.6"


scheduler = Scheduler()
timeout = partial(Timeout, scheduler=scheduler)
retry = partial(Retry, timeout_factory=timeout)
