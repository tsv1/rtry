import signal
import sched
from types import FrameType


__all__ = ("Scheduler",)


class Scheduler:
    def __init__(self):
        self._scheduler = sched.scheduler()
        self._orig_handler = None
        self._interval_timer = signal.ITIMER_REAL

    def new(self, seconds, exception):
        orig_handler = signal.getsignal(signal.SIGALRM)
        if not isinstance(orig_handler, type(self)):
            self._orig_handler = orig_handler

        def handler():
            raise exception()

        priority = -len(self._scheduler.queue)
        event = self._scheduler.enter(seconds, priority, handler)

        signal.signal(signal.SIGALRM, self)
        signal.setitimer(self._interval_timer, self._scheduler.run(blocking=False))

        return event

    def cancel(self, event) -> None:
        try:
            self._scheduler.cancel(event)
        except ValueError:
            pass

        signal.setitimer(self._interval_timer, self._scheduler.run(blocking=False) or 0)

        if self._scheduler.empty():
            signal.signal(signal.SIGALRM, self._orig_handler)

    def __call__(self, signum: int, frame: FrameType) -> None:
        self._scheduler.run(blocking=False)
