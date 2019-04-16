import unittest
import signal
from time import sleep
from unittest.mock import MagicMock, sentinel, call

from rtry import timeout, CancelledError


class TestTimeout(unittest.TestCase):
    def test_wraps(self):
        def fn(): pass
        wrapped = timeout(0.01)(fn)
        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    def test_no_timeout(self):
        def fn():
            pass
        timeout(0)(fn)()

    def test_timeout_without_delay(self):
        def fn():
            pass
        timeout(0.01)(fn)()

    def test_timeout_with_expected_delay(self):
        def fn():
            sleep(0.01)
        timeout(0.02)(fn)()

    def test_timeout_with_unexpected_delay(self):
        def fn():
            sleep(0.02)
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
 
        def fn():
            sleep(0.01)
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

    def test_nested_timeout_result(self):
        @timeout(0.01)
        def outer():
            @timeout(0.01)
            def inner():
                return sentinel.res
            return inner()

        self.assertEqual(outer(), sentinel.res)

    def test_nested_timeout_inner_propagation(self):
        mock = MagicMock()

        @timeout(0.05)
        def outer():
            mock(1)
            @timeout(0.01)
            def inner():
                mock(2)
                sleep(0.03)
                mock(3)
            inner()
            mock(4)

        with self.assertRaises(CancelledError):
            outer()
        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_nested_timeout_outer_propagation(self):
        mock = MagicMock()

        @timeout(0.01)
        def outer():
            mock(1)
            @timeout(0.05)
            def inner():
                mock(2)
                sleep(0.03)
                mock(3)
            inner()
            mock(4)

        with self.assertRaises(CancelledError):
            outer()
        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_nested_timeout_outer_raises(self):
        mock = MagicMock()

        @timeout(0.03)
        def outer():
            mock(1)
            @timeout(0.07)
            def inner():
                mock(2)
                sleep(0.01)
                mock(3)
            inner()
            mock(4)
            sleep(0.04)
            mock(5)

        with self.assertRaises(CancelledError):
            outer()
        mock.assert_has_calls([call(1), call(2), call(3), call(4)])
        self.assertEqual(mock.call_count, 4)

    def test_nested_timeout_outer_raises_inner_silent(self):
        mock = MagicMock()

        @timeout(0.05)
        def outer():
            mock(1)
            @timeout(0.01, exception=None)
            def inner():
                mock(2)
                sleep(0.03)
                mock(3)
            inner()
            mock(4)
            sleep(0.05)
            mock(5)

        with self.assertRaises(CancelledError):
            outer()
        mock.assert_has_calls([call(1), call(2), call(4)])
        self.assertEqual(mock.call_count, 3)

    def test_nested_timeout_raises_with_same_timeout(self):
        mock = MagicMock()

        @timeout(0.01)
        def outer():
            mock(1)
            @timeout(0.01)
            def inner():
                mock(2)
                sleep(0.03)
                mock(3)
            inner()
            mock(4)

        with self.assertRaises(CancelledError):
            outer()
        mock.assert_has_calls([call(1), call(2)])
