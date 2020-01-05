import asyncio
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Union

from ._errors import CancelledError
from ._timeout import Timeout
from ._types import (
    AnyCallable,
    AttemptValue,
    DelayCallable,
    DelayValue,
    LoggerCallable,
    SwallowException,
    TimeoutValue,
    UntilCallable,
)

__all__ = ("Retry",)


class Retry:
    def __init__(self, timeout_factory: Callable[[TimeoutValue], Timeout], *,
                 until: Optional[UntilCallable] = None,
                 attempts: Optional[AttemptValue] = None,
                 timeout: Optional[TimeoutValue] = None,
                 delay: Optional[Union[DelayValue, DelayCallable]] = None,
                 swallow: Optional[SwallowException] = BaseException,
                 logger: Optional[LoggerCallable] = None) -> None:
        assert (attempts is not None) or (timeout is not None)
        if attempts is not None:
            assert attempts > 0
        if timeout is not None:
            assert timeout >= 0

        self._timeout_factory = timeout_factory
        self._until = until
        self._attempts = attempts
        self._timeout = timeout
        self._delay = delay
        self._swallow = () if swallow is None else swallow
        if isinstance(self._swallow, list):
            self._swallow = tuple(self._swallow)
        self._logger = logger
        self._fn = None  # type: Union[AnyCallable, None]

    def _sync_wrapped(self, *args: Any, **kwargs: Any) -> Any:
        assert self._fn is not None

        retried = 0
        exception = None
        while (self._attempts is None) or (retried < self._attempts):
            try:
                result = self._fn(*args, **kwargs)
            except CancelledError:
                raise
            except self._swallow as e:
                exception = e
            else:
                if self._until is None:
                    return result
                elif not(self._until(result)):
                    return result
                exception = None
            retried += 1
            if hasattr(self._logger, "__call__"):
                self._logger(retried, exception or result, self._fn)  # type: ignore
            if self._delay is not None:
                delay = self._delay
                if hasattr(self._delay, "__call__"):
                    delay = self._delay(retried)  # type: ignore
                time.sleep(delay)  # type: ignore
            else:
                time.sleep(0)
        if exception:
            raise exception
        return result

    async def _async_wrapped(self, *args: Any, **kwargs: Any) -> Any:
        assert self._fn is not None

        retried = 0
        exception = None
        while (self._attempts is None) or (retried < self._attempts):
            try:
                result = await self._fn(*args, **kwargs)
            except (CancelledError, asyncio.CancelledError):
                raise
            except self._swallow as e:
                exception = e
            else:
                if self._until is None:
                    return result
                elif not(self._until(result)):
                    return result
                exception = None
            retried += 1
            if hasattr(self._logger, "__call__"):
                self._logger(retried, exception or result, self._fn)  # type: ignore
            if self._delay is not None:
                delay = self._delay
                if hasattr(self._delay, "__call__"):
                    delay = self._delay(retried)  # type: ignore
                await asyncio.sleep(delay)  # type: ignore
            else:
                await asyncio.sleep(0)
        if exception:
            raise exception
        return result

    def __call__(self, fn: AnyCallable) -> AnyCallable:
        self._fn = fn

        if asyncio.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                return await self._async_wrapped(*args, **kwargs)
            wrapped = async_wrapped
        else:
            @wraps(fn)
            def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
                return self._sync_wrapped(*args, **kwargs)
            wrapped = sync_wrapped

        if self._timeout is None:
            return wrapped
        return self._timeout_factory(self._timeout)(wrapped)

    def __repr__(self) -> str:
        args = []  # type: List[str]
        if self._until is not None:
            args += ["until={}".format(repr(self._until))]
        if self._attempts is not None:
            args += ["attempts={}".format(self._attempts)]
        if self._timeout is not None:
            args += ["timeout={}".format(self._timeout)]
        if self._delay is not None:
            args += ["delay={}".format(repr(self._delay))]
        if (self._swallow is not None) and (self._swallow != BaseException):
            args += ["swallow={}".format(self._swallow)]
        if self._logger is not None:
            args += ["logger={}".format(repr(self._logger))]
        return "retry({})".format(", ".join(args))
