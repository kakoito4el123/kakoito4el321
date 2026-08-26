import threading

# Делаем это глобальным для всего процесса
_cache = {}
_lock = threading.Lock()

def cache_get(key):
    with _lock:
        val = _cache.get(key)
        if val is not None:
            print(f"[CACHE] Взял из ОЗУ: {key}")
        return val

def cache_set(key, value):
    with _lock:
        print(f"[CACHE] Записал в ОЗУ: {key}")
        _cache[key] = value

def cache_invalidate(key):
    with _lock:
        if key in _cache:
            del _cache[key]