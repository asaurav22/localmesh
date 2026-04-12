import httpx
import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from control_plane.models import DashboardResponse
from control_plane import registry as registry_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

SIDECAR_URL = "http://localhost:8001"


async def _fetch_sidecar_data() -> dict:
    """Fetch metrics and breaker state from sidecar — best effort."""
    result = {"metrics": {}, "breakers": {}}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            metrics_r = await client.get(f"{SIDECAR_URL}/metrics")
            breakers_r = await client.get(f"{SIDECAR_URL}/breakers")
            if metrics_r.status_code == 200:
                result["metrics"] = metrics_r.json()
            if breakers_r.status_code == 200:
                result["breakers"] = breakers_r.json()
    except Exception as e:
        logger.warning(f"[DASHBOARD] Could not reach sidecar: {e}")
    return result


@router.get("", response_model=DashboardResponse)
def dashboard():
    return registry_store.get_dashboard_data()


@router.get("/json")
async def dashboard_json():
    """
    Full dashboard payload — registry state + sidecar metrics + breakers.
    Single endpoint that aggregates everything needed for a dashboard view.
    """
    registry_data = registry_store.get_dashboard_data()
    sidecar_data = await _fetch_sidecar_data()

    return JSONResponse(content={
        "mesh_summary": registry_data["mesh_summary"],
        "services": registry_data["services"],
        "metrics": sidecar_data["metrics"],
        "breakers": sidecar_data["breakers"]
    })


@router.get("/ui", response_class=HTMLResponse)
async def dashboard_ui():
    """
    Live HTML dashboard — auto-refreshes every 5 seconds.
    Shows registry state, health, sidecar metrics, and circuit breakers.
    """
    registry_data = registry_store.get_dashboard_data()
    sidecar_data = await _fetch_sidecar_data()

    services = registry_data["services"]
    summary = registry_data["mesh_summary"]
    metrics = sidecar_data["metrics"]
    breakers = sidecar_data["breakers"]

    # ── service rows ──────────────────────────────────────
    def health_color(health: str) -> str:
        return {"healthy": "#27ae60", "unhealthy": "#e74c3c"}.get(health, "#f39c12")

    def status_color(status: str) -> str:
        return "#27ae60" if status == "healthy" else "#f39c12"

    service_rows = ""
    for s in services:
        hc = health_color(s["health"])
        sc = status_color(s["status"])
        service_rows += f"""
        <tr>
            <td><strong>{s['name']}</strong></td>
            <td>{s['host']}:{s['port']}</td>
            <td style="color:{hc}; font-weight:bold">{s['health'].upper()}</td>
            <td style="color:{sc}">{s['expires_in_seconds']}s</td>
            <td>v{s['version']}</td>
            <td>{s.get('consecutive_failures', 0)}</td>
        </tr>"""

    if not service_rows:
        service_rows = "<tr><td colspan='6' style='text-align:center;color:#888'>No services registered</td></tr>"

    # ── metrics rows ──────────────────────────────────────
    metrics_rows = ""
    for svc, m in metrics.items():
        err_color = "#e74c3c" if m["error_rate"] > 0 else "#27ae60"
        metrics_rows += f"""
        <tr>
            <td><strong>{svc}</strong></td>
            <td>{m['total']}</td>
            <td style="color:{err_color}">{m['errors']}</td>
            <td style="color:{err_color}">{round(m['error_rate'] * 100, 1)}%</td>
            <td>{m['p50_ms']}ms</td>
            <td>{m['p95_ms']}ms</td>
            <td>{m['p99_ms']}ms</td>
        </tr>"""

    if not metrics_rows:
        metrics_rows = "<tr><td colspan='7' style='text-align:center;color:#888'>No traffic recorded yet</td></tr>"

    # ── breaker rows ──────────────────────────────────────
    def breaker_color(state: str) -> str:
        return {"closed": "#27ae60", "open": "#e74c3c", "half_open": "#f39c12"}.get(state, "#888")

    breaker_rows = ""
    for svc, b in breakers.items():
        bc = breaker_color(b["state"])
        breaker_rows += f"""
        <tr>
            <td><strong>{svc}</strong></td>
            <td style="color:{bc}; font-weight:bold">{b['state'].upper()}</td>
            <td>{b['failure_count']}</td>
            <td>{b['failure_threshold']}</td>
            <td>{b['open_duration']}s</td>
            <td>{'Yes' if b['probe_sent'] else 'No'}</td>
        </tr>"""

    if not breaker_rows:
        breaker_rows = "<tr><td colspan='6' style='text-align:center;color:#888'>No breakers active yet</td></tr>"

    # ── summary badges ────────────────────────────────────
    summary_html = f"""
        <span class="badge" style="background:#27ae60">✅ Healthy: {summary['healthy']}</span>
        <span class="badge" style="background:#f39c12">⚠️ Expiring: {summary['expiring_soon']}</span>
        <span class="badge" style="background:#e74c3c">❌ Unhealthy: {summary['unhealthy']}</span>
        <span class="badge" style="background:#2c3e50">📦 Total: {summary['total_services']}</span>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="5">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalMesh Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0f1117;
            color: #e0e0e0;
            padding: 24px;
        }}
        h1 {{
            font-size: 24px;
            color: #ffffff;
            margin-bottom: 4px;
        }}
        .subtitle {{
            color: #888;
            font-size: 13px;
            margin-bottom: 20px;
        }}
        .badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 28px;
        }}
        .badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            color: white;
        }}
        h2 {{
            font-size: 15px;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            margin-top: 28px;
            border-bottom: 1px solid #2a2a2a;
            padding-bottom: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        th {{
            background: #1e2130;
            color: #aaa;
            padding: 10px 14px;
            text-align: left;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid #1e2130;
            color: #ddd;
        }}
        tr:hover td {{ background: #1a1d2a; }}
        .refresh-note {{
            color: #555;
            font-size: 12px;
            margin-top: 24px;
            text-align: right;
        }}
    </style>
</head>
<body>
    <h1>🏍️ LocalMesh Dashboard</h1>
    <div class="subtitle">Auto-refreshes every 5 seconds</div>

    <div class="badges">
        {summary_html}
    </div>

    <h2>📋 Service Registry</h2>
    <table>
        <thead>
            <tr>
                <th>Service</th>
                <th>Host:Port</th>
                <th>Health</th>
                <th>Expires In</th>
                <th>Version</th>
                <th>Failures</th>
            </tr>
        </thead>
        <tbody>
            {service_rows}
        </tbody>
    </table>

    <h2>📊 Sidecar Metrics</h2>
    <table>
        <thead>
            <tr>
                <th>Service</th>
                <th>Total</th>
                <th>Errors</th>
                <th>Error Rate</th>
                <th>p50</th>
                <th>p95</th>
                <th>p99</th>
            </tr>
        </thead>
        <tbody>
            {metrics_rows}
        </tbody>
    </table>

    <h2>⚡ Circuit Breakers</h2>
    <table>
        <thead>
            <tr>
                <th>Service</th>
                <th>State</th>
                <th>Failures</th>
                <th>Threshold</th>
                <th>Open Duration</th>
                <th>Probe Sent</th>
            </tr>
        </thead>
        <tbody>
            {breaker_rows}
        </tbody>
    </table>

    <div class="refresh-note">Last rendered — auto-refreshing every 5s</div>
</body>
</html>"""

    return HTMLResponse(content=html)
