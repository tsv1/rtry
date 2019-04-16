import unittest
import signal
from time import sleep
from unittest.mock import MagicMock, sentinel

from rtry import timeout, CancelledError


class TestTimeout(unittest.TestCase):
    def test_wraps(self):
        def fn(): pass
        wrapped = timeout(0.01)(fn)
        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    def test_no_timeout(self):
        def fn(): pass
        timeout(0)(fn)()

    def test_timeout_without_delay(self):
        def fn(): pass
        timeout(0.01)(fn)()

    def test_timeout_with_expected_delay(self):
        def fn(): sleep(0.01)
        timeout(0.02)(fn)()

    def test_timeout_with_unexpected_delay(self):
        def fn(): sleep(0.02)
        with self.assertRaises(CancelledError):
           timeout(0.01)(fn)()

    def test_silent_timeout_with_unexpected_delay(self):
        mock = MagicMock()
        def fn():
            mock(1)
            sleep(0.02)
            mock(2)
        timeout(0.01, exception=None)(fn)()
        mock.assert_called_once_with(1)

    def test_forwards_args_and_result(self):
        mock = MagicMock(return_value=sentinel.res)
        res = timeout(0.01)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        mock.assert_called_once_with(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        self.assertEqual(res, sentinel.res)

    def test_restores_prev_signal_handler_with_expected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)
 
        def fn(): sleep(0.01)
        timeout(0.02)(fn)()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_restores_prev_signal_handler_with_unexpected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)
 
        def fn():
            sleep(0.02)
        with self.assertRaises(CancelledError):
            timeout(0.01)(fn)()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_custom_exception(self):
        class CustomException(CancelledError): pass
        def fn(): sleep(0.02)

        with self.assertRaises(CustomException):
            timeout(0.01, exception=CustomException)(fn)()

