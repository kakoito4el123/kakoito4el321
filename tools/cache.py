import threading
import time

# Делаем это глобальным для всего процесса
_cache = {}
_cache_times = {}
_lock = threading.Lock()

def cache_get(key, max_age=None):
    with _lock:
        val = _cache.get(key)
        if val is not None and max_age is not None and time.monotonic() - _cache_times.get(key, 0) > max_age:
            _cache.pop(key, None)
            _cache_times.pop(key, None)
            val = None
        if val is not None:
            print(f"[CACHE] Взял из ОЗУ: {key}")
        return val

def cache_set(key, value):
    with _lock:
        print(f"[CACHE] Записал в ОЗУ: {key}")
        _cache[key] = value
        _cache_times[key] = time.monotonic()

def cache_invalidate(key):
    with _lock:
        if key in _cache:
            del _cache[key]
            _cache_times.pop(key, None)