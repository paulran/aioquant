# -*- coding:utf-8 -*-

"""
Market Server.

Market Server will get market data from Exchange via Websocket or REST as soon as possible, then packet market data into
MarketEvent and publish into EventCenter.
"""

import sys

from aioquant import const
from aioquant.configure import config
from aioquant import quant

def initialize():
    """Initialize Server."""

    for platform in config.markets:
        if platform == const.OKEX:
            from aioquant.markets.okex import OKEx as Market
        elif platform == const.BINANCE:
            from aioquant.markets.binance import Binance as Market
        else:
            from aioquant.utils import logger
            logger.error("platform error! platform:", platform)
            continue
        cc = config.markets[platform]
        cc["platform"] = platform
        Market(**cc)


def main():
    config_file = sys.argv[1]  # config file, e.g. market.json.
    quant.start(config_file, initialize)


if __name__ == "__main__":
    main()
