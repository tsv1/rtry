import signal
import unittest
from time import sleep
from unittest.mock import Mock, call, sentinel

from rtry import CancelledError, timeout


class TestTimeout(unittest.TestCase):
    def test_wraps(self):
        def fn():
            pass
        wrapped = timeout(0.01)(fn)
        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    def test_no_timeout(self):
        @timeout(0)
        def fn():
            pass
        fn()

    def test_timeout_without_delay(self):
        @timeout(0.01)
        def fn():
            pass
        fn()

    def test_timeout_with_expected_delay(self):
        @timeout(0.02)
        def fn():
            sleep(0.01)
        fn()

    def test_timeout_with_unexpected_delay(self):
        @timeout(0.01)
        def fn():
            sleep(0.02)
        with self.assertRaises(CancelledError):
            fn()

    def test_silent_timeout_with_unexpected_delay(self):
        mock = Mock()

        @timeout(0.01, exception=None)
        def fn():
            mock(1)
            sleep(0.02)
            mock(2)
        fn()
        mock.assert_called_once_with(1)

    def test_nested_silent_timeout_with_exception(self):
        @timeout(0.05, exception=None)
        def outer():
            @timeout(0.01)
            def inner():
                sleep(0.03)
            inner()
        with self.assertRaises(CancelledError):
            outer()

    def test_forwards_args_and_result(self):
        mock = Mock(return_value=sentinel.res)
        res = timeout(0.01)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        mock.assert_called_once_with(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        self.assertEqual(res, sentinel.res)

    def test_timeout_seconds_property(self):
        seconds = 0.05
        self.assertEqual(timeout(seconds).seconds, seconds)

    def test_timeout_exception_property(self):
        exception = timeout(0.05).exception
        self.assertEqual(exception, CancelledError)

    def test_timeout_exception_property_custom(self):
        class CustomException(CancelledError):
            pass
        exception = timeout(0.05, exception=CustomException).exception
        self.assertEqual(exception, CustomException)

    def test_silent_timeout_exception_property(self):
        exception = timeout(0.05, exception=None).exception
        self.assertIsNone(exception)

    def test_restores_prev_signal_handler_with_expected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        @timeout(0.02)
        def fn():
            sleep(0.01)
        fn()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_restores_prev_signal_handler_with_unexpected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        @timeout(0.01)
        def fn():
            sleep(0.02)
        with self.assertRaises(CancelledError):
            fn()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_custom_exception(self):
        class CustomException(CancelledError):
            pass

        @timeout(0.01, exception=CustomException)
        def fn():
            sleep(0.02)

        with self.assertRaises(CustomException):
            fn()

    def test_nested_timeout_result(self):
        @timeout(0.01)
        def outer():
            @timeout(0.01)
            def inner():
                return sentinel.res
            return inner()

        self.assertEqual(outer(), sentinel.res)

    def test_nested_timeout_inner_propagation(self):
        mock = Mock()

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
        mock = Mock()

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
        mock = Mock()

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
        mock = Mock()

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
        mock = Mock()

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
        self.assertEqual(mock.call_count, 2)

    def test_multiple_calls_with_expected_delay(self):
        @timeout(0.01)
        def fn():
            pass
        fn()
        sleep(0.01)
        fn()

    def test_multiple_calls_with_unexpected_delay(self):
        @timeout(0.01)
        def fn():
            sleep(0.02)
        with self.assertRaises(CancelledError):
            fn()
        with self.assertRaises(CancelledError):
            fn()

    def test_timeout_with_exception(self):
        @timeout(0.01)
        def fn():
            raise ZeroDivisionError()
        with self.assertRaises(ZeroDivisionError):
            fn()

    def test_silent_timeout_with_exception(self):
        @timeout(0.01, exception=None)
        def fn():
            raise ZeroDivisionError()
        with self.assertRaises(ZeroDivisionError):
            fn()

    def test_timeout_remaining_property(self):
        seconds = 1.0
        self.assertEqual(timeout(seconds).remaining, seconds)

    def test_nested_timeout_with_exception(self):
        @timeout(0.02)
        def outer():
            @timeout(0.01)
            def inner():
                raise ZeroDivisionError()
            inner()
        with self.assertRaises(ZeroDivisionError):
            outer()

    def test_timeout_repr_with_default_exception(self):
        self.assertEqual(
            repr(timeout(1.0)),
            "timeout(1.0, exception={})".format(repr(CancelledError)))

    def test_silent_timeout_repr(self):
        self.assertEqual(
            repr(timeout(1.0, exception=None)),
            "timeout(1.0, exception=None)")

    def test_timeout_repr_with_custom_exception(self):
        class CustomException(CancelledError):
            pass
        self.assertEqual(
            repr(timeout(1.0, exception=CustomException)),
            "timeout(1.0, exception={})".format(repr(CustomException)))
