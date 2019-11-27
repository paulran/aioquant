# -*- coding:utf-8 -*-

"""
Position object.

Author: HuangTao
Date:   2018/04/22
Email:  huangtao@ifclover.com
"""

import json

from aioquant.utils import tools


class Position:
    """Position object.

    Attributes:
        platform: Exchange platform name, e.g. `binance` / `bitmex`.
        account: Trading account name, e.g. `test@gmail.com`.
        strategy: Strategy name, e.g. `my_strategy`.
        symbol: Trading pair name, e.g. `ETH/BTC`.
    """

    def __init__(self, platform=None, account=None, strategy=None, symbol=None):
        self.platform = platform
        self.account = account
        self.strategy = strategy
        self.symbol = symbol
        self.short_quantity = 0  # Short quantity.
        self.short_avg_price = 0  # Short average price.
        self.long_quantity = 0  # Long quantity.
        self.long_avg_price = 0  # Long average price.
        self.liquid_price = 0  # Liquidation price.
        self.timestamp = None  # Update timestamp(millisecond).

    def update(self, short_quantity=0, short_avg_price=0, long_quantity=0, long_avg_price=0, liquid_price=0,
               timestamp=None):
        self.short_quantity = short_quantity
        self.short_avg_price = short_avg_price
        self.long_quantity = long_quantity
        self.long_avg_price = long_avg_price
        self.liquid_price = liquid_price
        self.timestamp = timestamp if timestamp else tools.get_cur_timestamp_ms()

    @property
    def data(self):
        d = {
            "platform": self.platform,
            "account": self.account,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "short_quantity": self.short_quantity,
            "short_avg_price": self.short_avg_price,
            "long_quantity": self.long_quantity,
            "long_avg_price": self.long_avg_price,
            "liquid_price": self.liquid_price,
            "timestamp": self.timestamp
        }
        return d

    def __str__(self):
        info = json.dumps(self.data)
        return info

    def __repr__(self):
        return str(self)
