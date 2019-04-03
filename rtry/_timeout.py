import signal
from functools import wraps
from typing import Union, Type, Callable, Optional


class CancelledError(Exception):
    pass


class timeout:
    def __init__(self,
                 seconds: Union[float, int],
                 exception: Optional[Type[BaseException]] = CancelledError) -> None:
        assert exception is None or issubclass(exception, BaseException)
        self._seconds = seconds
        self._exception = exception if exception else CancelledError
        self._silent = exception is None

    def _handler(self, signum, frame):
        raise self._exception()

    def __call__(self, fn: Callable) -> Callable:
        if self._seconds == 0:
            return fn

        @wraps(fn)
        def wrapped(*args, **kwargs):
            # Python signal handlers are always executed in the main Python thread,
            # even if the signal was received in another thread.
            # https://docs.python.org/3/library/signal.html
            prev_handler = signal.signal(signal.SIGALRM, self._handler)
            signal.setitimer(signal.ITIMER_REAL, self._seconds)
            try:
                return fn(*args, **kwargs)
            except self._exception:
                if not self._silent:
                    raise
                pass
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev_handler)
        return wrapped
