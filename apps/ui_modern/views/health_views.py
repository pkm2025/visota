"""Health check endpoints for monitoring."""
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache


def health_simple(request):
    """Lightweight health check — for load balancer pings."""
    return JsonResponse({'status': 'ok'})


def health_detailed(request):
    """Detailed health check — includes DB and cache status."""
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
    }
    all_ok = all(c.get('status') == 'ok' for c in checks.values())
    return JsonResponse({
        'status': 'ok' if all_ok else 'degraded',
        'checks': checks,
    }, status=200 if all_ok else 503)


def _check_database():
    try:
        connections['default'].cursor().execute('SELECT 1')
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _check_cache():
    try:
        cache.set('_health_check', '1', 10)
        val = cache.get('_health_check')
        if val in (b'1', '1'):
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'Cache set/get mismatch'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
