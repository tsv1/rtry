import time
from functools import wraps
from typing import Optional, Union, Callable, Tuple, Type, Any

from ._error import CancelledError
from ._timeout import Timeout


__all__ = ("Retry",)


AttemptValue = int
TimeoutValue = Union[float, int]
DelayValue = Union[float, int]
DelayCallable = Callable[[AttemptValue], DelayValue]
ExceptionType = Type[BaseException]
LoggerCallable = Callable[[AttemptValue, Any, Callable], Any]
UntilCallable = Callable[[Any], bool]
SwallowException = Union[Tuple[ExceptionType, ...], ExceptionType]


class Retry:
    def __init__(self, *,
                 until: Optional[UntilCallable] = None,
                 attempts: Optional[AttemptValue] = None,
                 timeout: Optional[TimeoutValue] = None,
                 delay: Optional[Union[DelayValue, DelayCallable]] = None,
                 swallow: Optional[SwallowException] = BaseException,
                 logger: Optional[LoggerCallable] = None,
                 timeout_factory: Optional[Type[Timeout]] = None) -> None:
        assert timeout_factory is not None
        assert (attempts is not None) or (timeout is not None)
        if attempts is not None:
            assert attempts > 0
        if timeout is not None:
            assert timeout >= 0

        self._until = until
        self._attempts = attempts
        self._timeout = timeout
        self._delay = delay
        self._swallow = () if swallow is None else swallow
        if isinstance(self._swallow, list):
            self._swallow = tuple(self._swallow)
        self._logger = logger
        self._timeout_factory = timeout_factory

    def __call__(self, fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(*args, **kwargs):
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
                    self._logger(retried, exception or result, fn)
                if self._delay is not None:
                    delay = self._delay
                    if hasattr(self._delay, "__call__"):
                        delay = self._delay(retried)
                    time.sleep(delay)
            if exception:
                raise exception
            return result
        return wrapped if self._timeout is None else self._timeout_factory(self._timeout)(wrapped)
