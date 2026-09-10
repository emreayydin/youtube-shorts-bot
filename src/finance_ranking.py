"""Read-only market snapshots and deterministic weekly rankings.

The ranking is deliberately calculated locally from fetched prices. No language
model is involved in the numeric ordering. The stock list is an explicit
watchlist, not a claim about every listed company; crypto is filtered to a
declared market-cap/volume universe. Every result carries its source and UTC
timestamp so a script cannot be mistaken for a timeless recommendation.
"""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FINANCE_CONFIG = ROOT / "config" / "finance.json"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
COINGECKO_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"
USER_AGENT = "DifferenceMoneyRanking/1.0 (+https://www.youtube.com/@differencemoney)"
STABLECOINS = {
    "usdt", "usdc", "dai", "tusd", "usde", "usds", "fdusd", "usdd",
    "frax", "lusd", "pyusd", "eurc", "eurt", "xaut",
}


def _get_json(url: str, timeout: int = 20):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _as_of(timestamp: int | float | None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def _percent(value: float) -> float:
    # Stable, human-readable output without binary float noise in scripts.
    return round(value, 2)


def load_finance_config() -> dict:
    with FINANCE_CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def _stock_item(entry: dict, lookback_sessions: int) -> dict:
    symbol = entry["symbol"].upper()
    query = urllib.parse.urlencode({"range": "1mo", "interval": "1d", "events": "history"})
    source_url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol)) + "?" + query
    payload = _get_json(source_url)
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError(f"Keine Kursdaten für {symbol}")
    timestamps = result.get("timestamp") or []
    closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    points = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
    if len(points) <= lookback_sessions:
        raise ValueError(f"Zu wenige Handelstage für {symbol}")
    previous_ts, previous = points[-(lookback_sessions + 1)]
    latest_ts, latest = points[-1]
    change = (latest / previous - 1) * 100 if previous else math.nan
    if not math.isfinite(change):
        raise ValueError(f"Ungültige Veränderung für {symbol}")
    meta = result.get("meta") or {}
    return {
        "symbol": symbol,
        "name": entry.get("name") or meta.get("longName") or symbol,
        "price": round(float(latest), 4),
        "changePct": _percent(change),
        "currency": meta.get("currency", "USD"),
        "period": f"{lookback_sessions} trading sessions",
        "asOf": _as_of(latest_ts),
        "source": "Yahoo Finance chart endpoint",
        "sourceUrl": source_url,
    }


def fetch_stock_ranking(top_n: int = 5, lookback_sessions: int = 5,
                        watchlist: list[dict] | None = None) -> dict:
    """Rank the configured liquid watchlist by deterministic price change."""
    config = load_finance_config()
    watchlist = watchlist or config["stockWatchlist"]
    items, errors = [], []
    for entry in watchlist:
        try:
            items.append(_stock_item(entry, lookback_sessions))
        except Exception as exc:  # one unavailable quote must not reorder the rest
            errors.append({"symbol": entry.get("symbol"), "error": str(exc)})
    items.sort(key=lambda item: item["changePct"], reverse=True)
    for rank, item in enumerate(items[:top_n], start=1):
        item["rank"] = rank
    return {
        "kind": "stocks",
        "period": f"{lookback_sessions} trading sessions",
        "universe": f"configured watchlist ({len(watchlist)} symbols)",
        "asOf": max((item["asOf"] for item in items), default=_as_of(None)),
        "source": "Yahoo Finance chart endpoint",
        "sourceUrl": "https://finance.yahoo.com/",
        "items": items[:top_n],
        "errors": errors,
    }


def fetch_crypto_ranking(top_n: int = 5, universe_size: int | None = None) -> dict:
    """Rank top-market-cap crypto assets by seven-day price change."""
    config = load_finance_config()["crypto"]
    universe_size = universe_size or int(config["marketCapUniverse"])
    params = urllib.parse.urlencode({
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": universe_size,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "7d",
        "locale": "en",
    })
    source_url = COINGECKO_MARKETS + "?" + params
    payload = _get_json(source_url)
    min_volume = float(config.get("minVolume24hUsd", 0))
    items = []
    for coin in payload:
        symbol = str(coin.get("symbol", "")).lower()
        if config.get("excludeStablecoins", True) and (
            symbol in STABLECOINS or str(coin.get("id", "")).lower() in STABLECOINS
        ):
            continue
        volume = float(coin.get("total_volume") or 0)
        change = coin.get("price_change_percentage_7d_in_currency")
        if change is None or volume < min_volume:
            continue
        items.append({
            "symbol": symbol.upper(),
            "name": coin.get("name") or symbol.upper(),
            "price": round(float(coin.get("current_price") or 0), 8),
            "changePct": _percent(float(change)),
            "marketCapRank": coin.get("market_cap_rank"),
            "marketCapUsd": coin.get("market_cap"),
            "volume24hUsd": int(volume),
            "period": "7 days",
            "asOf": coin.get("last_updated") or _as_of(None),
            "source": "CoinGecko markets endpoint",
            "sourceUrl": source_url,
        })
    items.sort(key=lambda item: item["changePct"], reverse=True)
    for rank, item in enumerate(items[:top_n], start=1):
        item["rank"] = rank
    return {
        "kind": "crypto",
        "period": "7 days",
        "universe": f"top {universe_size} by market cap, volume filtered",
        "asOf": max((item["asOf"] for item in items), default=_as_of(None)),
        "source": "CoinGecko markets endpoint",
        "sourceUrl": "https://www.coingecko.com/en/api",
        "items": items[:top_n],
        "errors": [],
    }


def ranking_to_content(ranking: dict) -> dict:
    """Turn a fetched ranking into a short, factual English script."""
    if not ranking.get("items"):
        raise RuntimeError(f"Ranking has no usable items: {ranking.get('errors')}")
    is_crypto = ranking["kind"] == "crypto"
    label = "crypto assets" if is_crypto else "stocks on this watchlist"
    period = ranking["period"]
    items = ranking["items"]
    title = (
        f"Top {len(items)} Crypto Moves in 7 Days"
        if is_crypto else f"Top {len(items)} Stocks on This Watchlist"
    )
    hook = "Which money mover won this week?"
    lines = [
        f"Snapshot, not a buy list. We rank {label} by {period}. "
        f"Data timestamp: {ranking['asOf']}."
    ]
    for item in reversed(items):
        direction = "up" if item["changePct"] >= 0 else "down"
        lines.append(f"Number {item['rank']}: {item['name']}, {direction} {abs(item['changePct']):.2f} percent.")
    lines.append("Top performance can reverse fast. Check the source and risk before acting.")
    lines.append("Which asset should we track next week?")
    return {
        "title": title,
        "hook": hook,
        "body": " ".join(lines),
        "cta": "Follow for the next transparent market snapshot.",
        "tags": ["markets", "investing", "stocks" if not is_crypto else "crypto", "finance", "money"],
        "category": "Finance",
        "language": "en",
        "ranking": ranking,
        "sources": [ranking["sourceUrl"]],
    }


def _historical_series(symbol: str, lookback_years: int = 10) -> tuple[list[dict], str]:
    """Fetch an adjusted-close history for one comparison asset.

    Adjusted close is used so distributions are not silently omitted. The
    returned source URL is kept with the content and shown in the upload
    description/on-screen provenance line.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=round(365.25 * lookback_years))
    params = urllib.parse.urlencode({
        "period1": int(start.timestamp()),
        "period2": int(end.timestamp()),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    })
    source_url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol)) + "?" + params
    payload = _get_json(source_url)
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError(f"Keine historischen Daten für {symbol}")

    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    adjusted = ((result.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    closes = quote.get("close") or []
    points = []
    for index, timestamp in enumerate(timestamps):
        value = adjusted[index] if index < len(adjusted) and adjusted[index] is not None else (
            closes[index] if index < len(closes) else None
        )
        if value is None:
            continue
        points.append({
            "date": datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d"),
            "value": float(value),
        })
    if len(points) < 2:
        raise ValueError(f"Zu wenige historische Daten für {symbol}")
    return points, source_url


def _money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f} million"
    return f"${value:,.0f}"


def generate_comparison() -> dict:
    """Create a 60+ second Difference Money comparison from live public data."""
    config = load_finance_config()
    comparison_config = config.get("comparison") or {}
    symbol = os.environ.get("COMPARISON_SYMBOL", comparison_config.get("symbol", "SPY")).upper()
    initial = float(os.environ.get("COMPARISON_INITIAL", comparison_config.get("initialAmount", 10_000)))
    lookback_years = int(os.environ.get("COMPARISON_LOOKBACK_YEARS", comparison_config.get("lookbackYears", 10)))
    series, source_url = _historical_series(symbol, lookback_years=lookback_years)

    asset_entry = next((item for item in config.get("stockWatchlist", []) if item.get("symbol", "").upper() == symbol), {})
    asset_label = os.environ.get("COMPARISON_LABEL", comparison_config.get("assetLabel") or asset_entry.get("name") or symbol)
    asset_label = str(asset_label)
    base = series[0]["value"]
    if base <= 0:
        raise ValueError(f"Ungültiger Startwert für {symbol}")
    value_series = [
        {"date": point["date"], "value": round(initial * point["value"] / base, 2)}
        for point in series
    ]
    start_year = value_series[0]["date"][:4]
    end_year = value_series[-1]["date"][:4]
    final_value = value_series[-1]["value"]
    difference = final_value - initial
    sign = "more" if difference >= 0 else "less"
    as_of = value_series[-1]["date"]

    body = (
        f"This is a historical illustration, not a prediction or a buy signal. "
        f"We start with {_money(initial)} on {value_series[0]['date']} and follow the adjusted historical performance of {asset_label}. "
        f"By {as_of}, that investment would be worth about {_money(final_value)}, before taxes and fees. "
        f"The cash balance would still be {_money(initial)}, so the difference would be about {_money(abs(difference))} {sign}. "
        "Markets can fall, and past performance does not guarantee future results. "
        "Which money comparison should we run next?"
    )
    return {
        "title": f"{_money(initial)} in {asset_label} vs cash: {start_year}–{end_year}",
        "hook": f"What if you invested {_money(initial)} in {asset_label} instead of keeping cash",
        "body": body,
        "cta": "Follow The Difference Money for transparent comparisons.",
        "tags": ["markets", "investing", "stocks", "finance", "money"],
        "category": "Finance",
        "language": "en",
        "video_format": "comparison",
        "sources": [source_url],
        "comparison": {
            "assetLabel": asset_label,
            "symbol": symbol,
            "initialAmount": round(initial, 2),
            "startDate": value_series[0]["date"],
            "endDate": value_series[-1]["date"],
            "asOf": as_of,
            "series": value_series,
            "source": "Yahoo Finance adjusted-close history",
            "sourceUrl": source_url,
        },
    }


def fetch_ranking(kind: str = "stocks") -> dict:
    kind = kind.strip().lower()
    if kind == "stocks":
        return fetch_stock_ranking()
    if kind == "crypto":
        return fetch_crypto_ranking()
    raise ValueError("Ranking-Typ muss 'stocks' oder 'crypto' sein")


def generate_ranking(kind: str = "stocks") -> dict:
    return ranking_to_content(fetch_ranking(kind))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read-only weekly finance ranking")
    parser.add_argument("--kind", choices=["stocks", "crypto"], default="stocks")
    args = parser.parse_args()
    print(json.dumps(generate_ranking(args.kind), ensure_ascii=False, indent=2))
