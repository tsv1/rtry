import asyncio
import sys
from functools import partial
from unittest.mock import Mock, call, sentinel

if sys.version_info >= (3, 8):
    from unittest import IsolatedAsyncioTestCase as TestCase
    from unittest.mock import AsyncMock, patch
else:
    from asynctest import TestCase
    from asynctest.mock import patch
    from asynctest.mock import CoroutineMock as AsyncMock

from rtry import CancelledError, retry


class TestAsyncRetry(TestCase):
    async def test_wraps(self):
        async def fn():
            pass

        wrapped = retry(attempts=1)(fn)

        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    async def test_forwards_args_and_result(self):
        mock = AsyncMock(return_value=sentinel.res)

        res = await retry(attempts=1)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)

        self.assertEqual(mock.await_args_list, [
            call(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        ])
        self.assertEqual(res, sentinel.res)

    # Attempts

    async def test_single_attempt(self):
        mock = AsyncMock(side_effect=None)
        await retry(attempts=1)(mock)()
        self.assertEqual(mock.await_args_list, [call()])

    async def test_multiple_attempts_without_errors(self):
        mock = AsyncMock(side_effect=None)
        await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()])

    async def test_multiple_attempts_with_error_after_start(self):
        mock = AsyncMock(side_effect=(Exception, None, None))
        await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

    async def test_multiple_attempts_with_error_before_end(self):
        mock = AsyncMock(side_effect=(Exception, Exception, None))
        await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)

    async def test_multiple_attempts_with_errors(self):
        mock = AsyncMock(side_effect=Exception)
        with self.assertRaises(Exception):
            await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)

    # Delay

    async def test_default_delay(self):
        mock = AsyncMock(side_effect=None)
        with patch("asyncio.sleep", return_value=None) as patched:
            await retry(attempts=3)(mock)()
            self.assertEqual(patched.await_args_list, [])
        self.assertEqual(mock.await_args_list, [call()])

    async def test_no_delay_without_errors(self):
        mock = AsyncMock(side_effect=None)
        with patch("asyncio.sleep", return_value=None) as patched:
            await retry(attempts=3, delay=1.0)(mock)()
            self.assertEqual(patched.await_args_list, [])
        self.assertEqual(mock.await_args_list, [call()])

    async def test_delay_with_error_after_start(self):
        mock = AsyncMock(side_effect=(Exception, None, None))
        with patch("asyncio.sleep", return_value=None) as patched:
            delay = 1.0
            await retry(attempts=3, delay=delay)(mock)()
            self.assertEqual(patched.await_args_list, [call(delay)])
        self.assertEqual(mock.await_args_list, [call()] * 2)

    async def test_delay_with_error_before_end(self):
        mock = AsyncMock(side_effect=(Exception, Exception, None))

        with patch("asyncio.sleep", return_value=None) as patched:
            delay = 1.0
            await retry(attempts=3, delay=delay)(mock)()
            self.assertEqual(patched.await_args_list, [call(delay)] * 2)

        self.assertEqual(mock.await_args_list, [call()] * 3)

    async def test_delay_with_errors(self):
        mock = AsyncMock(side_effect=Exception)

        with patch("asyncio.sleep", return_value=None) as patched:
            with self.assertRaises(Exception):
                delay = 1.0
                await retry(attempts=3, delay=delay)(mock)()
            self.assertEqual(patched.await_args_list, [call(delay)] * 3)

        self.assertEqual(mock.await_args_list, [call()] * 3)

    async def test_delay_with_custom_backoff(self):
        mock = AsyncMock(side_effect=(Exception, Exception, None))

        with patch("asyncio.sleep", return_value=None) as patched:
            delay = Mock(side_effect=(42, 0))  # Coro
            await retry(attempts=3, delay=delay)(mock)()

            self.assertEqual(delay.mock_calls, [call(1), call(2)])
            self.assertEqual(patched.await_args_list, [call(42), call(0)])

        self.assertEqual(mock.await_args_list, [call()] * 3)

    # Swallow

    async def test_swallow_no_exceptions(self):
        mock = AsyncMock(side_effect=(Exception, None))
        with self.assertRaises(Exception):
            await retry(attempts=2, swallow=None)(mock)()
        self.assertEqual(mock.await_args_list, [call()])

    async def test_swallow_builtin_exception(self):
        mock = AsyncMock(side_effect=(Exception, None))
        await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

    async def test_swallow_custom_exception(self):
        class CustomException(Exception):
            pass

        mock = AsyncMock(side_effect=(CustomException, None))
        await retry(attempts=3)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

    async def test_swallow_single_exception(self):
        mock = AsyncMock(side_effect=(KeyError, None))
        await retry(attempts=3, swallow=KeyError)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

        mock = AsyncMock(side_effect=(KeyError, IndexError, None))
        with self.assertRaises(IndexError):
            await retry(attempts=3, swallow=KeyError)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

    async def test_swallow_multiple_exceptions(self):
        mock = AsyncMock(side_effect=(KeyError, IndexError, None))
        await retry(attempts=3, swallow=(KeyError, IndexError))(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)

        mock = AsyncMock(side_effect=(KeyError, IndexError, ZeroDivisionError))
        with self.assertRaises(ZeroDivisionError):
            await retry(attempts=3, swallow=(KeyError, IndexError))(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)

    async def test_swallow_list_exceptions(self):
        mock = AsyncMock(side_effect=(KeyError, None))
        await retry(attempts=3, swallow=[ValueError, KeyError])(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)

    # Until

    async def test_until_without_errors(self):
        until = Mock(side_effect=(False,))

        mock = AsyncMock(return_value=sentinel.res)
        res = await retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.res)
        self.assertEqual(mock.await_args_list, [call()])

        self.assertEqual(until.mock_calls, [
            call(sentinel.res)
        ])

    async def test_until_with_error_after_start(self):
        until = Mock(side_effect=(True, False))

        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b))
        res = await retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.b)
        self.assertEqual(mock.await_args_list, [call()] * 2)

        self.assertEqual(until.mock_calls, [
            call(sentinel.a),
            call(sentinel.b)
        ])

    async def test_until_with_error_before_end(self):
        until = Mock(side_effect=(True, True, False))

        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))
        res = await retry(until=until, attempts=3)(mock)()

        self.assertEqual(res, sentinel.c)
        self.assertEqual(mock.await_args_list, [call()] * 3)

        self.assertEqual(until.mock_calls, [
            call(sentinel.a),
            call(sentinel.b),
            call(sentinel.c)
        ])

    async def test_until_with_errors(self):
        until = Mock(side_effect=(True, True, True))

        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))
        await retry(until=until, attempts=3)(mock)()

        self.assertEqual(mock.await_args_list, [call()] * 3)

        self.assertEqual(until.mock_calls, [
            call(sentinel.a),
            call(sentinel.b),
            call(sentinel.c)
        ])

    # Logger

    async def test_custom_logger_without_errors(self):
        logger = Mock()

        mock = AsyncMock()
        await retry(attempts=3, logger=logger)(mock)()

        self.assertEqual(logger.mock_calls, [])

    async def test_logger_with_error_after_start(self):
        logger = Mock()

        exception = Exception()
        mock = AsyncMock(side_effect=(exception, None))
        await retry(attempts=3, logger=logger)(mock)()

        self.assertEqual(logger.mock_calls, [
            call(1, exception, mock)
        ])

    async def test_logger_with_error_before_end(self):
        logger = Mock()

        exception1, exception2 = Exception(), Exception()
        mock = AsyncMock(side_effect=(exception1, exception2, None))
        await retry(attempts=3, logger=logger)(mock)()

        self.assertEqual(logger.mock_calls, [
            call(1, exception1, mock),
            call(2, exception2, mock)
        ])

    async def test_logger_with_errors(self):
        logger = Mock()

        exception = Exception()
        mock = AsyncMock(side_effect=exception)
        with self.assertRaises(type(exception)):
            await retry(attempts=3, logger=logger)(mock)()

        self.assertEqual(logger.mock_calls, [
            call(1, exception, mock),
            call(2, exception, mock),
            call(3, exception, mock)
        ])

    # Logger with Until

    async def test_logger_with_until_true_after_start(self):
        logger = Mock()
        until = Mock(side_effect=(True, False, False))
        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = await retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 2)
        self.assertEqual(res, sentinel.b)

        self.assertEqual(logger.mock_calls, [
            call(1, sentinel.a, mock),
        ])

    async def test_logger_with_until_true_before_end(self):
        logger = Mock()
        until = Mock(side_effect=(True, True, False))
        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = await retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)
        self.assertEqual(res, sentinel.c)

        self.assertEqual(logger.mock_calls, [
            call(1, sentinel.a, mock),
            call(2, sentinel.b, mock)
        ])

    async def test_logger_with_until_true(self):
        logger = Mock()
        until = Mock(side_effect=(True, True, True))
        mock = AsyncMock(side_effect=(sentinel.a, sentinel.b, sentinel.c))

        res = await retry(until=until, attempts=3, logger=logger)(mock)()
        self.assertEqual(mock.await_args_list, [call()] * 3)
        self.assertEqual(res, sentinel.c)

        self.assertEqual(logger.mock_calls, [
            call(1, sentinel.a, mock),
            call(2, sentinel.b, mock),
            call(3, sentinel.c, mock)
        ])

    # Timeout

    async def test_timeout_without_delay(self):
        mock = AsyncMock()
        await retry(timeout=0.01)(mock)()
        self.assertEqual(mock.await_args_list, [call()])

    async def test_timeout_with_expected_delay(self):
        mock = AsyncMock(side_effect=partial(asyncio.sleep, 0.01))

        await retry(timeout=0.03)(mock)()

        self.assertEqual(mock.await_args_list, [call()])

    async def test_timeout_with_unexpected_delay(self):
        mock = AsyncMock(side_effect=partial(asyncio.sleep, 0.03))

        with self.assertRaises(CancelledError):
            await retry(timeout=0.01)(mock)()

        self.assertEqual(mock.await_args_list, [call()])

    async def test_timeout_with_errors(self):
        mock = AsyncMock(side_effect=Exception)

        with self.assertRaises(CancelledError):
            await retry(timeout=0.01, swallow=Exception)(mock)()

        self.assertGreater(mock.call_count, 1)

    async def test_timeout_with_error_after_start(self):
        mock = AsyncMock(side_effect=(Exception, sentinel.res, sentinel.res, sentinel.res))

        res = await retry(timeout=0.01)(mock)()

        self.assertEqual(mock.await_args_list, [call()] * 2)
        self.assertEqual(res, sentinel.res)

    async def test_timeout_with_error_before_end(self):
        mock = AsyncMock(side_effect=(Exception, Exception, sentinel.res, sentinel.res))

        res = await retry(timeout=0.01)(mock)()

        self.assertEqual(mock.await_args_list, [call()] * 3)
        self.assertEqual(res, sentinel.res)

    async def test_do_not_swallow_timeout_error(self):
        mock = AsyncMock(side_effect=Exception)
        with self.assertRaises(CancelledError):
            await retry(timeout=0.01, swallow=(Exception, CancelledError))(mock)()
        self.assertGreater(mock.call_count, 1)

    # Timeout with Attempts

    async def test_timeout_with_exceeded_attempts(self):
        mock = AsyncMock(side_effect=ZeroDivisionError)

        with self.assertRaises(ZeroDivisionError):
            await retry(attempts=3, timeout=1.0)(mock)()

        self.assertEqual(mock.await_args_list, [call()] * 3)

    async def test_attempts_with_exceeded_timeout(self):
        async def side_effect():
            await asyncio.sleep(0.01)
            raise ZeroDivisionError()
        mock = AsyncMock(side_effect=side_effect)

        with self.assertRaises(CancelledError):
            await retry(attempts=99, timeout=0.03)(mock)()

        self.assertLess(mock.call_count, 99)
