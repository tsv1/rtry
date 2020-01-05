import asyncio
import sys
from functools import wraps
from types import TracebackType
from typing import Any, Optional, Type, Union

from ._errors import CancelledError
from ._scheduler import AsyncEvent, AsyncScheduler, Event, Scheduler
from ._types import AnyCallable, ExceptionType, TimeoutValue

__all__ = ("Timeout", "TimeoutProxy", "AsyncTimeoutProxy",)


class TimeoutProxy:
    def __init__(self, timeout: "Timeout") -> None:
        self._timeout = timeout

    @property
    def exception(self) -> Union[ExceptionType, None]:
        return self._timeout.exception

    @property
    def remaining(self) -> TimeoutValue:
        return self._timeout.remaining

    def __repr__(self) -> str:
        return "TimeoutProxy(timeout({seconds}, exception={exception}))".format(
            seconds=self.remaining,
            exception=self.exception)


class AsyncTimeoutProxy(TimeoutProxy):
    def __repr__(self) -> str:
        return "AsyncTimeoutProxy(timeout({seconds}, exception={exception}))".format(
            seconds=self.remaining,
            exception=self.exception)


class Timeout:
    def __init__(self,
                 scheduler: Scheduler,
                 async_scheduler: AsyncScheduler,
                 seconds: TimeoutValue,
                 exception: Optional[ExceptionType] = CancelledError) -> None:
        assert exception is None or issubclass(exception, CancelledError)
        self._scheduler = scheduler
        self._async_scheduler = async_scheduler
        self._seconds = seconds
        self._orig_exception = exception or CancelledError
        self._exception = type("_CancelledError", (self._orig_exception,), {})
        self._silent = exception is None
        self._event = None  # type: Union[Event, None]
        self._raised = None  # type: Union[Event, None]

    @property
    def seconds(self) -> TimeoutValue:
        return self._seconds

    @property
    def exception(self) -> Union[ExceptionType, None]:
        return self._orig_exception if not self._silent else None

    @property
    def remaining(self) -> TimeoutValue:
        if self._event is None:
            return self._seconds

        if isinstance(self._event, AsyncEvent):
            return self._async_scheduler.get_remaining(self._event)
        return self._scheduler.get_remaining(self._event)

    def __enter__(self) -> TimeoutProxy:
        def sync_handler() -> None:
            self._scheduler.cancel(self._event)
            self._raised = self._exception()
            raise self._raised  # type: ignore

        if self._seconds > 0:
            self._event = self._scheduler.new(self._seconds, sync_handler)
        return TimeoutProxy(self)

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> bool:
        self._scheduler.cancel(self._event)
        if isinstance(exc_val, self._exception):
            return self._silent
        return exc_val is None

    async def __aenter__(self) -> AsyncTimeoutProxy:
        if sys.version_info >= (3, 7):  # pragma: no cover
            task = asyncio.current_task()
        else:  # pragma: no cover
            task = asyncio.Task.current_task()

        def async_handler(task: "Optional[asyncio.Task[None]]" = task) -> None:
            self._async_scheduler.cancel(self._event)
            if task:  # pragma: no branch
                self._raised = self._exception()
                task.cancel()

        if self._seconds > 0:
            self._event = self._async_scheduler.new(self._seconds, async_handler)
        return AsyncTimeoutProxy(self)

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> bool:
        self._async_scheduler.cancel(self._event)

        if isinstance(exc_val, asyncio.CancelledError) and \
           isinstance(self._raised, self._exception):
            if self._silent:
                return True
            raise self._raised  # type: ignore

        return exc_val is None

    def __call__(self, fn: AnyCallable) -> AnyCallable:
        if asyncio.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                async with self:
                    return await fn(*args, **kwargs)
            wrapped = async_wrapped
        else:
            @wraps(fn)
            def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
                with self:
                    return fn(*args, **kwargs)
            wrapped = sync_wrapped
        return wrapped

    def __repr__(self) -> str:
        return "timeout({seconds}, exception={exception})".format(
            seconds=self.seconds,
            exception=self.exception)
