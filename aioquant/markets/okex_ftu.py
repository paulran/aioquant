# -*— coding:utf-8 -*-

"""
OKEx Future Market Server.
https://www.okex.com/docs/zh/#futures_ws-all
"""

import zlib
import json
import copy

from aioquant import const
from aioquant.utils import tools
from aioquant.utils import logger
from aioquant.tasks import LoopRunTask
from aioquant.utils.web import Websocket
from aioquant.utils.decorator import async_method_locker
from aioquant.event import EventOrderbook, EventKline, EventTrade
from aioquant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL
from aioquant.market import Orderbook, Trade, Kline


class OKExFuture:
    """ OKEx Future Market Server.

    Attributes:
        kwargs:
            platform: Exchange platform name, must be `okex_future` or `okex_swap`.
            wss: Exchange Websocket host address, default is "wss://real.okex.com:8443".
            symbols: symbol list, OKEx Future instrument_id list.
            channels: channel list, only `orderbook`, `kline` and `trade` to be enabled.
            orderbook_length: The length of orderbook's data to be published via OrderbookEvent, default is 10.
    """

    def __init__(self, **kwargs):
        self._platform = kwargs["platform"]
        self._wss = kwargs.get("wss", "wss://real.okex.com:8443")
        self._symbols = list(set(kwargs.get("symbols")))
        self._channels = kwargs.get("channels")
        self._orderbook_length = kwargs.get("orderbook_length", 10)

        self._orderbooks = {}  # orderbook data, e.g. {"symbol": {"bids": {"price": quantity, ...}, "asks": {...}}}

        url = self._wss + "/ws/v3"
        self._ws = Websocket(url, connected_callback=self.connected_callback,
                             process_binary_callback=self.process_binary)
        self._ws.initialize()
        LoopRunTask.register(self.send_heartbeat_msg, 5)

    async def connected_callback(self):
        """After create connection to Websocket server successfully, we will subscribe orderbook/kline/trade event."""
        ches = []
        for ch in self._channels:
            if ch == "orderbook":
                for symbol in self._symbols:
                    if self._platform == const.OKEX_FUTURE:
                        ch = "futures/depth:{s}".format(s=symbol)
                    else:
                        ch = "swap/depth:{s}".format(s=symbol)
                    ches.append(ch)
            elif ch == "trade":
                for symbol in self._symbols:
                    if self._platform == const.OKEX_FUTURE:
                        ch = "futures/trade:{s}".format(s=symbol.replace("/", '-'))
                    else:
                        ch = "swap/trade:{s}".format(s=symbol.replace("/", '-'))
                    ches.append(ch)
            elif ch == "kline":
                for symbol in self._symbols:
                    if self._platform == const.OKEX_FUTURE:
                        ch = "futures/candle60s:{s}".format(s=symbol.replace("/", '-'))
                    else:
                        ch = "swap/candle60s:{s}".format(s=symbol.replace("/", '-'))
                    ches.append(ch)
            else:
                logger.error("channel error! channel:", ch, caller=self)
            if len(ches) > 0:
                msg = {
                    "op": "subscribe",
                    "args": ches
                }
                await self._ws.send(msg)
                logger.info("subscribe orderbook/kline/trade success.", caller=self)

    async def send_heartbeat_msg(self, *args, **kwargs):
        data = "ping"
        if not self._ws:
            logger.error("Websocket connection not yeah!", caller=self)
            return
        await self._ws.send(data)

    async def process_binary(self, raw):
        """ Process message that received from Websocket connection.

        Args:
            raw: Raw binary message received from Websocket connection.
        """
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        msg = decompress.decompress(raw)
        msg += decompress.flush()
        msg = msg.decode()
        if msg == "pong":  # Heartbeat message.
            return
        msg = json.loads(msg)
        # logger.debug("msg:", msg, caller=self)

        table = msg.get("table")
        if table in ["futures/depth", "swap/depth"]:
            if msg.get("action") == "partial":
                for d in msg["data"]:
                    await self.process_orderbook_partial(d)
            elif msg.get("action") == "update":
                for d in msg["data"]:
                    await self.process_orderbook_update(d)
        elif table in ["futures/trade", "swap/trade"]:
            for d in msg["data"]:
                await self.process_trade(d)
        elif table in ["futures/candle60s", "swap/candle60s"]:
            for d in msg["data"]:
                await self.process_kline(d)

    @async_method_locker("OKExFuture.orderbook_partial")
    async def process_orderbook_partial(self, data):
        """Deal with orderbook partial message."""
        symbol = data.get("instrument_id")
        if symbol not in self._symbols:
            return
        asks = data.get("asks")
        bids = data.get("bids")
        self._orderbooks[symbol] = {"asks": {}, "bids": {}, "timestamp": 0}
        for ask in asks:
            price = float(ask[0])
            quantity = int(ask[1])
            self._orderbooks[symbol]["asks"][price] = quantity
        for bid in bids:
            price = float(bid[0])
            quantity = int(bid[1])
            self._orderbooks[symbol]["bids"][price] = quantity
        timestamp = tools.utctime_str_to_mts(data.get("timestamp"))
        self._orderbooks[symbol]["timestamp"] = timestamp

    @async_method_locker("OKExFuture.orderbook_update")
    async def process_orderbook_update(self, data):
        """Deal with orderbook update message."""
        symbol = data.get("instrument_id")
        asks = data.get("asks")
        bids = data.get("bids")
        timestamp = tools.utctime_str_to_mts(data.get("timestamp"))

        if symbol not in self._orderbooks:
            return
        self._orderbooks[symbol]["timestamp"] = timestamp

        for ask in asks:
            price = float(ask[0])
            quantity = int(ask[1])
            if quantity == 0 and price in self._orderbooks[symbol]["asks"]:
                self._orderbooks[symbol]["asks"].pop(price)
            else:
                self._orderbooks[symbol]["asks"][price] = quantity

        for bid in bids:
            price = float(bid[0])
            quantity = int(bid[1])
            if quantity == 0 and price in self._orderbooks[symbol]["bids"]:
                self._orderbooks[symbol]["bids"].pop(price)
            else:
                self._orderbooks[symbol]["bids"][price] = quantity

        await self.publish_orderbook(symbol)

    async def publish_orderbook(self, symbol):
        """Publish orderbook message to EventCenter via OrderbookEvent."""
        ob = copy.copy(self._orderbooks[symbol])
        if not ob["asks"] or not ob["bids"]:
            logger.warn("symbol:", symbol, "asks:", ob["asks"], "bids:", ob["bids"], caller=self)
            return

        ask_keys = sorted(list(ob["asks"].keys()))
        bid_keys = sorted(list(ob["bids"].keys()), reverse=True)
        if ask_keys[0] <= bid_keys[0]:
            logger.warn("symbol:", symbol, "ask1:", ask_keys[0], "bid1:", bid_keys[0], caller=self)
            return

        asks = []
        for k in ask_keys[:self._orderbook_length]:
            price = "%.5f" % k
            quantity = str(ob["asks"].get(k))
            asks.append([price, quantity])

        bids = []
        for k in bid_keys[:self._orderbook_length]:
            price = "%.5f" % k
            quantity = str(ob["bids"].get(k))
            bids.append([price, quantity])

        orderbook = Orderbook(
            platform = self._platform,
            symbol = symbol,
            asks = asks,
            bids = bids,
            timestamp = ob["timestamp"]
        )
        EventOrderbook(orderbook).publish()
        logger.debug("symbol:", symbol, "orderbook:", orderbook, caller=self)

    async def process_trade(self, data):
        """Deal with trade data, and publish trade message to EventCenter via TradeEvent."""
        symbol = data["instrument_id"]
        if symbol not in self._symbols:
            return
        action = ORDER_ACTION_BUY if data["side"] == "buy" else ORDER_ACTION_SELL
        price = "%.5f" % float(data["price"])
        if self._platform == const.OKEX_FUTURE:
            quantity = str(data["qty"])
        else:
            quantity = str(data["size"])
        timestamp = tools.utctime_str_to_mts(data["timestamp"])

        # Publish EventTrade.
        trade = Trade(
            platform = self._platform,
            symbol = symbol,
            action = action,
            price = price,
            quantity = quantity,
            timestamp = timestamp
        )
        EventTrade(trade).publish()
        logger.debug("symbol:", symbol, "trade:", trade, caller=self)

    async def process_kline(self, data):
        """ Deal with 1min kline data, and publish kline message to EventCenter via KlineEvent.

        Args:
            data: Newest kline data.
        """
        symbol = data["instrument_id"]
        if symbol not in self._symbols:
            return
        timestamp = tools.utctime_str_to_mts(data["candle"][0])
        _open = "%.5f" % float(data["candle"][1])
        high = "%.5f" % float(data["candle"][2])
        low = "%.5f" % float(data["candle"][3])
        close = "%.5f" % float(data["candle"][4])
        volume = str(data["candle"][5])

        # Publish EventKline
        kline = Kline(
            platform = self._platform,
            symbol = symbol,
            open = _open,
            high = high,
            low = low,
            close = close,
            volume = volume,
            timestamp = timestamp,
            kline_type = const.MARKET_TYPE_KLINE
        )
        EventKline(kline).publish()
        logger.debug("symbol:", symbol, "kline:", kline, caller=self)
