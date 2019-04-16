from functools import wraps
from typing import Union, Type, Optional, Any
from types import TracebackType

from ._errors import CancelledError
from ._scheduler import Scheduler, Event
from ._types import ExceptionType, AnyCallable, TimeoutValue


__all__ = ("Timeout", "TimeoutProxy",)


class TimeoutProxy:
    def __init__(self, timeout: "Timeout") -> None:
        self._timeout = timeout

    @property
    def exception(self) -> Union[ExceptionType, None]:
        return self._timeout.exception

    @property
    def remaining(self) -> TimeoutValue:
        return self._timeout.remaining


class Timeout:
    def __init__(self, scheduler: Scheduler,
                 seconds: Union[float, int],
                 exception: Optional[ExceptionType] = CancelledError) -> None:
        assert exception is None or issubclass(exception, CancelledError)
        self._scheduler = scheduler
        self._seconds = seconds
        self._exception = type("_CancelledError", (exception or CancelledError,), {})
        self._silent = exception is None
        self._event = None  # type: Union[Event, None]

    @property
    def exception(self) -> Union[ExceptionType, None]:
        return self._exception

    @property
    def remaining(self) -> TimeoutValue:
        if self._event:
            return self._scheduler.get_remaining(self._event)
        return 0

    def __enter__(self) -> TimeoutProxy:
        if self._seconds > 0:
            self._event = self._scheduler.new(self._seconds, self._exception)
        return TimeoutProxy(self)

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> bool:
        self._scheduler.cancel(self._event)
        if isinstance(exc_val, self._exception):
            return self._silent
        return exc_val is None

    def __call__(self, fn: AnyCallable) -> AnyCallable:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            with self:
                return fn(*args, **kwargs)
        return wrapped
