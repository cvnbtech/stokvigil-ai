import json
import math
from typing import Any
from starlette.responses import JSONResponse


def sanitize_non_compliant_floats(obj: Any) -> Any:
    """
    Recursively replaces NaN, Infinity, and -Infinity with None (JSON null).
    Strictly enforces RFC 8259 JSON compliance and StokVigil Zero-Default Policy.
    Prevents 'ValueError: Out of range float values are not JSON compliant' in Starlette JSONResponse.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_non_compliant_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_non_compliant_floats(v) for v in obj]
    elif isinstance(obj, tuple):
        return [sanitize_non_compliant_floats(v) for v in obj]
    return obj


class SafeJSONResponse(JSONResponse):
    """
    RFC 8259 Compliant JSONResponse that automatically sanitizes NaN and Inf to null.
    Guarantees zero 500 crashes when financial, scientific, or technical indicators produce out-of-range floats.
    """
    def render(self, content: Any) -> bytes:
        sanitized = sanitize_non_compliant_floats(content)
        return json.dumps(
            sanitized,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
