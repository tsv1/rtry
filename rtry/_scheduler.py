import signal
import sched
from sched import Event
from time import monotonic, sleep
from typing import Union, Type, Callable, Any
from types import FrameType
from signal import Signals, Handlers


__all__ = ("Scheduler", "Event",)


SignalHandler = Union[Callable[[Signals, FrameType], None], int, Handlers, None]


class Scheduler:
    def __init__(self,
                 timefunc: Callable[..., Any] = monotonic,
                 delayfunc: Callable[..., Any] = sleep,
                 itimer: int = signal.ITIMER_REAL) -> None:
        self._timefunc = timefunc
        self._delayfunc = delayfunc
        self._itimer = itimer
        self._scheduler = sched.scheduler(timefunc, delayfunc)
        self._orig_handler = None  # type: SignalHandler

    def _next_event(self) -> float:
        queue = self._scheduler.queue
        if queue:
            return max(0, float(queue[0].time - self._timefunc()))
        return 0

    def new(self, seconds: Union[int, float], exception: Type[Exception]) -> Event:
        orig_handler = signal.getsignal(signal.SIGALRM)
        if not isinstance(orig_handler, type(self)):
            self._orig_handler = orig_handler

        def handler() -> None:
            raise exception()

        priority = -len(self._scheduler.queue)
        event = self._scheduler.enter(seconds, priority, handler)

        signal.signal(signal.SIGALRM, self)
        signal.setitimer(self._itimer, self._next_event())

        return event

    def cancel(self, event: Union[Event, None]) -> None:
        try:
            self._scheduler.cancel(event)  # type: ignore
        except ValueError:
            pass

        if self._scheduler.empty():
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._orig_handler)
        else:
            signal.setitimer(self._itimer, self._next_event())

    def __call__(self, signum: int, frame: FrameType) -> None:
        self._scheduler.run(blocking=False)