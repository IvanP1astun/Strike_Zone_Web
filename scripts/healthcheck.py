"""Docker healthcheck: exit 0 if the app answers /health/ with 200, else 1.

Runs inside the container with the standard library only. The Host header is
taken from DJANGO_ALLOWED_HOSTS so that Django's ALLOWED_HOSTS check passes.
"""
import os
import sys
import urllib.request

PORT = os.getenv('HEALTHCHECK_PORT', '8000')


def pick_host():
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost').split(','):
        host = host.strip().lstrip('.')
        if host and host != '*':
            return host
    return 'localhost'


def main():
    request = urllib.request.Request(
        'http://127.0.0.1:%s/health/' % PORT, headers={'Host': pick_host()}
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return 0 if response.status == 200 else 1
    except Exception as error:
        print('healthcheck failed:', error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
