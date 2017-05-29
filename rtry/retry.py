class retry:
    def __init__(self, until=None, attempts=1, swallow=Exception):
        self._until = until
        self._attempts = attempts
        self._swallow = swallow

    def __call__(self, fn):
        def wrapped(*args, **kwargs):
            retried = 0
            exception = None
            while retried < self._attempts:
                try:
                    result = fn(*args, **kwargs)
                except self._swallow as e:
                    exception = e
                else:
                    if (self._until is not None) and not(self._until(result)):
                        return result
                    exception = None
                retried += 1
            if exception:
                raise exception
            return result
        return wrapped
