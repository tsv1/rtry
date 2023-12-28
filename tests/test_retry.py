import unittest
from functools import partial
from time import sleep
from unittest.mock import MagicMock, Mock, call, patch, sentinel

from rtry import CancelledError, retry


class TestRetry(unittest.TestCase):
    def test_no_args(self):
        with self.assertRaises(AssertionError):
            retry()

    def test_wraps(self):
        def fn():
            pass

        wrapped = retry(attempts=1)(fn)

        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    def test_forwards_args_and_result(self):
        mock = MagicMock(return_value=sentinel.res)

        res = retry(attempts=1)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)

        mock.assert_called_once_with(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        self.assertEqual(res, sentinel.res)

    # Attempts

    def test_zero_attempts(self):
        with self.assertRaises(AssertionError):
            retry(attempts=0)

    def test_single_attempt(self):
        mock = MagicMock(side_effect=None)
        retry(attempts=1)(mock)()
        self.assertEqual(mock.call_count, 1)

    def test_multiple_attempts_without_errors(self):
        mock = MagicMock(side_effect=None)
        retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 1)

    def test_multiple_attempts_with_error_after_start(self):
        mock = MagicMock(side_effect=(Exception, None, None))
        retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 2)

    def test_multiple_attempts_with_error_before_end(self):
        mock = MagicMock(side_effect=(Exception, Exception, None))
        retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 3)

    def test_multiple_attempts_with_errors(self):
        mock = MagicMock(side_effect=Exception)
        with self.assertRaises(Exception):
            retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 3)

    # Delay

    def test_default_delay(self):
        mock = MagicMock(side_effect=None)
        with patch("time.sleep", return_value=None) as patched:
            retry(attempts=3)(mock)()
            patched.assert_not_called()
        self.assertEqual(mock.call_count, 1)

    def test_no_delay_without_errors(self):
        mock = MagicMock(side_effect=None)
        with patch("time.sleep", return_value=None) as patched:
            retry(attempts=3, delay=1.0)(mock)()
            patched.assert_not_called()
        self.assertEqual(mock.call_count, 1)

    def test_delay_with_error_after_start(self):
        mock = MagicMock(side_effect=(Exception, None, None))
        with patch("time.sleep", return_value=None) as patched:
            delay = 1.0
            retry(attempts=3, delay=delay)(mock)()
            patched.assert_called_once_with(delay)
        self.assertEqual(mock.call_count, 2)

    def test_delay_with_error_before_end(self):
        mock = MagicMock(side_effect=(Exception, Exception, None))

        with patch("time.sleep", return_value=None) as patched:
            delay = 1.0
            retry(attempts=3, delay=delay)(mock)()

            patched.assert_has_calls([call(delay)] * 2)
            self.assertEqual(patched.call_count, 2)

        self.assertEqual(mock.call_count, 3)

    def test_delay_with_errors(self):
        mock = MagicMock(side_effect=Exception)

        with patch("time.sleep", return_value=None) as patched:
            with self.assertRaises(Exception):
                delay = 1.0
                retry(attempts=3, delay=delay)(mock)()

            patched.assert_has_calls([call(delay)] * 3)
            self.assertEqual(patched.call_count, 3)

        self.assertEqual(mock.call_count, 3)

    def test_delay_with_custom_backoff(self):
        mock = MagicMock(side_effect=(Exception, Exception, None))

        with patch("time.sleep", return_value=None) as patched:
            delay = MagicMock(side_effect=(42, 0))
            retry(attempts=3, delay=delay)(mock)()

            delay.assert_has_calls([call(1), call(2)])
            self.assertEqual(delay.call_count, 2)

            patched.assert_has_calls([call(42), call(0)])
            self.assertEqual(patched.call_count, 2)

        self.assertEqual(mock.call_count, 3)

    # Swallow

    def test_swallow_no_exceptions(self):
        mock = MagicMock(side_effect=(Exception, None))
        with self.assertRaises(Exception):
            retry(attempts=2, swallow=None)(mock)()
        self.assertEqual(mock.call_count, 1)

    def test_swallow_builtin_exception(self):
        mock = MagicMock(side_effect=(Exception, None))
        retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 2)

    def test_swallow_custom_exception(self):
        class CustomException(Exception):
            pass

        mock = MagicMock(side_effect=(CustomException, None))
        retry(attempts=3)(mock)()
        self.assertEqual(mock.call_count, 2)

    def test_swallow_single_exception(self):
        mock = MagicMock(side_effect=(KeyError, None))
        retry(attempts=3, swallow=KeyError)(mock)()
        self.assertEqual(mock.call_count, 2)

        mock = MagicMock(side_effect=(KeyError, IndexError, None))
        with self.assertRaises(IndexError):
            retry(attempts=3, swallow=KeyError)(mock)()
        self.assertEqual(mock.call_count, 2)

    def test_swallow_multiple_exceptions(self):
        mock = MagicMock(side_effect=(KeyError, IndexError, None))
        retry(attempts=3, swallow=(KeyError, IndexError))(mock)()
        self.assertEqual(mock.call_count, 3)

        mock = MagicMock(side_effect=(KeyError, IndexError, ZeroDivisionError))
        with self.assertRaises(ZeroDivisionError):
            retry(attempts=3, swallow=(KeyError, IndexError))(mock)()
        self.assertEqual(mock.call_count, 3)

    def test_swallow_list_exceptions(self):
        mock = MagicMock(side_effect=(KeyError, None))
        retry(attempts=3, swallow=[ValueError, KeyError])(mock)()
        self.assertEqual(mock.call_count, 2)

    # Until

    def test_until_without_errors(self):
        until = MagicMock(side_effect=(False,))

        mock = MagicMock(return_value=sentinel.res)
        res = retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.res)
        self.assertEqual(mock.call_count, 1)

        until.assert_called_once_with(sentinel.res)

    def test_until_with_error_after_start(self):
        until = MagicMock(side_effect=(True, False))

        mock = MagicMock(side_effect=(sentinel.a, sentinel.b))
        res = retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.b)
        self.assertEqual(mock.call_count, 2)

        until.assert_has_calls([
            call(sentinel.a),
            call(sentinel.b),
        ])
        self.assertEqual(until.call_count, 2)

    def test_until_with_error_before_end(self):
        until = MagicMock(side_effect=(True, True, False))

        mock = MagicMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))
        res = retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.c)
        self.assertEqual(mock.call_count, 3)

        until.assert_has_calls([
            call(sentinel.a),
            call(sentinel.b),
            call(sentinel.c)
        ])
        self.assertEqual(until.call_count, 3)

    def test_until_with_errors(self):
        until = MagicMock(side_effect=(True, True, True))

        mock = MagicMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))
        retry(until=until, attempts=3)(mock)()
        self.assertEqual(mock.call_count, 3)

        until.assert_has_calls([
            call(sentinel.a),
            call(sentinel.b),
            call(sentinel.c)
        ])
        self.assertEqual(until.call_count, 3)

    # Logger

    def test_custom_logger_without_errors(self):
        logger = Mock()

        mock = MagicMock()
        retry(attempts=3, logger=logger)(mock)()

        logger.assert_not_called()

    def test_logger_with_error_after_start(self):
        logger = Mock()

        exception = Exception()
        mock = MagicMock(side_effect=(exception, None))
        retry(attempts=3, logger=logger)(mock)()

        logger.assert_called_once_with(1, exception, mock)

    def test_logger_with_error_before_end(self):
        logger = Mock()

        exception1, exception2 = Exception(), Exception()
        mock = MagicMock(side_effect=(exception1, exception2, None))
        retry(attempts=3, logger=logger)(mock)()

        logger.assert_has_calls([
            call(1, exception1, mock),
            call(2, exception2, mock)
        ])
        self.assertEqual(logger.call_count, 2)

    def test_logger_with_errors(self):
        logger = Mock()

        exception = Exception()
        mock = MagicMock(side_effect=exception)
        with self.assertRaises(type(exception)):
            retry(attempts=3, logger=logger)(mock)()

        logger.assert_has_calls([
            call(1, exception, mock),
            call(2, exception, mock),
            call(3, exception, mock)
        ])
        self.assertEqual(logger.call_count, 3)

    # Logger with Until

    def test_logger_with_until_true_after_start(self):
        logger = Mock()
        until = MagicMock(side_effect=(True, False, False))
        mock = MagicMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.call_count, 2)
        self.assertEqual(res, sentinel.b)

        logger.assert_called_once_with(1, sentinel.a, mock)

    def test_logger_with_until_true_before_end(self):
        logger = Mock()
        until = MagicMock(side_effect=(True, True, False))
        mock = MagicMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.call_count, 3)
        self.assertEqual(res, sentinel.c)

        logger.assert_has_calls([
            call(1, sentinel.a, mock),
            call(2, sentinel.b, mock)
        ])
        self.assertEqual(logger.call_count, 2)

    def test_logger_with_until_true(self):
        logger = Mock()
        until = MagicMock(side_effect=(True, True, True))
        mock = MagicMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.call_count, 3)
        self.assertEqual(res, sentinel.c)

        logger.assert_has_calls([
            call(1, sentinel.a, mock),
            call(2, sentinel.b, mock),
            call(3, sentinel.c, mock)
        ])
        self.assertEqual(logger.call_count, 3)

    # Timeout

    def test_negative_timeout(self):
        with self.assertRaises(AssertionError):
            retry(timeout=-1)

    def test_timeout_without_delay(self):
        mock = MagicMock()
        retry(timeout=0.01)(mock)()
        self.assertEqual(mock.call_count, 1)

    def test_timeout_with_expected_delay(self):
        mock = MagicMock(side_effect=partial(sleep, 0.01))

        retry(timeout=0.03)(mock)()

        self.assertEqual(mock.call_count, 1)

    def test_timeout_with_unexpected_delay(self):
        mock = MagicMock(side_effect=partial(sleep, 0.03))

        with self.assertRaises(CancelledError):
            retry(timeout=0.01)(mock)()

        self.assertEqual(mock.call_count, 1)

    def test_timeout_with_errors(self):
        mock = MagicMock(side_effect=Exception)

        with self.assertRaises(CancelledError):
            retry(timeout=0.01)(mock)()

        self.assertGreater(mock.call_count, 1)

    def test_timeout_with_error_after_start(self):
        mock = MagicMock(side_effect=(Exception, sentinel.res, sentinel.res, sentinel.res))

        res = retry(timeout=0.01)(mock)()

        self.assertEqual(mock.call_count, 2)
        self.assertEqual(res, sentinel.res)

    def test_timeout_with_error_before_end(self):
        mock = MagicMock(side_effect=(Exception, Exception, sentinel.res, sentinel.res))

        res = retry(timeout=0.01)(mock)()

        self.assertEqual(mock.call_count, 3)
        self.assertEqual(res, sentinel.res)

    def test_do_not_swallow_timeout_error(self):
        mock = MagicMock(side_effect=Exception)
        with self.assertRaises(CancelledError):
            retry(timeout=0.01, swallow=(Exception, CancelledError))(mock)()
        self.assertGreater(mock.call_count, 1)

    # Timeout with Attempts

    def test_timeout_with_exceeded_attempts(self):
        mock = MagicMock(side_effect=ZeroDivisionError)

        with self.assertRaises(ZeroDivisionError):
            retry(attempts=3, timeout=1.0)(mock)()

        self.assertEqual(mock.call_count, 3)

    def test_attempts_with_exceeded_timeout(self):
        def side_effect():
            sleep(0.01)
            raise ZeroDivisionError()
        mock = MagicMock(side_effect=side_effect)

        with self.assertRaises(CancelledError):
            retry(attempts=99, timeout=0.03)(mock)()

        self.assertLess(mock.call_count, 99)

    # Repr

    def test_repr_with_attempts(self):
        self.assertEqual(
            repr(retry(attempts=3)),
            "retry(attempts=3)")

    def test_repr_with_until(self):
        self.assertEqual(
            repr(retry(until=bool, attempts=3)),
            "retry(until={}, attempts=3)".format(repr(bool)))

    def test_repr_with_timeout(self):
        self.assertEqual(
            repr(retry(timeout=1.0)),
            "retry(timeout=1.0)")

    def test_repr_with_delay(self):
        self.assertEqual(
            repr(retry(attempts=3, delay=0.1)),
            "retry(attempts=3, delay=0.1)")

    def test_repr_with_delay_func(self):
        from math import exp
        self.assertEqual(
            repr(retry(attempts=3, delay=exp)),
            "retry(attempts=3, delay={})".format(repr(exp)))

    def test_repr_with_no_swallow(self):
        self.assertEqual(
            repr(retry(attempts=3, swallow=None)),
            "retry(attempts=3, swallow=())")

    def test_repr_with_custom_swallow(self):
        exception = ValueError
        self.assertEqual(
            repr(retry(attempts=3, swallow=exception)),
            "retry(attempts=3, swallow={})".format(repr(exception)))

    def test_repr_with_custom_swallows(self):
        exceptions = (ValueError, IndexError)
        self.assertEqual(
            repr(retry(attempts=3, swallow=exceptions)),
            "retry(attempts=3, swallow={})".format(repr(exceptions)))

    def test_repr_with_logger(self):
        self.assertEqual(
            repr(retry(attempts=3, logger=print)),
            "retry(attempts=3, logger={})".format(repr(print)))
