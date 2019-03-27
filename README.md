# rtry

[![License](https://img.shields.io/github/license/nikitanovosibirsk/rtry.svg)](https://github.com/nikitanovosibirsk/rtry)
[![Drone](https://cloud.drone.io/api/badges/nikitanovosibirsk/rtry/status.svg)](https://cloud.drone.io/nikitanovosibirsk/rtry)
[![Codecov](https://img.shields.io/codecov/c/github/nikitanovosibirsk/rtry/master.svg)](https://codecov.io/gh/nikitanovosibirsk/rtry)
[![PyPI](https://img.shields.io/pypi/v/rtry.svg)](https://pypi.python.org/pypi/rtry/)
[![Python Version](https://img.shields.io/pypi/pyversions/rtry.svg)](https://pypi.python.org/pypi/rtry/)

## Installation

```bash
pip3 install rtry
```

## Attempts

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

## Until

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

## Logger

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

## Delay

##### Const delay

```python
@retry(until=lambda r: r.status_code != 200, attempts=2, delay=0.1)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

started_at = time()
resp = fn()
ended_at = time()
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

started_at = time()
resp = fn()
ended_at = time()
print('Elapsed {:.2f}'.format(ended_at - started_at))
# Elapsed 11.79
```

## Swallow

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

## Timeout

##### As argument

```python
from retry import CancelledError

@retry(until=lambda r: r.status_code != 200, timeout=0.1)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

try:
    resp = fn()
except CancelledError:
    pass
```

##### As decorator

```python
from retry import timeout, CancelledError

@timeout(0.1)
def fn():
    resp = requests.get("https://httpbin.org/status/500")
    return resp

try:
    resp = fn()
except CancelledError:
    pass
```
