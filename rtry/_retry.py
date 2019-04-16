import time
from functools import wraps
from typing import Optional, Union, Callable, Any

from ._errors import CancelledError
from ._timeout import Timeout
from ._types import (AttemptValue, TimeoutValue, DelayValue, DelayCallable,
                     LoggerCallable, UntilCallable, SwallowException,
                     AnyCallable)


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

    def __call__(self, fn: AnyCallable) -> AnyCallable:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            retried = 0
            exception = None
            while (self._attempts is None) or (retried < self._attempts):
                try:
                    result = fn(*args, **kwargs)
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
                    self._logger(retried, exception or result, fn)  # type: ignore
                if self._delay is not None:
                    delay = self._delay
                    if hasattr(self._delay, "__call__"):
                        delay = self._delay(retried)  # type: ignore
                    time.sleep(delay)  # type: ignore
            if exception:
                raise exception
            return result
        return wrapped if self._timeout is None else self._timeout_factory(self._timeout)(wrapped)
