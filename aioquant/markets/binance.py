# -*— coding:utf-8 -*-

"""
Binance Market Server.
https://github.com/binance-exchange/binance-official-api-docs/blob/master/web-socket-streams.md
"""

from aioquant import const
from aioquant.utils import tools
from aioquant.utils import logger
from aioquant.utils.web import Websocket
from aioquant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL
from aioquant.event import EventTrade, EventKline, EventOrderbook
from aioquant.market import Orderbook, Trade, Kline

class Binance:
    """ Binance Market Server.

    Attributes:
        kwargs:
            platform: Exchange platform name, must be `binance`.
            wss: Exchange Websocket host address, default is `wss://stream.binance.com:9443`.
            symbols: Symbol list.
            channels: Channel list, only `orderbook` / `trade` / `kline` to be enabled.
            orderbook_length: The length of orderbook's data to be published via OrderbookEvent, default is 10.
    """

    def __init__(self, **kwargs):
        self._platform = kwargs["platform"]
        self._wss = kwargs.get("wss", "wss://stream.binance.com:9443")
        self._symbols = list(set(kwargs.get("symbols")))
        self._channels = kwargs.get("channels")
        self._orderbook_length = kwargs.get("orderbook_length", 10)

        self._c_to_s = {}
        self._tickers = {}

        url = self._make_url()
        self._ws = Websocket(url, process_callback=self.process)
        # self._ws.initialize()

    def _make_url(self):
        """Generate request url.
        """
        cc = []
        for ch in self._channels:
            if ch == "kline":
                for symbol in self._symbols:
                    c = self._symbol_to_channel(symbol, "kline_1m")
                    cc.append(c)
            elif ch == "orderbook":
                for symbol in self._symbols:
                    c = self._symbol_to_channel(symbol, "depth20")
                    cc.append(c)
            elif ch == "trade":
                for symbol in self._symbols:
                    c = self._symbol_to_channel(symbol, "trade")
                    cc.append(c)
            else:
                logger.error("channel error! channel:", ch, caller=self)
        url = self._wss + "/stream?streams=" + "/".join(cc)
        return url

    async def process(self, msg):
        """Process message that received from Websocket connection.

        Args:
            msg: Message received from Websocket connection.
        """
        # logger.debug("msg:", msg, caller=self)
        if not isinstance(msg, dict):
            return

        channel = msg.get("stream")
        if channel not in self._c_to_s:
            logger.warn("unkown channel, msg:", msg, caller=self)
            return

        symbol = self._c_to_s[channel]
        data = msg.get("data")
        e = data.get("e")

        if e == "kline":
            await self.process_kline(symbol, data)
        elif channel.endswith("depth20"):
            await self.process_orderbook(symbol, data)
        elif e == "trade":
            await self.process_trade(symbol, data)

    async def process_kline(self, symbol, data):
        """Process kline data and publish KlineEvent."""
        kline = Kline(
            platform = self._platform,
            symbol = symbol,
            open = data.get("k").get("o"),
            high = data.get("k").get("h"),
            low = data.get("k").get("l"),
            close = data.get("k").get("c"),
            volume = data.get("k").get("q"),
            timestamp = data.get("k").get("t"),
            kline_type = const.MARKET_TYPE_KLINE
        )
        EventKline(kline).publish()
        logger.info("symbol:", symbol, "kline:", kline, caller=self)

    async def process_orderbook(self, symbol, data):
        """Process orderbook data and publish OrderbookEvent."""
        bids = []
        asks = []
        for bid in data.get("bids")[:self._orderbook_length]:
            bids.append(bid[:2])
        for ask in data.get("asks")[:self._orderbook_length]:
            asks.append(ask[:2])
        orderbook = Orderbook(
            platform = self._platform,
            symbol = symbol,
            asks = asks,
            bids = bids,
            timestamp = tools.get_cur_timestamp_ms()
        )
        EventOrderbook(orderbook).publish()
        logger.info("symbol:", symbol, "orderbook:", orderbook, caller=self)

    async def process_trade(self, symbol, data):
        """Process trade data and publish TradeEvent."""
        trade = Trade(
            platform = self._platform,
            symbol = symbol,
            action = ORDER_ACTION_SELL if data["m"] else ORDER_ACTION_BUY,
            price = data.get("p"),
            quantity = data.get("q"),
            timestamp = data.get("T")
        )
        EventTrade(trade).publish()
        logger.info("symbol:", symbol, "trade:", trade, caller=self)

    def _symbol_to_channel(self, symbol, channel_type="ticker"):
        channel = "{x}@{y}".format(x=symbol.replace("/", "").lower(), y=channel_type)
        self._c_to_s[channel] = symbol
        return channel
