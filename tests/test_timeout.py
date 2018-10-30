import unittest
import signal
from time import sleep
from unittest.mock import MagicMock, sentinel

from rtry import timeout, CancelledError


class TestTimeout(unittest.TestCase):
    def test_wraps(self):
        def fn(): pass
        wrapped = timeout(0.1)(fn)
        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    def test_no_timeout(self):
        def fn(): pass
        original = timeout(0)(fn)
        self.assertEqual(original, fn)
        self.assertFalse(hasattr(original, "__wrapped__"))

    def test_timeout_without_delay(self):
        def fn(): pass
        timeout(0.1)(fn)()

    def test_timeout_with_expected_delay(self):
        def fn(): sleep(0.1)
        timeout(0.2)(fn)()

    def test_timeout_with_unexpected_delay(self):
        def fn(): sleep(0.2)
        with self.assertRaises(CancelledError):
           timeout(0.1)(fn)()

    def test_forwards_args_and_result(self):
        mock = MagicMock(return_value=sentinel.res)
        res = timeout(0.1)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        mock.assert_called_once_with(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        self.assertEqual(res, sentinel.res)

    def test_restores_prev_signal_handler_with_expected_delay(self):
        handler_before = signal.getsignal(signal.SIGALRM)
 
        def fn(): sleep(0.1)
        timeout(0.2)(fn)()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler_before)

    def test_restores_prev_signal_handler_with_unexpected_delay(self):
        handler_before = signal.getsignal(signal.SIGALRM)
 
        def fn(): sleep(0.2)
        with self.assertRaises(CancelledError):
            timeout(0.1)(fn)()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler_before)

    def test_custom_exception(self):
        class CustomException(Exception): pass
        def fn(): sleep(0.2)

        with self.assertRaises(CustomException):
            timeout(0.1, CustomException)(fn)()
