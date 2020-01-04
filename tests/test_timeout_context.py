import signal
import unittest
from time import sleep
from unittest.mock import Mock, call

from rtry import CancelledError, timeout
from rtry.types import TimeoutProxy

from ._ignore_exception import ignore_exception


class TestTimeoutContext(unittest.TestCase):
    def test_no_timeout(self):
        mock = Mock()
        with timeout(0):
            mock(1)
        mock.assert_called_once_with(1)

    def test_timeout_without_delay(self):
        mock = Mock()
        with timeout(0.01):
            mock(1)
        mock.assert_called_once_with(1)

    def test_timeout_with_expected_delay(self):
        mock = Mock()
        with timeout(0.02):
            mock(1)
            sleep(0.01)
            mock(2)
        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_timeout_with_unexpected_delay(self):
        mock = Mock()
        with self.assertRaises(CancelledError):
            with timeout(0.01):
                mock(1)
                sleep(0.02)
                mock(2)
        mock.assert_called_once_with(1)

    def test_timeout_with_ignored_inner_exception(self):
        mock = Mock()
        with self.assertRaises(CancelledError):
            with timeout(0.05):
                with timeout(0.01):
                    with ignore_exception(CancelledError, 0.05):
                        mock(1)
                        sleep(0.02)
                        mock(2)
                    mock(3)
                mock(4)
        mock.assert_called_once_with(1)

    def test_timeout_context(self):
        with timeout(0.01) as smth:
            self.assertIsInstance(smth, TimeoutProxy)

    def test_timeout_proxy_exception_property(self):
        with timeout(0.05) as t:
            self.assertTrue(issubclass(t.exception, CancelledError))

    def test_silent_timeout_proxy_exception_property(self):
        with timeout(0.05, exception=None) as t:
            self.assertIsNone(t.exception)

    def test_timeout_remaining_property(self):
        with timeout(1.0) as t:
            self.assertLess(t.remaining, 1.0)

    def test_timeout_remaining_property_berfore(self):
        seconds = 1.0
        t = timeout(seconds)
        with t:
            self.assertLess(t.remaining, seconds)

    def test_timeout_remaining_property_after(self):
        t = timeout(0.01)
        with t:
            pass
        sleep(0.02)
        self.assertEqual(t.remaining, 0)

    def test_silent_timeout_with_unexpected_delay(self):
        mock = Mock()
        with timeout(0.01, exception=None):
            mock(1)
            sleep(0.02)
            mock(2)
        mock.assert_called_once_with(1)

    def test_nested_silent_timeout_with_exception(self):
        with self.assertRaises(CancelledError):
            with timeout(0.05, exception=None):
                with timeout(0.01):
                    sleep(0.03)

    def test_restores_prev_signal_handler_with_expected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        with timeout(0.02):
            sleep(0.01)

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_restores_prev_signal_handler_with_unexpected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        with self.assertRaises(CancelledError):
            with timeout(0.01):
                sleep(0.02)

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    def test_timeout_custom_exception_with_unexpected_delay(self):
        class CustomException(CancelledError):
            pass

        with self.assertRaises(CustomException):
            with timeout(0.01, exception=CustomException):
                sleep(0.02)

    def test_timeout_custom_exception_with_manual_raise(self):
        class CustomException(CancelledError):
            pass

        with self.assertRaises(CustomException):
            with timeout(0.01, exception=CustomException) as t:
                raise t.exception()

    def test_nested_timeout_inner_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.05):
                mock(1)
                with timeout(0.01):
                    mock(2)
                    sleep(0.03)
                    mock(3)
                mock(4)

        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_nested_timeout_outer_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.01):
                mock(1)
                with timeout(0.05):
                    mock(2)
                    sleep(0.03)
                    mock(3)
                mock(4)

        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_nested_timeout_outer_raises(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.03):
                mock(1)
                with timeout(0.07):
                    mock(2)
                    sleep(0.01)
                    mock(3)
                mock(4)
                sleep(0.04)
                mock(5)

        mock.assert_has_calls([call(1), call(2), call(3), call(4)])
        self.assertEqual(mock.call_count, 4)

    def test_nested_timeout_outer_raises_inner_silent(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.05):
                mock(1)
                with timeout(0.01, exception=None):
                    mock(2)
                    sleep(0.03)
                    mock(3)
                mock(4)
                sleep(0.05)
                mock(5)

        mock.assert_has_calls([call(1), call(2), call(4)])
        self.assertEqual(mock.call_count, 3)

    def test_nested_timeout_raises_with_same_timeout(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.01):
                mock(1)
                with timeout(0.01):
                    mock(2)
                    sleep(0.03)
                    mock(3)
                mock(4)

        mock.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock.call_count, 2)

    def test_multiple_nested_timeout_inner_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.07):
                mock(1)
                with timeout(0.05):
                    mock(2)
                    with timeout(0.01):
                        mock(3)
                        sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        mock.assert_has_calls([call(1), call(2), call(3)])
        self.assertEqual(mock.call_count, 3)

    def test_multiple_nested_silent_timeout_inner_propagation(self):
        mock = Mock()

        with timeout(0.07):
            mock(1)
            with timeout(0.05):
                mock(2)
                with timeout(0.01, exception=None):
                    mock(3)
                    sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        mock.assert_has_calls([call(1), call(2), call(3), call(5), call(6)])
        self.assertEqual(mock.call_count, 5)

    def test_multiple_nested_timeout_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.07):
                mock(1)
                with timeout(0.01):
                    mock(2)
                    with timeout(0.05):
                        mock(3)
                        sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        mock.assert_has_calls([call(1), call(2), call(3)])
        self.assertEqual(mock.call_count, 3)

    def test_multiple_nested_silent_timeout_propagation(self):
        mock = Mock()

        with timeout(0.07):
            mock(1)
            with timeout(0.01, exception=None):
                mock(2)
                with timeout(0.05):
                    mock(3)
                    sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        mock.assert_has_calls([call(1), call(2), call(3), call(6)])
        self.assertEqual(mock.call_count, 4)

    def test_multiple_nested_timeout_outer_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            with timeout(0.01):
                mock(1)
                with timeout(0.07):
                    mock(2)
                    with timeout(0.05):
                        mock(3)
                        sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        mock.assert_has_calls([call(1), call(2), call(3)])
        self.assertEqual(mock.call_count, 3)

    def test_multiple_nested_silent_timeout_outer_propagation(self):
        mock = Mock()

        with timeout(0.01, exception=None):
            mock(1)
            with timeout(0.07):
                mock(2)
                with timeout(0.05):
                    mock(3)
                    sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        mock.assert_has_calls([call(1), call(2), call(3)])
        self.assertEqual(mock.call_count, 3)

    def test_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            with timeout(0.01):
                raise ZeroDivisionError()

    def test_silent_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            with timeout(0.01, exception=None):
                raise ZeroDivisionError()

    def test_nested_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            with timeout(0.02):
                with timeout(0.01):
                    raise ZeroDivisionError()

    def test_timeout_proxy_repr(self):
        with timeout(1.0) as t:
            self.assertTrue(repr(t).startswith("TimeoutProxy(timeout(0.9"))
            self.assertTrue(repr(t).endswith(", exception={}))".format(repr(CancelledError))))

        with timeout(1.0, exception=None) as t:
            self.assertTrue(repr(t).startswith("TimeoutProxy(timeout(0.9"))
            self.assertTrue(repr(t).endswith(", exception=None))"))
