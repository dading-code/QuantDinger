"""
QuantDinger MCP server — exposes the Agent Gateway as MCP tools.

This is intentionally a thin wrapper:
  * REST stays the source of truth (`/api/agent/v1`).
  * Only Read-class (R) and Backtest-class (B) tools are exposed.
  * The user-supplied agent token's scopes still gate every call server-side.

If you want to expose more (e.g. trading), prefer issuing a token with the
right scopes and keep this server unchanged — that way the security boundary
stays in the Gateway, not in the MCP layer.

Includes MT5 MCP tools ported from AI_Trading_Monitor_MT5_Observer project.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Import MT5 tools
try:
    from .mt5_tools import (
        mt5_get_account_info,
        mt5_get_open_positions,
        mt5_get_ohlc_data,
        mt5_get_market_data,
        mt5_get_trade_history,
        mt5_get_tick_data,
        mt5_get_market_depth,
        mt5_get_kronos_history,
        mt5_get_symbols,
        mt5_get_pending_orders,
        mt5_get_connection_status,
    )
    _mt5_available = True
except ImportError:
    _mt5_available = False


def _env(name: str, required: bool = True) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value and required:
        print(
            f"[quantdinger-mcp] missing required env var: {name}",
            file=sys.stderr,
        )
        sys.exit(2)
    return value


BASE_URL = _env("QUANTDINGER_BASE_URL").rstrip("/")
AGENT_TOKEN = _env("QUANTDINGER_AGENT_TOKEN")
TIMEOUT_S = float(os.environ.get("QUANTDINGER_TIMEOUT_S", "60"))


_client = httpx.Client(
    base_url=BASE_URL,
    timeout=TIMEOUT_S,
    headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
)


def _get(path: str, params: dict | None = None) -> Any:
    r = _client.get(path, params=params or {})
    return _unwrap(r)


def _post(path: str, json: dict | None = None, headers: dict | None = None) -> Any:
    r = _client.post(path, json=json or {}, headers=headers or {})
    return _unwrap(r)


def _unwrap(r: httpx.Response) -> Any:
    try:
        body = r.json()
    except Exception:
        return {
            "error": True,
            "status": r.status_code,
            "text": r.text[:2000],
        }
    if r.status_code >= 400:
        return {
            "error": True,
            "status": r.status_code,
            "body": body,
        }
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


mcp = FastMCP(
    "quantdinger",
    instructions=(
        "Tools for the QuantDinger self-hosted quant platform. "
        "All tools are tenant-scoped via the configured agent token. "
        "Trading is intentionally NOT exposed via MCP; use the REST API for that."
    ),
)


# ───────────────────────────── Read-class tools ─────────────────────────────

@mcp.tool()
def whoami() -> Any:
    """Return the calling token's identity, scopes, and allowlists."""
    return _get("/api/agent/v1/whoami")


@mcp.tool()
def list_markets() -> Any:
    """List markets the configured token is allowed to query."""
    return _get("/api/agent/v1/markets")


@mcp.tool()
def search_symbols(market: str, keyword: str = "", limit: int = 20) -> Any:
    """Find symbols in a market.

    Args:
        market: Market id, e.g. "Crypto", "USStock", "Forex".
        keyword: Substring/code; empty returns hot symbols.
        limit:   1..100, default 20.
    """
    return _get(
        f"/api/agent/v1/markets/{market}/symbols",
        params={"keyword": keyword, "limit": limit},
    )


@mcp.tool()
def get_klines(
    market: str,
    symbol: str,
    timeframe: str = "1D",
    limit: int = 300,
    before_time: int | None = None,
) -> Any:
    """OHLCV bars.

    Args:
        market:      e.g. "Crypto"
        symbol:      e.g. "BTC/USDT"
        timeframe:   "1m"/"5m"/"15m"/"30m"/"1H"/"4H"/"1D"/"1W"
        limit:       1..2000
        before_time: unix seconds; for paging older bars.
    """
    params = {"market": market, "symbol": symbol, "timeframe": timeframe, "limit": limit}
    if before_time is not None:
        params["before_time"] = int(before_time)
    return _get("/api/agent/v1/klines", params=params)


@mcp.tool()
def get_price(market: str, symbol: str) -> Any:
    """Latest price for a symbol."""
    return _get("/api/agent/v1/price", params={"market": market, "symbol": symbol})


@mcp.tool()
def list_strategies(limit: int = 50) -> Any:
    """List the tenant's strategies (compact projection)."""
    return _get("/api/agent/v1/strategies", params={"limit": limit})


@mcp.tool()
def get_strategy(strategy_id: int) -> Any:
    """Get a strategy by id (tenant-scoped)."""
    return _get(f"/api/agent/v1/strategies/{int(strategy_id)}")


@mcp.tool()
def get_job(job_id: str) -> Any:
    """Poll a previously-submitted backtest / experiment job."""
    return _get(f"/api/agent/v1/jobs/{job_id}")


@mcp.tool()
def list_jobs(kind: str | None = None, limit: int = 50) -> Any:
    """List recent jobs for this tenant. Optional `kind` filter."""
    params: dict[str, Any] = {"limit": limit}
    if kind:
        params["kind"] = kind
    return _get("/api/agent/v1/jobs", params=params)


# ───────────────────────────── Backtest-class tools ─────────────────────────────

@mcp.tool()
def submit_backtest(
    code: str,
    market: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 10000,
    commission: float = 0.001,
    slippage: float = 0.0,
    leverage: int = 1,
    trade_direction: str = "long",
    idempotency_key: str | None = None,
) -> Any:
    """Submit a backtest. Returns `{job_id, status, ...}` — poll with `get_job`.

    Args:
        code:           Indicator code (Python).
        market/symbol/timeframe: Series identification.
        start_date/end_date:     YYYY-MM-DD.
        initial_capital, commission, slippage, leverage, trade_direction:
                       standard backtest knobs.
        idempotency_key: optional; repeat calls with the same key return the
                         original job instead of submitting a duplicate.
    """
    payload = {
        "code": code,
        "market": market,
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "commission": commission,
        "slippage": slippage,
        "leverage": leverage,
        "trade_direction": trade_direction,
    }
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
    return _post("/api/agent/v1/backtests", json=payload, headers=headers)


@mcp.tool()
def regime_detect(
    market: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> Any:
    """Detect the current market regime (synchronous)."""
    return _post(
        "/api/agent/v1/experiments/regime/detect",
        json={
            "market": market, "symbol": symbol, "timeframe": timeframe,
            "startDate": start_date, "endDate": end_date,
        },
    )


@mcp.tool()
def submit_structured_tune(payload: dict) -> Any:
    """Submit a grid/random tuning job. Returns a job for polling.

    `payload` should include `base` (a backtest spec) and either `parameterSpace`
    (grid) or `randomTrials` (random). See `docs/AI_TRADING_SYSTEM_PLAN_CN.md`.
    """
    return _post("/api/agent/v1/experiments/structured-tune", json=payload)


# ───────────────────────────── MT5-class tools ─────────────────────────────
# Ported from AI_Trading_Monitor_MT5_Observer project

def _mt5_tool_wrapper(func):
    """Wrapper for MT5 tools to handle availability check."""
    def wrapper(*args, **kwargs):
        if not _mt5_available:
            return {
                "success": False,
                "error": "MT5 tools not available. MetaTrader5 library not installed."
            }
        import asyncio
        return asyncio.run(func(*args, **kwargs))
    return wrapper


if _mt5_available:
    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_account_info() -> Any:
        """Get MT5 account information including balance, equity, margin."""
        return await mt5_get_account_info({})

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_open_positions(symbol: str = "") -> Any:
        """Get current open positions from MT5.
        
        Args:
            symbol: Optional symbol filter (e.g., "XAUUSD.c")
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await mt5_get_open_positions(params)

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_ohlc_data(symbol: str = "XAUUSD.c", timeframe: str = "H1", count: int = 100) -> Any:
        """Get OHLC candlestick data from MT5.
        
        Args:
            symbol: Trading symbol (default: XAUUSD.c)
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN)
            count: Number of candles to fetch (max 1000)
        """
        return await mt5_get_ohlc_data({
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count
        })

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_market_data(symbol: str = "XAUUSD.c", timeframe: str = "H1", count: int = 50) -> Any:
        """Get market data including tick and candles from MT5.
        
        Args:
            symbol: Trading symbol (default: XAUUSD.c)
            timeframe: Timeframe for candles
            count: Number of candles
        """
        return await mt5_get_market_data({
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count
        })

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_trade_history(days: int = 7) -> Any:
        """Get trade history from MT5 for the specified number of days.
        
        Args:
            days: Number of days to look back (default: 7)
        """
        return await mt5_get_trade_history({"days": days})

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_tick_data(symbol: str = "XAUUSD.c", lookback_minutes: int = 5) -> Any:
        """Get tick data from MT5 for order flow analysis.
        
        Args:
            symbol: Trading symbol (default: XAUUSD.c)
            lookback_minutes: Lookback period in minutes (default: 5)
        """
        return await mt5_get_tick_data({
            "symbol": symbol,
            "lookback_minutes": lookback_minutes
        })

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_market_depth(symbol: str = "XAUUSD.c") -> Any:
        """Get market depth (DOM) data from MT5.
        
        Args:
            symbol: Trading symbol (default: XAUUSD.c)
        """
        return await mt5_get_market_depth({"symbol": symbol})

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_kronos_history(symbol: str = "XAUUSD.c", days: int = 7, timeframe: str = "M15") -> Any:
        """Get Kronos history data for AI analysis.
        
        Args:
            symbol: Trading symbol (default: XAUUSD.c)
            days: Number of days (default: 7)
            timeframe: Timeframe (default: M15)
        """
        return await mt5_get_kronos_history({
            "symbol": symbol,
            "days": days,
            "timeframe": timeframe
        })

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_symbols(group: str = "*") -> Any:
        """Get available symbols from MT5.
        
        Args:
            group: Symbol group filter (e.g., "*USD*", "Forex*")
        """
        return await mt5_get_symbols({"group": group})

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_pending_orders(symbol: str = "") -> Any:
        """Get pending orders from MT5.
        
        Args:
            symbol: Optional symbol filter
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await mt5_get_pending_orders(params)

    @mcp.tool()
    @_mt5_tool_wrapper
    async def mt5_get_connection_status() -> Any:
        """Get MT5 connection status."""
        return await mt5_get_connection_status({})


_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _resolve_transport() -> str:
    raw = (os.environ.get("QUANTDINGER_MCP_TRANSPORT") or "stdio").strip().lower()
    # Accept a few obvious aliases so users don't have to look this up.
    if raw in ("http", "streaming-http", "streamable_http"):
        raw = "streamable-http"
    if raw not in _TRANSPORTS:
        print(
            f"[quantdinger-mcp] unknown transport '{raw}'. "
            f"Expected one of: {sorted(_TRANSPORTS)} (or http/streaming-http alias).",
            file=sys.stderr,
        )
        sys.exit(2)
    return raw


def _apply_http_settings_from_env() -> None:
    """Bind host/port for HTTP transports without forcing a CLI dance.

    FastMCP exposes these via its `settings` attribute. We only touch them when
    the transport is HTTP-flavored, so the stdio default stays untouched.
    """
    host = (os.environ.get("QUANTDINGER_MCP_HOST") or "").strip()
    port_raw = (os.environ.get("QUANTDINGER_MCP_PORT") or "").strip()
    settings = getattr(mcp, "settings", None)
    if settings is None:
        return
    if host:
        try:
            settings.host = host
        except Exception:
            pass
    if port_raw:
        try:
            settings.port = int(port_raw)
        except Exception:
            print(
                f"[quantdinger-mcp] invalid QUANTDINGER_MCP_PORT='{port_raw}', ignoring.",
                file=sys.stderr,
            )


def main() -> None:
    """Entrypoint.

    Transport selection (env-only — works in both desktop and cloud):
      QUANTDINGER_MCP_TRANSPORT=stdio              (default; stdin/stdout)
      QUANTDINGER_MCP_TRANSPORT=sse                (SSE over HTTP)
      QUANTDINGER_MCP_TRANSPORT=streamable-http    (newer MCP HTTP transport)
      QUANTDINGER_MCP_HOST=0.0.0.0                 (bind for HTTP transports)
      QUANTDINGER_MCP_PORT=7800                    (port for HTTP transports)
    """
    transport = _resolve_transport()
    if transport in ("sse", "streamable-http"):
        _apply_http_settings_from_env()
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
