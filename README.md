# rtry

[![Codecov](https://img.shields.io/codecov/c/github/nikitanovosibirsk/rtry/master.svg?style=flat-square)](https://codecov.io/gh/nikitanovosibirsk/rtry)
[![PyPI](https://img.shields.io/pypi/v/rtry.svg?style=flat-square)](https://pypi.python.org/pypi/rtry/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rtry?style=flat-square)](https://pypi.python.org/pypi/rtry/)
[![Python Version](https://img.shields.io/pypi/pyversions/rtry.svg?style=flat-square)](https://pypi.python.org/pypi/rtry/)

## Installation

```bash
pip3 install rtry
```

## Documentation

* [timeout](#timeout)
    * [as context manager](#as-context-manager)
    * [as context manager (silent)](#as-context-manager-silent)
    * [as context manager (asyncio)](#as-context-manager-asyncio)
    * [as decorator](#as-decorator)
    * [as decorator (asyncio)](#as-decorator-asyncio)
    * [as argument](#as-argument)
* [retry](#retry)
    * [attempts](#attempts)
    * [until](#until)
    * [logger](#logger)
    * [delay](#delay)
    * [swallow](#swallow)
    * [asyncio](#asyncio)

---

## Timeout

##### As context manager

```python
from rtry import timeout, CancelledError

try:
    with timeout(3.0):
        resp = requests.get("https://httpbin.org/status/200")
except CancelledError:
    raise
else:
    print(resp)
```

##### As context manager (silent)

```python
from rtry import timeout, CancelledError

resp = None
with timeout(3.0, exception=None):
    resp = requests.get("https://httpbin.org/status/200")
```

##### As context manager (asyncio)

```python
import asyncio
import aiohttp
from rtry import timeout, CancelledError

async def main():
    try:
        async with aiohttp.ClientSession() as session, timeout(3.0):
            async with session.get("https://httpbin.org/status/200") as resp:
                return resp
    except CancelledError:
        raise
    else:
        print(resp)

asyncio.run(main())
```

##### As decorator

```python
from rtry import timeout, CancelledError

@timeout(3.0)
def fn():
    resp = requests.get("https://httpbin.org/status/200")
    return resp

try:
    resp = fn()
except CancelledError:
    raise
else:
    print(resp)
```

##### As decorator (asyncio)

```python
import asyncio
import aiohttp
from rtry import timeout, CancelledError

@timeout(3.0)
async def fn():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/status/200") as resp:
            return resp

async def main():
    try:
        resp = await fn()
    except CancelledError:
        raise
    else:
        print(resp)

asyncio.run(main())
```

##### As argument

```python
from rtry import retry, CancelledError

@retry(until=lambda r: r.status_code != 200, timeout=3.0)
def fn():
    resp = requests.get("https://httpbin.org/status/200")
    return resp

try:
    resp = fn()
except CancelledError:
    raise
else:
    print(resp)
```

## Retry

### Attempts

```python
@retry(attempts=2)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    print(resp)
    assert resp.status_code == 200
    return resp

resp = fn()
# <Response [500]>
# <Response [500]>
# Traceback:
#   AssertionError
```

### Until

```python
@retry(until=lambda r: r.status_code != 200, attempts=2)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    print(resp)
    return resp

resp = fn()
# <Response [500]>
# <Response [500]>
```

### Logger

##### Simple logger

```python
@retry(until=lambda r: r.status_code != 200, attempts=2, logger=print)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

resp = fn()
# 1 <Response [500]> <function fn at 0x103dcd268>
# 2 <Response [500]> <function fn at 0x103dcd268>
```

##### Custom logger

```python
def logger(attempt, result_or_exception, decorated):
    logging.info("Attempt: %d, Result: %s", attempt, result_or_exception)

@retry(until=lambda r: r.status_code != 200, attempts=2, logger=logger)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

resp = fn()
# INFO:root:Attempt: 1, Result: <Response [500]>
# INFO:root:Attempt: 2, Result: <Response [500]>
```

### Delay

##### Const delay

```python
@retry(until=lambda r: r.status_code != 200, attempts=2, delay=0.1)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

started_at = time.monotonic()
resp = fn()
ended_at = time.monotonic()
print('Elapsed {:.2f}'.format(ended_at - started_at))
# Elapsed 2.11
```

##### Custom delay

```python
from math import exp

@retry(until=lambda r: r.status_code != 200, attempts=2, delay=exp)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

started_at = time.monotonic()
resp = fn()
ended_at = time.monotonic()
print('Elapsed {:.2f}'.format(ended_at - started_at))
# Elapsed 11.79
```

### Swallow

##### Fail on first exception

```python
@retry(attempts=2, swallow=None, logger=print)
def fn():
    resp = requests.get("http://127.0.0.1/status/500")
    return resp

try:
    resp = fn()
except Exception as e:
    print(e)
    # HTTPConnectionPool(host='127.0.0.1', port=80): Max retries exceeded with url: /status/500
```

##### Swallow only ConnectionError

```python
from requests.exceptions import ConnectionError

@retry(attempts=2, swallow=ConnectionError, logger=print)
def fn():
    resp = requests.get("http://127.0.0.1/status/500")
    return resp

try:
    resp = fn()
except Exception as e:
    print(e)
    # 1 HTTPConnectionPool(host='127.0.0.1', port=80): Max retries exceeded with url: /status/500
    # 2 HTTPConnectionPool(host='127.0.0.1', port=80): Max retries exceeded with url: /status/500
    # HTTPConnectionPool(host='127.0.0.1', port=80): Max retries exceeded with url: /status/500
```

### AsyncIO

```python
import asyncio
import aiohttp
from rtry import retry

@retry(attempts=2)
async def fn():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/status/500") as resp:
            print(resp)
            assert resp.status == 200
            return resp

async def main():
    resp = await fn()
    # <ClientResponse(https://httpbin.org/status/500) [500 INTERNAL SERVER ERROR]>
    # <ClientResponse(https://httpbin.org/status/500) [500 INTERNAL SERVER ERROR]>
    # Traceback
    #   AssertionError

asyncio.run(main())
```
