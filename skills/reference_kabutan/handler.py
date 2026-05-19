# ./skills/reference_kabutan/handler.py

import pathlib
import re
import pandas as pd
from sqlalchemy import create_engine


class Config:
    base_folder = pathlib.Path(
        r"/Users/samrullo/programming/pyprojects/yahoo_stock_parser"
    )
    stock_db_path = base_folder / "datasets" / "stock.db"
    db_uri = f"sqlite:///{stock_db_path}"


SCREEN_COLUMNS = [
    "ticker",
    "company_name_en",
    "industry",
    "market_cap_yen",
    "price_close_yen",
    "per",
    "pbr",
    "dividend_yield_pct",
]

ORDER_COLUMNS = {
    "market_cap_yen": "market_cap_yen",
    "market_cap": "market_cap_yen",
    "per": "per",
    "pbr": "pbr",
    "dividend_yield_pct": "dividend_yield_pct",
    "dividend_yield": "dividend_yield_pct",
}


def _get_engine():
    return create_engine(Config.db_uri)


def _load_latest_fundamentals():
    engine = _get_engine()
    cols = ["id", *SCREEN_COLUMNS, "asof_date"]
    query = f"SELECT {', '.join(cols)} FROM `kabutan_fundamentals`"
    fundamdf = pd.read_sql(query, engine)
    fundamdf = fundamdf.sort_values(["ticker", "id"]).drop_duplicates(
        "ticker", keep="last"
    )
    return fundamdf


def _parse_number(text):
    match = re.search(r"([\d,.]+)\s*([a-zA-Z]*)", text)
    if not match:
        return None

    value = float(match.group(1).replace(",", ""))
    unit = match.group(2).lower()

    if unit in {"t", "tn", "trn", "trln", "trillion"}:
        return value * 1_000_000_000_000
    if unit in {"b", "bn", "billion"}:
        return value * 1_000_000_000
    if unit in {"m", "mn", "million"}:
        return value * 1_000_000
    return value


def _parse_instruction(instruction):
    parsed = {}
    text = (instruction or "").lower()

    metric_patterns = {
        "market_cap_yen": r"(?:market cap|market capitalization|時価総額)[^\d]*(?:higher than|greater than|above|over|>=|>)?\s*([\d,.]+\s*(?:trln|trn|tn|trillion|bn|billion|m|million)?)",
        "dividend_yield_pct": r"(?:dividend yield|yield|配当利回り)[^\d]*(?:higher than|greater than|above|over|>=|>)?\s*([\d,.]+)\s*%?",
        "per": r"\bper\b[^\d]*(?:higher than|greater than|above|over|>=|>)?\s*([\d,.]+)",
        "pbr": r"\bpbr\b[^\d]*(?:higher than|greater than|above|over|>=|>)?\s*([\d,.]+)",
    }

    for key, pattern in metric_patterns.items():
        match = re.search(pattern, text)
        if match:
            parsed[f"min_{key}"] = _parse_number(match.group(1))

    if "market cap" in text or "market capitalization" in text or "時価総額" in text:
        parsed["order_by"] = "market_cap_yen"
    elif "dividend" in text or "yield" in text or "配当" in text:
        parsed["order_by"] = "dividend_yield_pct"
    elif "pbr" in text:
        parsed["order_by"] = "pbr"
    elif "per" in text:
        parsed["order_by"] = "per"

    limit_match = re.search(r"(?:top|limit|show)\s+(\d+)", text)
    if limit_match:
        parsed["limit"] = int(limit_match.group(1))

    return parsed


def _format_yen_compact(value):
    if pd.isna(value):
        return "-"
    value = float(value)
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"


def _format_float(value, digits=2):
    if pd.isna(value):
        return "-"
    return f"{float(value):.{digits}f}"


def _truncate(text, max_len):
    text = "" if pd.isna(text) else str(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _format_stock_table(df):
    headers = ["ticker", "company", "industry", "mcap", "price", "per", "pbr", "div%"]
    widths = [8, 22, 10, 8, 8, 6, 5, 6]
    lines = [
        " ".join(header.ljust(width) for header, width in zip(headers, widths)),
        " ".join("-" * width for width in widths),
    ]

    for _, row in df.iterrows():
        values = [
            _truncate(row["ticker"], widths[0]),
            _truncate(row["company_name_en"], widths[1]),
            _truncate(row["industry"], widths[2]),
            _format_yen_compact(row["market_cap_yen"]),
            _format_yen_compact(row["price_close_yen"]),
            _format_float(row["per"], 1),
            _format_float(row["pbr"], 2),
            _format_float(row["dividend_yield_pct"], 2),
        ]
        lines.append(
            " ".join(str(value).ljust(width)[:width] for value, width in zip(values, widths))
        )

    return "```\n" + "\n".join(lines) + "\n```"


def screen_reference_kabutan_stocks(
    instruction=None,
    order_by="market_cap_yen",
    order_desc=True,
    min_market_cap_yen=None,
    min_per=None,
    min_pbr=None,
    min_dividend_yield_pct=None,
    limit=10,
):
    parsed = _parse_instruction(instruction)
    order_by = parsed.get("order_by", order_by)
    limit = parsed.get("limit", limit)
    min_market_cap_yen = parsed.get("min_market_cap_yen", min_market_cap_yen)
    min_per = parsed.get("min_per", min_per)
    min_pbr = parsed.get("min_pbr", min_pbr)
    min_dividend_yield_pct = parsed.get(
        "min_dividend_yield_pct", min_dividend_yield_pct
    )

    order_col = ORDER_COLUMNS.get(order_by, "market_cap_yen")
    limit = max(1, min(int(limit or 10), 50))

    df = _load_latest_fundamentals()

    filters = []
    thresholds = {
        "market_cap_yen": min_market_cap_yen,
        "per": min_per,
        "pbr": min_pbr,
        "dividend_yield_pct": min_dividend_yield_pct,
    }
    for col, threshold in thresholds.items():
        if threshold is not None:
            df = df[df[col].notna() & (df[col] > float(threshold))]
            filters.append(f"{col} > {threshold:g}")

    df = df.sort_values(order_col, ascending=not bool(order_desc), na_position="last")
    total_matches = len(df)
    df = df.head(limit)

    return {
        "table": _format_stock_table(df),
        "columns": SCREEN_COLUMNS,
        "order_by": order_col,
        "order_desc": bool(order_desc),
        "filters": filters,
        "total_matches": total_matches,
        "returned": len(df),
    }


def reference_kabutan_fundamentals(ticker: str):
    """
    Search a record in kabutan fundamentals based on the ticker and return results
    """
    engine = _get_engine()
    fundamdf = pd.read_sql("SELECT * FROM `kabutan_fundamentals`", engine)
    if not ticker.endswith(".T"):
        ticker = f"{ticker}.T"
    fundamdf = fundamdf[fundamdf["ticker"] == ticker]
    if len(fundamdf) > 0:
        fundamdf = fundamdf.reset_index().iloc[-1]
        cols = [
            "ticker",
            "company_name_en",
            "website",
            "description",
            "price_close_yen",
            "price_low_yen",
            "price_high_yen",
            "per",
            "dividend_yield_pct",
            "market_cap_yen",
            "latest_eps_yen",
            "asof_date"
        ]
        return fundamdf[cols].to_dict()
    else:
        return {"error":f"No record in database for the ticker {ticker}"}


# Tool definition to tell the agent about the available 'save_note' tool
tools = [
    {
        "name": "reference_kabutan_fundamentals",
        "description": "Search a record in kabutan fundamentals local database based on the ticker and return results",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker"},                
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "screen_reference_kabutan_stocks",
        "description": (
            "Screen Japanese stocks from the local kabutan_fundamentals database. "
            "Returns a Telegram-friendly table with ticker, company_name_en, industry, "
            "market_cap_yen, price_close_yen, per, pbr, and dividend_yield_pct. "
            "Use for requests like 'Pull stocks where market cap is higher than 1 trln yen' "
            "or 'dividend yield is higher than 2%'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Natural-language screening instruction from the user.",
                },
                "order_by": {
                    "type": "string",
                    "enum": [
                        "market_cap_yen",
                        "per",
                        "pbr",
                        "dividend_yield_pct",
                    ],
                    "description": "Column to order by.",
                },
                "order_desc": {
                    "type": "boolean",
                    "description": "Whether to sort descending. Default true.",
                },
                "min_market_cap_yen": {
                    "type": "number",
                    "description": "Minimum market capitalization in yen.",
                },
                "min_per": {
                    "type": "number",
                    "description": "Minimum PER.",
                },
                "min_pbr": {
                    "type": "number",
                    "description": "Minimum PBR.",
                },
                "min_dividend_yield_pct": {
                    "type": "number",
                    "description": "Minimum dividend yield percentage, e.g. 2 for 2%.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return. Default 10, max 50.",
                },
            },
            "required": [],
        },
    },
]


# Function called when the agent invokes this tool
async def execute(tool_name, tool_input, context):
    if tool_name == "reference_kabutan_fundamentals":
        return reference_kabutan_fundamentals(tool_input['ticker'])
    if tool_name == "screen_reference_kabutan_stocks":
        return screen_reference_kabutan_stocks(
            instruction=tool_input.get("instruction"),
            order_by=tool_input.get("order_by", "market_cap_yen"),
            order_desc=tool_input.get("order_desc", True),
            min_market_cap_yen=tool_input.get("min_market_cap_yen"),
            min_per=tool_input.get("min_per"),
            min_pbr=tool_input.get("min_pbr"),
            min_dividend_yield_pct=tool_input.get("min_dividend_yield_pct"),
            limit=tool_input.get("limit", 10),
        )
        

    return {"error": f"Unknown tool: {tool_name}"}
