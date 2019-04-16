from functools import wraps
from typing import Union, Type, Callable, Optional, Any
from types import TracebackType

from ._error import CancelledError
from ._scheduler import Scheduler, Event


__all__ = ("Timeout",)


class Timeout:
    def __init__(self, seconds: Union[float, int], *,
                 exception: Optional[Type[BaseException]] = CancelledError,
                 scheduler: Optional[Scheduler] = None) -> None:
        assert exception is None or issubclass(exception, CancelledError)
        assert scheduler is not None
        self._seconds = seconds
        self._exception = type("_CancelledError", (exception or CancelledError,), {})
        self._silent = exception is None
        self._scheduler = scheduler
        self._event = None  # type: Union[Event, None]

    def __enter__(self) -> None:
        if self._seconds > 0:
            self._event = self._scheduler.new(self._seconds, self._exception)
        pass

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> bool:
        self._scheduler.cancel(self._event)
        if isinstance(exc_val, self._exception):
            return self._silent
        return exc_val is None

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            with self:
                return fn(*args, **kwargs)
        return wrapped
