from typing import Union, Type, Callable, Any, Tuple
from types import FrameType
from signal import Signals, Handlers


__all__ = ("AttemptValue", "TimeoutValue", "DelayValue", "DelayCallable",
           "AnyCallable", "ExceptionType", "LoggerCallable", "UntilCallable",
           "SwallowException", "SignalHandler",)


AttemptValue = int
TimeoutValue = Union[float, int]
DelayValue = Union[float, int]
DelayCallable = Callable[[AttemptValue], DelayValue]
AnyCallable = Callable[..., Any]
ExceptionType = Type[BaseException]
LoggerCallable = Callable[[AttemptValue, Any, AnyCallable], Any]
UntilCallable = Callable[[Any], bool]
SwallowException = Union[Tuple[ExceptionType, ...], ExceptionType]
SignalHandler = Union[Callable[[Signals, FrameType], None], int, Handlers, None]
