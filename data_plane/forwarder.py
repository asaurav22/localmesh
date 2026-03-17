import uuid
import httpx
import logging
from fastapi import Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)


http_client = httpx.AsyncClient()

HOP_BY_HOP = {
    "host",
    "connection",
    "transfer-encoding",
    "keep-alive",
    "upgrade",
    "proxy-authentication",
    "proxy-authorization",
    "te",
    "trailers"
}


def strip_hop_by_hop(headers: dict) -> dict:
    """Remove headers that must not be forwarded to upstream"""
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}


def get_or_generate_correlation_id(headers: dict) -> tuple[str, bool]:
    """
    Returns (correlation_id, was_generated).
    Preserves client-provided ID, generates UUID4 if missing.
    """
    existing = headers.get("x-correlation-id") or headers.get("X-Correlation-ID")
    if existing:
        return existing, False
    return str(uuid.uuid4()), True


async def forward(request: Request, real_url: str) -> Response:
    """
    Forward the incoming request to the resolved upstream URL.
    Preserves method, headers, and body exactly.
    """
    clean_headers = strip_hop_by_hop(dict(request.headers))
    body = await request.body()

    corr_id, was_generated = get_or_generate_correlation_id(clean_headers)
    clean_headers["x-correlation-id"] = corr_id

    if was_generated:
        logger.info(f"[{corr_id}] Generated new correlation ID")
    else:
        logger.info(f"[{corr_id}] Preserved client correlation ID")

    logger.info(f"[{corr_id}] {request.method} /{request.url.path} -> {real_url}")

    upstream = await http_client.request(
        method=request.method,
        url=real_url,
        headers=clean_headers,
        content=body
    )

    logger.info(f"[{corr_id}] Response: {upstream.status_code} from {real_url}")

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=dict(upstream.headers)
    )
