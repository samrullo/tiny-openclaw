# ./skills/reference_kabutan/handler.py

import os
import pathlib
from dotenv import load_dotenv
from sampytools.configdict import ConfigDict
import pandas as pd
import numpy as np
import datetime
import logging
from sqlalchemy import create_engine, Table, MetaData, Date, Integer, Float, String
from sampytools.list_utils import search_list, get_list_diff
from sampytools.list_utils import print_list_items
from sampytools.datetime_utils import to_yyyymmdd_with_hyphen, to_yyyymmdd


def reference_kabutan_fundamentals(ticker: str):
    """
    Search a record in kabutan fundamentals based on the ticker and return results
    """
    class Config:
        base_folder = pathlib.Path(
            r"/Users/samrullo/programming/pyprojects/yahoo_stock_parser"
        )
        stock_db_path = base_folder / "datasets" / "stock.db"
        db_uri = f"sqlite:///{stock_db_path}"

    engine = create_engine(Config.db_uri)
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
]


# Function called when the agent invokes this tool
async def execute(tool_name, tool_input, context):
    if tool_name == "reference_kabutan_fundamentals":
        return reference_kabutan_fundamentals(tool_input['ticker'])
        

    return {"error": f"Unknown tool: {tool_name}"}
