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


async def forward(request: Request, real_url: str) -> Response:
    """
    Forward the incoming request to the resolved upstream URL.
    Preserves method, headers, and body exactly.
    """
    clean_headers = strip_hop_by_hop(dict(request.headers))
    body = await request.body()

    logger.info(f"[FORWARD] {request.method} {real_url}")

    upstream = await http_client.request(
        method=request.method,
        url=real_url,
        headers=clean_headers,
        content=body
    )

    logger.info(f"[FORWARD] Response : {upstream.status_code} from {real_url}")

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=dict(upstream.headers)
    )
