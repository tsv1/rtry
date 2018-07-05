from functools import wraps
from time import sleep


class retry:
    def __init__(self, until=None, attempts=1, delay=None, swallow=Exception, logger=None):
        self._until = until
        self._attempts = attempts
        self._delay = delay
        self._swallow = swallow
        self._logger = logger

    def __call__(self, fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            retried = 0
            exception = None
            while retried < self._attempts:
                try:
                    result = fn(*args, **kwargs)
                except self._swallow as e:
                    exception = e
                else:
                    if self._until is None:
                        return result
                    elif not(self._until(result)):
                        return result
                    exception = None
                retried += 1
                if hasattr(self._logger, '__call__'):
                    self._logger('Retried {} time(s): {}'.format(retried, fn))
                if self._delay is not None:
                    sleep(self._delay)
            if exception:
                raise exception
            return result
        return wrapped
