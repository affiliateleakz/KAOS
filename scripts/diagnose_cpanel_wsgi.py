"""Bounded local probes of the installed WSGI entrypoint; no credentials or DB writes."""
import io
import json
from pathlib import Path
import runpy
import signal
import time
from wsgiref.util import setup_testing_defaults


def deadline(signum, frame):
    raise TimeoutError('Local probe deadline')


def main():
    signal.signal(signal.SIGALRM, deadline)
    entry = Path.home() / 'tradingwithkaos.com/backend/passenger_wsgi.py'
    print('Loading installed WSGI entrypoint (20-second limit)...', flush=True)
    try:
        signal.alarm(20)
        start = time.monotonic()
        app = runpy.run_path(str(entry))['application']
        print(f'Entrypoint loaded in {time.monotonic()-start:.2f}s', flush=True)
        signal.alarm(0)
    except Exception as exc:
        print('Entrypoint failed: ' + type(exc).__name__, flush=True)
        return 1
    finally:
        signal.alarm(0)
    for method, path, body in [('GET', '/api', b''), ('POST', '/api/auth/login', b'{}')]:
        print(f'Local {method} {path} (20-second limit; no credentials)...', flush=True)
        env = {};setup_testing_defaults(env)
        env.update(REQUEST_METHOD=method, PATH_INFO=path, CONTENT_TYPE='application/json',
                   CONTENT_LENGTH=str(len(body)), HTTP_ORIGIN='https://tradingwithkaos.com',
                   HTTP_HOST='api.tradingwithkaos.com', REMOTE_ADDR='127.0.0.1')
        env['wsgi.input'] = io.BytesIO(body);env['wsgi.url_scheme'] = 'https'
        status = [];headers = [];response = None
        try:
            signal.alarm(20);start = time.monotonic()
            response = app(env, lambda s, h, exc_info=None: (status.append(s), headers.extend(h)))
            content = b''.join(response)
            print(f'{status[0] if status else "NO STATUS"} in {time.monotonic()-start:.2f}s', flush=True)
            if method == 'GET' and json.loads(content).get('runtime') == 'native-wsgi':
                print('Legacy runtime detected; skipping login probe.', flush=True);return 1
            expected = '200' if method == 'GET' else '422'
            if not status or not status[0].startswith(expected):
                print('Unexpected status. Response contents withheld; inspect application logs.', flush=True);return 1
        except Exception as exc:
            print('Probe failed: ' + type(exc).__name__ + '. Response and settings withheld.', flush=True)
            return 1
        finally:
            signal.alarm(0)
            if response is not None and hasattr(response, 'close'):response.close()
    print('Local WSGI health and login validation passed. If public requests time out, compare the hosting request/worker path.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
