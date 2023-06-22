import asyncio
import signal
import sys
from asyncio import sleep
from unittest.mock import Mock, call

if sys.version_info >= (3, 8):
    from unittest import IsolatedAsyncioTestCase as TestCase
else:
    from asynctest import TestCase

from rtry import CancelledError, timeout
from rtry.types import AsyncTimeoutProxy

from ._ignore_exception import ignore_exception


class TestAsyncTimeoutContext(TestCase):
    async def test_no_timeout(self):
        mock = Mock()
        async with timeout(0):
            mock(1)
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_timeout_without_delay(self):
        mock = Mock()
        async with timeout(0.01):
            mock(1)
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_timeout_with_expected_delay(self):
        mock = Mock()
        async with timeout(0.02):
            mock(1)
            await sleep(0.01)
            mock(2)
        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_timeout_with_unexpected_delay(self):
        mock = Mock()
        with self.assertRaises(CancelledError):
            async with timeout(0.01):
                mock(1)
                await sleep(0.03)
                mock(2)
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_timeout_with_ignored_inner_exception(self):
        mock = Mock()
        with self.assertRaises(CancelledError):
            async with timeout(0.05):
                async with timeout(0.01):
                    async with ignore_exception(CancelledError, 0.05):
                        mock(1)
                        await sleep(0.02)
                        mock(2)
                    mock(3)
                mock(4)
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_timeout_context(self):
        async with timeout(0.01) as smth:
            self.assertIsInstance(smth, AsyncTimeoutProxy)

    async def test_timeout_proxy_exception_property(self):
        async with timeout(0.05) as t:
            self.assertTrue(issubclass(t.exception, CancelledError))

    async def test_silent_timeout_proxy_exception_property(self):
        async with timeout(0.05, exception=None) as t:
            self.assertIsNone(t.exception)

    async def test_timeout_remaining_property(self):
        async with timeout(1.0) as t:
            self.assertLess(t.remaining, 1.0)

    async def test_timeout_remaining_property_before(self):
        seconds = 1.0
        t = timeout(seconds)
        async with t:
            self.assertLess(t.remaining, seconds)

    async def test_timeout_remaining_property_after(self):
        t = timeout(0.01)
        async with t:
            pass
        await sleep(0.02)
        self.assertEqual(t.remaining, 0)

    async def test_silent_timeout_with_unexpected_delay(self):
        mock = Mock()
        async with timeout(0.01, exception=None):
            mock(1)
            await sleep(0.02)
            mock(2)
        self.assertEqual(mock.mock_calls, [call(1)])

    async def test_nested_silent_timeout_with_exception(self):
        with self.assertRaises(CancelledError):
            async with timeout(0.05, exception=None):
                async with timeout(0.01):
                    await sleep(0.03)

    async def test_restores_prev_signal_handler_with_expected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        async with timeout(0.02):
            await sleep(0.01)

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    async def test_restores_prev_signal_handler_with_unexpected_delay(self):
        def handler():
            pass
        signal.signal(signal.SIGALRM, handler)

        with self.assertRaises(CancelledError):
            async with timeout(0.01):
                await sleep(0.02)

        handler_after = signal.getsignal(signal.SIGALRM)
        self.assertEqual(handler_after, handler)

    async def test_timeout_custom_exception_with_unexpected_delay(self):
        class CustomException(CancelledError):
            pass

        with self.assertRaises(CustomException):
            async with timeout(0.01, exception=CustomException):
                await sleep(0.02)

    async def test_timeout_custom_exception_with_manual_raise(self):
        class CustomException(CancelledError):
            pass

        with self.assertRaises(CancelledError):
            async with timeout(0.01, exception=CustomException) as t:
                raise t.exception()

    async def test_nested_timeout_inner_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.05):
                mock(1)
                async with timeout(0.01):
                    mock(2)
                    await sleep(0.03)
                    mock(3)
                mock(4)

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_nested_timeout_outer_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.01):
                mock(1)
                async with timeout(0.05):
                    mock(2)
                    await sleep(0.03)
                    mock(3)
                mock(4)

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_nested_timeout_outer_raises(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.03):
                mock(1)
                async with timeout(0.07):
                    mock(2)
                    await sleep(0.01)
                    mock(3)
                mock(4)
                await sleep(0.04)
                mock(5)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3), call(4)])

    async def test_nested_timeout_outer_raises_inner_silent(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.05):
                mock(1)
                async with timeout(0.01, exception=None):
                    mock(2)
                    await sleep(0.03)
                    mock(3)
                mock(4)
                await sleep(0.05)
                mock(5)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(4)])

    async def test_nested_timeout_raises_with_same_timeout(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.01):
                mock(1)
                async with timeout(0.01):
                    mock(2)
                    await sleep(0.03)
                    mock(3)
                mock(4)

        self.assertEqual(mock.mock_calls, [call(1), call(2)])

    async def test_multiple_nested_timeout_inner_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.07):
                mock(1)
                async with timeout(0.05):
                    mock(2)
                    async with timeout(0.01):
                        mock(3)
                        await sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3)])

    async def test_multiple_nested_silent_timeout_inner_propagation(self):
        mock = Mock()

        async with timeout(0.07):
            mock(1)
            async with timeout(0.05):
                mock(2)
                async with timeout(0.01, exception=None):
                    mock(3)
                    await sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3), call(5), call(6)])

    async def test_multiple_nested_timeout_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.07):
                mock(1)
                async with timeout(0.01):
                    mock(2)
                    async with timeout(0.05):
                        mock(3)
                        await sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3)])

    async def test_multiple_nested_silent_timeout_propagation(self):
        mock = Mock()

        async with timeout(0.07):
            mock(1)
            async with timeout(0.01, exception=None):
                mock(2)
                async with timeout(0.05):
                    mock(3)
                    await sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3), call(6)])

    async def test_multiple_nested_timeout_outer_propagation(self):
        mock = Mock()

        with self.assertRaises(CancelledError):
            async with timeout(0.01):
                mock(1)
                async with timeout(0.07):
                    mock(2)
                    async with timeout(0.05):
                        mock(3)
                        await sleep(0.03)
                        mock(4)
                    mock(5)
                mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3)])

    async def test_multiple_nested_silent_timeout_outer_propagation(self):
        mock = Mock()

        async with timeout(0.01, exception=None):
            mock(1)
            async with timeout(0.07):
                mock(2)
                async with timeout(0.05):
                    mock(3)
                    await sleep(0.03)
                    mock(4)
                mock(5)
            mock(6)

        self.assertEqual(mock.mock_calls, [call(1), call(2), call(3)])

    async def test_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            async with timeout(0.01):
                raise ZeroDivisionError()

    async def test_silent_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            async with timeout(0.01, exception=None):
                raise ZeroDivisionError()

    async def test_nested_timeout_with_exception(self):
        with self.assertRaises(ZeroDivisionError):
            async with timeout(0.02):
                async with timeout(0.01):
                    raise ZeroDivisionError()

    async def test_timeout_with_cancelled_task(self):
        with self.assertRaises(asyncio.CancelledError):
            async with timeout(0.01):
                task = asyncio.get_event_loop().create_task(sleep(0.02))
                task.cancel()
                await task

    async def test_silent_timeout_with_cancelled_task(self):
        with self.assertRaises(asyncio.CancelledError):
            async with timeout(0.01, exception=None):
                task = asyncio.get_event_loop().create_task(sleep(0.02))
                task.cancel()
                await task

    async def test_timeout_proxy_repr(self):
        async with timeout(1.0) as t:
            self.assertTrue(repr(t).startswith("AsyncTimeoutProxy(timeout(0.9"))
            self.assertTrue(repr(t).endswith(", exception={}))".format(repr(CancelledError))))

        async with timeout(1.0, exception=None) as t:
            self.assertTrue(repr(t).startswith("AsyncTimeoutProxy(timeout(0.9"))
            self.assertTrue(repr(t).endswith(", exception=None))"))
