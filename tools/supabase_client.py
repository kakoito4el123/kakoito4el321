import os
import json
from supabase import create_client
from tools.cache import cache_get, cache_set, cache_invalidate

DEFAULT_SUPABASE_URL = "https://lfauuwmubxzizuoypjhl.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxmYXV1d211Ynh6aXp1b3lwamhsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzM1MDIzNCwiZXhwIjoyMDk4OTI2MjM0fQ.J1JjAz3Glv0zTlBmOmKrUJSV7FOIsfi1G22PxCMvc-M"


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL") or DEFAULT_SUPABASE_URL
    key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or DEFAULT_SUPABASE_KEY
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set in environment")
    return create_client(url, key)


def get_storage_bucket_name(name=None):
    return name or os.environ.get("SUPABASE_BUCKET", "media")


def get_storage_bucket(name=None):
    sb = get_supabase_client()
    return sb.storage.from_(get_storage_bucket_name(name))


def is_supabase_configured():
    return bool(os.environ.get("SUPABASE_URL") or DEFAULT_SUPABASE_URL) and bool(
        os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or DEFAULT_SUPABASE_KEY
    )


def load_json_store(name, default=None):
    cache_key = f"store:{name}"
    cached = cache_get(cache_key, max_age=3 if name == "messages" else None)
    if cached is not None:
        return cached

    sb = get_supabase_client()
    bucket_name = get_storage_bucket_name()
    path = f"store/{name}.json"
    try:
        data = sb.storage.from_(bucket_name).download(path)
        if isinstance(data, (bytes, bytearray)):
            payload = json.loads(data.decode("utf-8"))
            cache_set(cache_key, payload)
            return payload
        if hasattr(data, "decode"):
            payload = json.loads(data.decode("utf-8"))
            cache_set(cache_key, payload)
            return payload
    except Exception:
        payload = default if default is not None else {}
        cache_set(cache_key, payload)
        return payload
    payload = default if default is not None else {}
    cache_set(cache_key, payload)
    return payload


def save_json_store(name, payload):
    sb = get_supabase_client()
    bucket_name = get_storage_bucket_name()
    path = f"store/{name}.json"
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    sb.storage.from_(bucket_name).upload(
        path,
        content,
        {"content-type": "application/json", "upsert": "true"}
    )
    cache_set(f"store:{name}", payload)
    return path


def invalidate_json_store(name):
    cache_invalidate(f"store:{name}")
