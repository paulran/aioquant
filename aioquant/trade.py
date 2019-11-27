# -*- coding:utf-8 -*-

"""
Trade Module.

Author: HuangTao
Date:   2019/04/21
Email:  huangtao@ifclover.com
"""

import copy

from aioquant import const
from aioquant.utils import tools
from aioquant.error import Error
from aioquant.utils import logger
from aioquant.tasks import SingleTask
from aioquant.order import Order
from aioquant.position import Position


class Trade:
    """Trade Module.

    Attributes:
        strategy: What's name would you want to created for your strategy.
        platform: Exchange platform name. e.g. `binance` / `okex` / `bitmex`.
        symbol: Symbol name for your trade. e.g. `BTC/USDT`.
        host: HTTP request host.
        wss: Websocket address.
        account: Account name for this trade exchange.
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
        passphrase: API KEY Passphrase. (Only for `OKEx`)
        order_update_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `order_update_callback` is like `async def on_order_update_callback(order: Order): pass` and this
            callback function will be executed asynchronous when some order state updated.
        position_update_callback: You can use this param to specify a async callback function when you initializing
            Trade module. `position_update_callback` is like `async def on_position_update_callback(position: Position): pass`
            and this callback function will be executed asynchronous when position updated.
        init_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `init_callback` is like `async def on_init_callback(success: bool, **kwargs): pass`
            and this callback function will be executed asynchronous after Trade module object initialized done.
        error_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `error_callback` is like `async def on_error_callback(error: Error, **kwargs): pass`
            and this callback function will be executed asynchronous when some error occur while trade module is running.
    """

    def __init__(self, strategy=None, platform=None, symbol=None, host=None, wss=None, account=None, access_key=None,
                 secret_key=None, passphrase=None, order_update_callback=None, position_update_callback=None,
                 init_callback=None, error_callback=None, **kwargs):
        """Initialize trade object."""
        kwargs["strategy"] = strategy
        kwargs["platform"] = platform
        kwargs["symbol"] = symbol
        kwargs["host"] = host
        kwargs["wss"] = wss
        kwargs["account"] = account
        kwargs["access_key"] = access_key
        kwargs["secret_key"] = secret_key
        kwargs["passphrase"] = passphrase
        kwargs["order_update_callback"] = self._on_order_update_callback
        kwargs["position_update_callback"] = self._on_position_update_callback
        kwargs["init_callback"] = self._on_init_callback
        kwargs["error_callback"] = self._on_error_callback

        self._raw_params = copy.copy(kwargs)
        self._order_update_callback = order_update_callback
        self._position_update_callback = position_update_callback
        self._init_callback = init_callback
        self._error_callback = error_callback

        if platform == const.BINANCE:
            from aioquant.platform.binance import BinanceTrade as T
        elif platform == const.OKEX:
            from aioquant.platform.okex import OKExTrade as T
        else:
            logger.error("platform error:", platform, caller=self)
            e = Error("platform error")
            SingleTask.run(self._error_callback, e)
            SingleTask.run(self._init_callback, False)
            return
        self._t = T(**kwargs)

    @property
    def orders(self):
        return self._t.orders

    @property
    def position(self):
        return self._t.position  # only for contract trading.

    @property
    def rest_api(self):
        return self._t.rest_api

    async def create_order(self, action, price, quantity, *args, **kwargs) -> (str, Error):
        """Create an order.

        Args:
            action: Trade direction, `BUY` or `SELL`.
            price: Price of each order/contract.
            quantity: The buying or selling quantity.
            kwargs：
                order_type: Specific type of order, `LIMIT` or `MARKET`. (default is `LIMIT`)
                client_order_id: Client order id, default `None` will be replaced by a random uuid string.

        Returns:
            order_id: Order id if created successfully, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        price = tools.float_to_str(price)
        quantity = tools.float_to_str(quantity)
        if not kwargs.get("client_order_id"):
            kwargs["client_order_id"] = tools.get_uuid1().replace("-", "")
        order_id, error = await self._t.create_order(action, price, quantity, *args, **kwargs)
        return order_id, error

    async def revoke_order(self, *order_ids):
        """Revoke (an) order(s).

        Args:
            order_ids: Order id list, you can set this param to 0 or multiple items. If you set 0 param, you can cancel
                all orders for this symbol(initialized in Trade object). If you set 1 param, you can cancel an order.
                If you set multiple param, you can cancel multiple orders. Do not set param length more than 100.

        Returns:
            success: If execute successfully, return success information, otherwise it's None.
            error: If execute failed, return error information, otherwise it's None.
        """
        success, error = await self._t.revoke_order(*order_ids)
        return success, error

    async def get_open_order_ids(self) -> (list, Error):
        """Get open order id list.

        Args:
            None.

        Returns:
            order_ids: Open order id list, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        order_ids, error = await self._t.get_open_order_ids()
        return order_ids, error

    async def _on_order_update_callback(self, order: Order) -> None:
        """Order information update callback.

        Args:
            order: Order object.
        """
        if not self._order_update_callback:
            return
        await self._order_update_callback(order)

    async def _on_position_update_callback(self, position: Position) -> None:
        """Position information update callback.

        Args:
            position: Position object.
        """
        if not self._position_update_callback:
            return
        await self._position_update_callback(position)

    async def _on_init_callback(self, success: bool) -> None:
        """Callback function when initialize Trade module finished.

        Args:
            success: `True` if initialize Trade module success, otherwise `False`.
        """
        if not self._init_callback:
            return
        params = {
            "strategy": self._raw_params["strategy"],
            "platform": self._raw_params["platform"],
            "symbol": self._raw_params["symbol"],
            "account": self._raw_params["account"]
        }
        await self._init_callback(success, **params)

    async def _on_error_callback(self, error: Error) -> None:
        """Callback function when some error occur while Trade module is running.

        Args:
            error: Error information.
        """
        if not self._error_callback:
            return
        params = {
            "strategy": self._raw_params["strategy"],
            "platform": self._raw_params["platform"],
            "symbol": self._raw_params["symbol"],
            "account": self._raw_params["account"]
        }
        await self._error_callback(error, **params)
