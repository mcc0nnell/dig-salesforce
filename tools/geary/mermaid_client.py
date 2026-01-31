import json
import urllib.error
import urllib.request


DEFAULT_TIMEOUT = 15


def render_mermaid(mermaid: str, *, worker_url: str, geary_key: str, id: str | None = None, timeout=DEFAULT_TIMEOUT) -> dict:
    if mermaid is None or not mermaid.strip():
        raise ValueError("mermaid must be non-empty")
    if not worker_url:
        raise ValueError("worker_url must be set")
    if not geary_key:
        raise ValueError("geary_key must be set")

    payload = {"mermaid": mermaid, "format": "json"}
    if id:
        payload["id"] = id

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        worker_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Geary-Key": geary_key,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        status = err.code
        body = err.read().decode("utf-8") if err.fp else ""
    except urllib.error.URLError as err:
        raise RuntimeError(f"request_failed: {err}") from err

    if status == 401:
        raise RuntimeError("unauthorized: check GEARY_KEY")
    if status == 413:
        raise RuntimeError("payload_too_large: > 200KB")
    if status < 200 or status >= 300:
        snippet = body.strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        raise RuntimeError(f"runner_error: {status} {snippet}".strip())

    try:
        return json.loads(body)
    except json.JSONDecodeError as err:
        raise RuntimeError("invalid_json_response") from err
