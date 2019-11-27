# -*- coding:utf-8 -*-

"""
Order object.

Author: HuangTao
Date:   2018/05/14
Email:  huangtao@ifclover.com
"""

import json

from aioquant.utils import tools


# Order type.
ORDER_TYPE_LIMIT = "LIMIT"  # Limit order.
ORDER_TYPE_MARKET = "MARKET"  # Market order.

# Order direction.
ORDER_ACTION_BUY = "BUY"  # Buy
ORDER_ACTION_SELL = "SELL"  # Sell

# Order status.
ORDER_STATUS_NONE = "NONE"  # New created order, no status.
ORDER_STATUS_SUBMITTED = "SUBMITTED"  # The order that submitted to server successfully.
ORDER_STATUS_PARTIAL_FILLED = "PARTIAL-FILLED"  # The order that filled partially.
ORDER_STATUS_FILLED = "FILLED"  # The order that filled fully.
ORDER_STATUS_CANCELED = "CANCELED"  # The order that canceled.
ORDER_STATUS_FAILED = "FAILED"  # The order that failed.

# Future order trade type.
TRADE_TYPE_NONE = "NONE"  # Unknown type, some Exchange's order information couldn't known the type of trade.
TRADE_TYPE_BUY_OPEN = "BUY_OPEN"  # Buy open, action = BUY & quantity > 0.
TRADE_TYPE_SELL_OPEN = "SELL_OPEN"  # Sell open, action = SELL & quantity < 0.
TRADE_TYPE_SELL_CLOSE = "SELL_CLOSE"  # Sell close, action = SELL & quantity > 0.
TRADE_TYPE_BUY_CLOSE = "BUY_CLOSE"  # Buy close, action = BUY & quantity < 0.


class Order:
    """Order object.

    Attributes:
        platform: Exchange platform name, e.g. `binance` / `bitmex`.
        account: Trading account name, e.g. `test@gmail.com`.
        strategy: Strategy name, e.g. `my_strategy`.
        order_id: Order id.
        client_order_id: Client order id.
        symbol: Trading pair name, e.g. `ETH/BTC`.
        action: Trading side, `BUY` / `SELL`.
        price: Order price.
        quantity: Order quantity.
        remain: Remain quantity that not filled.
        status: Order status.
        avg_price: Average price that filled.
        order_type: Order type.
        trade_type: Trade type, only for future order.
        fee: Trading fee.
        ctime: Order create time, millisecond.
        utime: Order update time, millisecond.
    """

    def __init__(self, platform=None, account=None, strategy=None, order_id=None, client_order_id=None, symbol=None,
                 action=None, price=0, quantity=0, remain=0, status=ORDER_STATUS_NONE, avg_price=0,
                 order_type=ORDER_TYPE_LIMIT, trade_type=TRADE_TYPE_NONE, fee=0, ctime=None, utime=None):
        self.platform = platform
        self.account = account
        self.strategy = strategy
        self.order_id = order_id
        self.client_order_id = client_order_id
        self.action = action
        self.order_type = order_type
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.remain = remain if remain else quantity
        self.status = status
        self.avg_price = avg_price
        self.trade_type = trade_type
        self.fee = fee
        self.ctime = ctime if ctime else tools.get_cur_timestamp_ms()
        self.utime = utime if utime else tools.get_cur_timestamp_ms()

    @property
    def data(self):
        d = {
            "platform": self.platform,
            "account": self.account,
            "strategy": self.strategy,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "action": self.action,
            "order_type": self.order_type,
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "remain": self.remain,
            "status": self.status,
            "avg_price": self.avg_price,
            "trade_type": self.trade_type,
            "fee": self.fee,
            "ctime": self.ctime,
            "utime": self.utime
        }
        return d

    def __str__(self):
        info = json.dumps(self.data)
        return info

    def __repr__(self):
        return str(self)
