import unittest
import signal
from time import sleep
from unittest.mock import Mock, sentinel, call

from rtry import timeout, CancelledError


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

    def test_timeout_context(self):
        with timeout(0.01) as smth:
            self.assertIsNone(smth)

    def test_silent_timeout_with_unexpected_delay(self):
        mock = Mock()
        with timeout(0.01, exception=None):
            mock(1)
            sleep(0.02)
            mock(2)
        mock.assert_called_once_with(1)

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

    def test_custom_exception(self):
        class CustomException(CancelledError):
            pass

        with self.assertRaises(CustomException):
            with timeout(0.01, exception=CustomException):
                sleep(0.02)
