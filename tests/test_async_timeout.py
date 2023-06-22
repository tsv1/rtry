import asyncio
import signal
import sys
from asyncio import sleep
from unittest.mock import Mock, call, sentinel

if sys.version_info >= (3, 8):
    from unittest import IsolatedAsyncioTestCase as TestCase
    from unittest.mock import AsyncMock
else:
    from asynctest import TestCase
    from asynctest.mock import CoroutineMock as AsyncMock

from rtry import CancelledError, timeout


class TestAsyncTimeout(TestCase):
    async def test_wraps(self):
        async def fn():
            pass
        wrapped = timeout(0.01)(fn)
        self.assertEqual(wrapped.__name__, fn.__name__)
        self.assertEqual(wrapped.__wrapped__, fn)

    async def test_no_timeout(self):
        @timeout(0)
        async def fn():
            pass
        await fn()

    async def test_timeout_without_delay(self):
        @timeout(0.01)
        async def fn():
            pass
        await fn()

    async def test_timeout_with_expected_delay(self):
        @timeout(0.02)
        async def fn():
            await sleep(0.01)
        await fn()

    async def test_timeout_with_unexpected_delay(self):
        @timeout(0.01)
        async def fn():
            await sleep(0.02)
        with self.assertRaises(CancelledError):
            await fn()

    async def test_silent_timeout_with_unexpected_delay(self):
        mock = Mock()

        @timeout(0.01, exception=None)
        async def fn():
            mock(1)
            await sleep(0.02)
            mock(2)
        await fn()
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_nested_silent_timeout_with_exception(self):
        @timeout(0.05, exception=None)
        async def outer():
            @timeout(0.01)
            async def inner():
                await sleep(0.03)
            await inner()
        with self.assertRaises(CancelledError):
            await outer()

    async def test_forwards_args_and_result(self):
        mock = AsyncMock(return_value=sentinel.res)
        res = await timeout(0.01)(mock)(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        self.assertEqual(mock.await_args_list, [
            call(sentinel.a, sentinel.b, key1=sentinel.val, key2=None)
        ])
        self.assertEqual(res, sentinel.res)

    async def test_restores_prev_signal_handler_with_expected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        @timeout(0.02)
        async def fn():
            await sleep(0.01)
        await fn()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    async def test_restores_prev_signal_handler_with_unexpected_delay(self):
        async def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        @timeout(0.01)
        async def fn():
            await sleep(0.02)
        with self.assertRaises(CancelledError):
            await fn()

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    async def test_custom_exception(self):
        class CustomException(CancelledError):
            pass

        @timeout(0.01, exception=CustomException)
        async def fn():
            await sleep(0.02)

        with self.assertRaises(CustomException):
            await fn()

    async def test_nested_timeout_result(self):
        @timeout(0.01)
        async def outer():
            @timeout(0.01)
            async def inner():
                return sentinel.res
            return await inner()

        self.assertEqual(await outer(), sentinel.res)

    async def test_nested_timeout_inner_propagation(self):
        mock = Mock()

        @timeout(0.05)
        async def outer():
            mock(1)

            @timeout(0.01)
            async def inner():
                mock(2)
                await sleep(0.03)
                mock(3)
            await inner()
            mock(4)

        with self.assertRaises(CancelledError):
            await outer()

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_nested_timeout_outer_propagation(self):
        mock = Mock()

        @timeout(0.01)
        async def outer():
            mock(1)

            @timeout(0.05)
            async def inner():
                mock(2)
                await sleep(0.03)
                mock(3)
            await inner()
            mock(4)

        with self.assertRaises(CancelledError):
            await outer()

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_nested_timeout_outer_raises(self):
        mock = Mock()

        @timeout(0.03)
        async def outer():
            mock(1)

            @timeout(0.07)
            async def inner():
                mock(2)
                await sleep(0.01)
                mock(3)
            await inner()
            mock(4)
            await sleep(0.04)
            mock(5)

        with self.assertRaises(CancelledError):
            await outer()

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3), call(4)])

    async def test_nested_timeout_outer_raises_inner_silent(self):
        mock = Mock()

        @timeout(0.05)
        async def outer():
            mock(1)

            @timeout(0.01, exception=None)
            async def inner():
                mock(2)
                await sleep(0.03)
                mock(3)
            await inner()
            mock(4)
            await sleep(0.05)
            mock(5)

        with self.assertRaises(CancelledError):
            await outer()

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(4)])

    async def test_nested_timeout_raises_with_same_timeout(self):
        mock = Mock()

        @timeout(0.01)
        async def outer():
            mock(1)

            @timeout(0.01)
            async def inner():
                mock(2)
                await sleep(0.03)
                mock(3)
            await inner()
            mock(4)

        with self.assertRaises(CancelledError):
            await outer()

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_multiple_calls_with_expected_delay(self):
        @timeout(0.01)
        async def fn():
            pass
        await fn()
        await sleep(0.01)
        await fn()

    async def test_multiple_calls_with_unexpected_delay(self):
        @timeout(0.01)
        async def fn():
            await sleep(0.02)
        with self.assertRaises(CancelledError):
            await fn()
        with self.assertRaises(CancelledError):
            await fn()

    async def test_timeout_with_exception(self):
        @timeout(0.01)
        async def fn():
            raise ZeroDivisionError()
        with self.assertRaises(ZeroDivisionError):
            await fn()

    async def test_silent_timeout_with_exception(self):
        @timeout(0.01, exception=None)
        async def fn():
            raise ZeroDivisionError()
        with self.assertRaises(ZeroDivisionError):
            await fn()

    async def test_nested_timeout_with_exception(self):
        @timeout(0.02)
        async def outer():
            @timeout(0.01)
            async def inner():
                raise ZeroDivisionError()
            await inner()
        with self.assertRaises(ZeroDivisionError):
            await outer()

    async def test_timeout_with_cancelled_task(self):
        @timeout(0.01)
        async def fn():
            await sleep(0.02)

        with self.assertRaises(asyncio.CancelledError):
            task = asyncio.get_event_loop().create_task(fn())
            task.cancel()
            await task

    async def test_silent_timeout_with_cancelled_task(self):
        @timeout(0.01, exception=None)
        async def fn():
            await sleep(0.02)

        with self.assertRaises(asyncio.CancelledError):
            task = asyncio.get_event_loop().create_task(fn())
            task.cancel()
            await task
