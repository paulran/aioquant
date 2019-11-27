# -*— coding:utf-8 -*-

"""
Event Center.

Author: HuangTao
Date:   2018/05/04
Email:  huangtao@ifclover.com
"""

import json
import zlib
import asyncio

import aioamqp

from aioquant.utils import logger
from aioquant.configure import config
from aioquant.tasks import LoopRunTask, SingleTask
from aioquant.market import Orderbook, Trade, Kline
from aioquant.utils.decorator import async_method_locker


__all__ = ("EventCenter", "EventKline", "EventOrderbook", "EventTrade", )


class Event:
    """Event base.

    Attributes:
        name: Event name.
        exchange: Exchange name.
        queue: Queue name.
        routing_key: Routing key name.
        pre_fetch_count: How may message per fetched, default is `1`.
        data: Message content.
    """

    def __init__(self, name=None, exchange=None, queue=None, routing_key=None, pre_fetch_count=1, data=None):
        """Initialize."""
        self._name = name
        self._exchange = exchange
        self._queue = queue
        self._routing_key = routing_key
        self._pre_fetch_count = pre_fetch_count
        self._data = data
        self._callback = None  # Asynchronous callback function.

    @property
    def name(self):
        return self._name

    @property
    def exchange(self):
        return self._exchange

    @property
    def queue(self):
        return self._queue

    @property
    def routing_key(self):
        return self._routing_key

    @property
    def prefetch_count(self):
        return self._pre_fetch_count

    @property
    def data(self):
        return self._data

    def dumps(self):
        d = {
            "n": self.name,
            "d": self.data
        }
        s = json.dumps(d)
        b = zlib.compress(s.encode("utf8"))
        return b

    def loads(self, b):
        b = zlib.decompress(b)
        d = json.loads(b.decode("utf8"))
        self._name = d.get("n")
        self._data = d.get("d")
        return d

    def parse(self):
        raise NotImplemented

    def subscribe(self, callback, multi=False):
        """Subscribe a event.

        Args:
            callback: Asynchronous callback function.
            multi: If subscribe multiple channels?
        """
        from aioquant import quant
        self._callback = callback
        SingleTask.run(quant.event_center.subscribe, self, self.callback, multi)

    def publish(self):
        """Publish a event."""
        from aioquant import quant
        SingleTask.run(quant.event_center.publish, self)

    async def callback(self, channel, body, envelope, properties):
        self._exchange = envelope.exchange_name
        self._routing_key = envelope.routing_key
        self.loads(body)
        o = self.parse()
        await self._callback(o)

    def __str__(self):
        info = "EVENT: name={n}, exchange={e}, queue={q}, routing_key={r}, data={d}".format(
            e=self.exchange, q=self.queue, r=self.routing_key, n=self.name, d=self.data)
        return info

    def __repr__(self):
        return str(self)


class EventKline(Event):
    """Kline event.

    Attributes:
        kline: Kline object.

    * NOTE:
        Publisher: Market server.
        Subscriber: Any servers.
    """

    def __init__(self, kline: Kline):
        """Initialize."""
        name = "EVENT_KLINE"
        exchange = "Kline"
        routing_key = "{p}.{s}".format(p=kline.platform, s=kline.symbol)
        queue = "{sid}.{ex}.{rk}".format(sid=config.server_id, ex=exchange, rk=routing_key)
        super(EventKline, self).__init__(name, exchange, queue, routing_key, data=kline.smart)

    def parse(self):
        kline = Kline().load_smart(self.data)
        return kline


class EventOrderbook(Event):
    """Orderbook event.

    Attributes:
        orderbook: Orderbook object.

    * NOTE:
        Publisher: Market server.
        Subscriber: Any servers.
    """

    def __init__(self, orderbook: Orderbook):
        """Initialize."""
        name = "EVENT_ORDERBOOK"
        exchange = "Orderbook"
        routing_key = "{p}.{s}".format(p=orderbook.platform, s=orderbook.symbol)
        queue = "{sid}.{ex}.{rk}".format(sid=config.server_id, ex=exchange, rk=routing_key)
        super(EventOrderbook, self).__init__(name, exchange, queue, routing_key, data=orderbook.smart)

    def parse(self):
        orderbook = Orderbook().load_smart(self.data)
        return orderbook


class EventTrade(Event):
    """Trade event.

    Attributes:
        trade: Trade object.

    * NOTE:
        Publisher: Market server.
        Subscriber: Any servers.
    """

    def __init__(self, trade: Trade):
        """Initialize."""
        name = "EVENT_TRADE"
        exchange = "Trade"
        routing_key = "{p}.{s}".format(p=trade.platform, s=trade.symbol)
        queue = "{sid}.{ex}.{rk}".format(sid=config.server_id, ex=exchange, rk=routing_key)
        super(EventTrade, self).__init__(name, exchange, queue, routing_key, data=trade.smart)

    def parse(self):
        trade = Trade().load_smart(self.data)
        return trade


class EventCenter:
    """Event center.
    """

    def __init__(self):
        self._host = config.rabbitmq.get("host", "localhost")
        self._port = config.rabbitmq.get("port", 5672)
        self._username = config.rabbitmq.get("username", "guest")
        self._password = config.rabbitmq.get("password", "guest")
        self._protocol = None
        self._channel = None  # Connection channel.
        self._connected = False  # If connect success.
        self._subscribers = []  # e.g. `[(event, callback, multi), ...]`
        self._event_handler = {}  # e.g. `{"exchange:routing_key": [callback_function, ...]}`

        # Register a loop run task to check TCP connection's healthy.
        LoopRunTask.register(self._check_connection, 10)

        # Create MQ connection.
        asyncio.get_event_loop().run_until_complete(self.connect())

    @async_method_locker("EventCenter.subscribe")
    async def subscribe(self, event: Event, callback=None, multi=False):
        """Subscribe a event.

        Args:
            event: Event type.
            callback: Asynchronous callback.
            multi: If subscribe multiple channel(routing_key) ?
        """
        logger.info("NAME:", event.name, "EXCHANGE:", event.exchange, "QUEUE:", event.queue, "ROUTING_KEY:",
                    event.routing_key, caller=self)
        self._subscribers.append((event, callback, multi))

    async def publish(self, event):
        """Publish a event.

        Args:
            event: A event to publish.
        """
        if not self._connected:
            logger.warn("RabbitMQ not ready right now!", caller=self)
            return
        data = event.dumps()
        await self._channel.basic_publish(payload=data, exchange_name=event.exchange, routing_key=event.routing_key)

    async def connect(self, reconnect=False):
        """Connect to RabbitMQ server and create default exchange.

        Args:
            reconnect: If this invoke is a re-connection ?
        """
        logger.info("host:", self._host, "port:", self._port, caller=self)
        if self._connected:
            return

        # Create a connection.
        try:
            transport, protocol = await aioamqp.connect(host=self._host, port=self._port, login=self._username,
                                                        password=self._password, login_method="PLAIN")
        except Exception as e:
            logger.error("connection error:", e, caller=self)
            return
        finally:
            if self._connected:
                return
        channel = await protocol.channel()
        self._protocol = protocol
        self._channel = channel
        self._connected = True
        logger.info("Rabbitmq initialize success!", caller=self)

        # Create default exchanges.
        exchanges = ["Orderbook", "Kline", "Trade"]
        for name in exchanges:
            await self._channel.exchange_declare(exchange_name=name, type_name="topic")
        logger.debug("create default exchanges success!", caller=self)

        if reconnect:
            self._bind_and_consume()
        else:
            # Maybe we should waiting for all modules to be initialized successfully.
            asyncio.get_event_loop().call_later(5, self._bind_and_consume)

    def _bind_and_consume(self):
        async def do_them():
            for event, callback, multi in self._subscribers:
                await self._initialize(event, callback, multi)
        SingleTask.run(do_them)

    async def _initialize(self, event: Event, callback=None, multi=False):
        if event.queue:
            await self._channel.queue_declare(queue_name=event.queue, auto_delete=True)
            queue_name = event.queue
        else:
            result = await self._channel.queue_declare(exclusive=True)
            queue_name = result["queue"]
        await self._channel.queue_bind(queue_name=queue_name, exchange_name=event.exchange,
                                       routing_key=event.routing_key)
        await self._channel.basic_qos(prefetch_count=event.prefetch_count)
        if callback:
            if multi:
                await self._channel.basic_consume(callback=callback, queue_name=queue_name, no_ack=True)
                logger.info("multi message queue:", queue_name, caller=self)
            else:
                await self._channel.basic_consume(self._on_consume_event_msg, queue_name=queue_name)
                logger.info("queue:", queue_name, caller=self)
                self._add_event_handler(event, callback)

    async def _on_consume_event_msg(self, channel, body, envelope, properties):
        try:
            key = "{exchange}:{routing_key}".format(exchange=envelope.exchange_name, routing_key=envelope.routing_key)
            funcs = self._event_handler[key]
            for func in funcs:
                SingleTask.run(func, channel, body, envelope, properties)
        except:
            logger.error("event handle error! body:", body, caller=self)
            return
        finally:
            await self._channel.basic_client_ack(delivery_tag=envelope.delivery_tag)  # response ack

    def _add_event_handler(self, event: Event, callback):
        key = "{exchange}:{routing_key}".format(exchange=event.exchange, routing_key=event.routing_key)
        if key in self._event_handler:
            self._event_handler[key].append(callback)
        else:
            self._event_handler[key] = [callback]
        logger.debug("event handlers:", self._event_handler.keys(), caller=self)

    async def _check_connection(self, *args, **kwargs):
        if self._connected and self._channel and self._channel.is_open:
            return
        logger.error("CONNECTION LOSE! START RECONNECT RIGHT NOW!", caller=self)
        self._connected = False
        self._protocol = None
        self._channel = None
        self._event_handler = {}
        SingleTask.run(self.connect, reconnect=True)
