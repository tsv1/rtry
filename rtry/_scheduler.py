import asyncio
import sched
import signal
from sched import Event
from time import monotonic, sleep
from types import FrameType
from typing import Any, Callable, Union

from ._types import DelayValue, SignalHandler, TimeoutValue

__all__ = ("AbstractScheduler", "Scheduler", "AsyncScheduler",
           "Event", "AsyncEvent",)


class AbstractScheduler:
    def get_remaining(self, event: Event) -> TimeoutValue:
        raise NotImplementedError()  # pragma: no cover

    def new(self, seconds: TimeoutValue, handler: Callable[[], None]) -> Event:
        raise NotImplementedError()  # pragma: no cover

    def cancel(self, event: Union[Event, None]) -> None:
        raise NotImplementedError()  # pragma: no cover


class Scheduler(AbstractScheduler):
    def __init__(self,
                 timefunc: Callable[[], TimeoutValue] = monotonic,
                 delayfunc: Callable[[DelayValue], Any] = sleep,
                 itimer: int = signal.ITIMER_REAL) -> None:
        self._timefunc = timefunc
        self._delayfunc = delayfunc
        self._itimer = itimer
        self._scheduler = sched.scheduler(timefunc, delayfunc)
        self._orig_handler = None  # type: Union[SignalHandler, None]

    def get_remaining(self, event: Event) -> TimeoutValue:
        return max(0, event.time - self._timefunc())

    def _next_event(self) -> TimeoutValue:
        return self.get_remaining(self._scheduler.queue[0]) if self._scheduler.queue else 0

    def new(self, seconds: TimeoutValue, handler: Callable[[], None]) -> Event:
        orig_handler = signal.getsignal(signal.SIGALRM)
        if not isinstance(orig_handler, type(self)):
            self._orig_handler = orig_handler

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
            if self._orig_handler:
                signal.signal(signal.SIGALRM, self._orig_handler)
                self._orig_handler = None
        else:
            signal.setitimer(self._itimer, self._next_event())

    def __call__(self, signum: int, frame: FrameType) -> None:
        self._scheduler.run(blocking=False)


class AsyncEvent(Event):
    pass


class AsyncScheduler(AbstractScheduler):
    @property
    def _loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    def get_remaining(self, event: Event) -> TimeoutValue:
        return max(0, event.time - self._loop.time())

    def new(self, seconds: TimeoutValue, handler: Callable[[], None]) -> AsyncEvent:
        when = self._loop.time() + seconds
        action = self._loop.call_at(when, handler)
        return AsyncEvent(time=when, priority=0, action=action.cancel, argument=(), kwargs={})

    def cancel(self, event: Union[Event, None]) -> None:
        if event is not None:
            event.action()
