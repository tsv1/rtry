from functools import partial

from ._errors import CancelledError
from ._retry import Retry
from ._scheduler import Scheduler
from ._timeout import Timeout


__all__ = ("retry", "timeout", "CancelledError",)
__version__ = "1.0.6"


_scheduler = Scheduler()
timeout = partial(Timeout, _scheduler)
retry = partial(Retry, timeout)
