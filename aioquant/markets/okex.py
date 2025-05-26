# -*— coding:utf-8 -*-

"""
OKEx Market Server.
https://www.okex.com/docs/zh
"""

import zlib
import json
import copy

from aioquant import const
from aioquant.utils import tools
from aioquant.utils import logger
from aioquant.tasks import LoopRunTask
from aioquant.utils.web import Websocket
from aioquant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL
from aioquant.event import EventOrderbook, EventTrade, EventKline
from aioquant.market import Orderbook, Trade, Kline


class OKEx:
    """ OKEx Market Server.

    Attributes:
        kwargs:
            platform: Exchange platform name, must be `okex` or `okex_margin`.
            host: Exchange Websocket host address, default is `wss://real.okex.com:8443`.
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

        self._orderbooks = {}  # 订单薄数据 {"symbol": {"bids": {"price": quantity, ...}, "asks": {...}}}

        url = self._wss + "/ws/v3"
        self._ws = Websocket(url, connected_callback=self.connected_callback,
                             process_binary_callback=self.process_binary)
        # self._ws.initialize()
        LoopRunTask.register(self.send_heartbeat_msg, 5)

    async def connected_callback(self):
        """After create Websocket connection successfully, we will subscribing orderbook/trade/kline."""
        ches = []
        for ch in self._channels:
            if ch == "orderbook":
                for symbol in self._symbols:
                    ch = "spot/depth:{s}".format(s=symbol.replace("/", '-'))
                    ches.append(ch)
            elif ch == "trade":
                for symbol in self._symbols:
                    ch = "spot/trade:{s}".format(s=symbol.replace("/", '-'))
                    ches.append(ch)
            elif ch == "kline":
                for symbol in self._symbols:
                    ch = "spot/candle60s:{s}".format(s=symbol.replace("/", '-'))
                    ches.append(ch)
            else:
                logger.error("channel error! channel:", ch, caller=self)
        if ches:
            msg = {
                "op": "subscribe",
                "args": ches
            }
            await self._ws.send(msg)
            logger.info("subscribe orderbook/trade/kline success.", caller=self)

    async def send_heartbeat_msg(self, *args, **kwargs):
        data = "ping"
        if not self._ws:
            logger.error("Websocket connection not yeah!", caller=self)
            return
        await self._ws.send(data)

    async def process_binary(self, raw):
        """ Process binary message that received from Websocket connection.

        Args:
            raw: Raw message that received from Websocket connection.
        """
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        msg = decompress.decompress(raw)
        msg += decompress.flush()
        msg = msg.decode()
        # logger.debug("msg:", msg, caller=self)
        if msg == "pong":
            return
        msg = json.loads(msg)

        table = msg.get("table")
        if table == "spot/depth":
            if msg.get("action") == "partial":
                for d in msg["data"]:
                    await self.process_orderbook_partial(d)
            elif msg.get("action") == "update":
                for d in msg["data"]:
                    await self.deal_orderbook_update(d)
            else:
                logger.warn("unhandle msg:", msg, caller=self)
        elif table == "spot/trade":
            for d in msg["data"]:
                await self.process_trade(d)
        elif table == "spot/candle60s":
            for d in msg["data"]:
                await self.process_kline(d)

    async def process_orderbook_partial(self, data):
        """Process orderbook partical data."""
        symbol = data.get("instrument_id").replace("-", "/")
        if symbol not in self._symbols:
            return
        asks = data.get("asks")
        bids = data.get("bids")
        self._orderbooks[symbol] = {"asks": {}, "bids": {}, "timestamp": 0}
        for ask in asks:
            price = float(ask[0])
            quantity = float(ask[1])
            self._orderbooks[symbol]["asks"][price] = quantity
        for bid in bids:
            price = float(bid[0])
            quantity = float(bid[1])
            self._orderbooks[symbol]["bids"][price] = quantity
        timestamp = tools.utctime_str_to_mts(data.get("timestamp"))
        self._orderbooks[symbol]["timestamp"] = timestamp

    async def deal_orderbook_update(self, data):
        """Process orderbook update data."""
        symbol = data.get("instrument_id").replace("-", "/")
        asks = data.get("asks")
        bids = data.get("bids")
        timestamp = tools.utctime_str_to_mts(data.get("timestamp"))

        if symbol not in self._orderbooks:
            return
        self._orderbooks[symbol]["timestamp"] = timestamp

        for ask in asks:
            price = float(ask[0])
            quantity = float(ask[1])
            if quantity == 0 and price in self._orderbooks[symbol]["asks"]:
                self._orderbooks[symbol]["asks"].pop(price)
            else:
                self._orderbooks[symbol]["asks"][price] = quantity

        for bid in bids:
            price = float(bid[0])
            quantity = float(bid[1])
            if quantity == 0 and price in self._orderbooks[symbol]["bids"]:
                self._orderbooks[symbol]["bids"].pop(price)
            else:
                self._orderbooks[symbol]["bids"][price] = quantity

        await self.publish_orderbook(symbol)

    async def publish_orderbook(self, symbol):
        """Publish OrderbookEvent."""
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
            price = "%.8f" % k
            quantity = "%.8f" % ob["asks"].get(k)
            asks.append([price, quantity])

        bids = []
        for k in bid_keys[:self._orderbook_length]:
            price = "%.8f" % k
            quantity = "%.8f" % ob["bids"].get(k)
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
        """Process trade data and publish TradeEvent."""
        symbol = data.get("instrument_id").replace("-", "/")
        if symbol not in self._symbols:
            return
        action = ORDER_ACTION_BUY if data["side"] == "buy" else ORDER_ACTION_SELL
        price = "%.8f" % float(data["price"])
        quantity = "%.8f" % float(data["size"])
        timestamp = tools.utctime_str_to_mts(data["timestamp"])

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
        """Process kline data and publish KlineEvent."""
        symbol = data["instrument_id"].replace("-", "/")
        if symbol not in self._symbols:
            return
        timestamp = tools.utctime_str_to_mts(data["candle"][0])
        _open = "%.8f" % float(data["candle"][1])
        high = "%.8f" % float(data["candle"][2])
        low = "%.8f" % float(data["candle"][3])
        close = "%.8f" % float(data["candle"][4])
        volume = "%.8f" % float(data["candle"][5])

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
