# -*- coding:utf-8 -*-

"""
OKEx Trade module.
https://www.okex.me/docs/zh/

Author: HuangTao
Date:   2019/01/19
Email:  huangtao@ifclover.com
"""

import time
import json
import copy
import hmac
import zlib
import base64
from urllib.parse import urljoin

from aioquant.error import Error
from aioquant.utils import tools
from aioquant.utils import logger
from aioquant.order import Order
from aioquant.tasks import SingleTask, LoopRunTask
from aioquant.utils.decorator import async_method_locker
from aioquant.utils.web import Websocket, AsyncHttpRequests
from aioquant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL
from aioquant.order import ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET
from aioquant.order import ORDER_STATUS_SUBMITTED, ORDER_STATUS_PARTIAL_FILLED, ORDER_STATUS_FILLED, \
    ORDER_STATUS_CANCELED, ORDER_STATUS_FAILED


__all__ = ("OKExRestAPI", "OKExTrade", )


class OKExRestAPI:
    """ OKEx REST API client.

    Attributes:
        host: HTTP request host.
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
        passphrase: API KEY Passphrase.
    """

    def __init__(self, host, access_key, secret_key, passphrase):
        """Initialize."""
        self._host = host
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase

    async def get_user_account(self):
        """Get account asset information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/accounts"
        result, error = await self.request("GET", uri, auth=True)
        return result, error

    async def create_order(self, action, symbol, price, quantity, order_type=ORDER_TYPE_LIMIT, client_oid=None):
        """Create an order.
        Args:
            action: Action type, `BUY` or `SELL`.
            symbol: Trading pair, e.g. `BTC-USDT`.
            price: Order price.
            quantity: Order quantity.
            order_type: Order type, `MARKET` or `LIMIT`.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/orders"
        data = {
            "side": "buy" if action == ORDER_ACTION_BUY else "sell",
            "instrument_id": symbol,
            "margin_trading": 1
        }
        if order_type == ORDER_TYPE_LIMIT:
            data["type"] = "limit"
            data["price"] = price
            data["size"] = quantity
        elif order_type == ORDER_TYPE_MARKET:
            data["type"] = "market"
            if action == ORDER_ACTION_BUY:
                data["notional"] = quantity  # buy price.
            else:
                data["size"] = quantity  # sell quantity.
        else:
            logger.error("order_type error! order_type:", order_type, caller=self)
            return None, "order type error!"
        if client_oid:
            data["client_oid"] = client_oid
        result, error = await self.request("POST", uri, body=data, auth=True)
        return result, error

    async def revoke_order(self, symbol, order_id=None, client_oid=None):
        """Cancelling an unfilled order.
        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_id: Order id, default is `None`.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_id` and `order_oid` must exist one, using order_id first.
        """
        if order_id:
            uri = "/api/spot/v3/cancel_orders/{order_id}".format(order_id=order_id)
        elif client_oid:
            uri = "/api/spot/v3/cancel_orders/{client_oid}".format(client_oid=client_oid)
        else:
            return None, "order id error!"
        data = {
            "instrument_id": symbol
        }
        result, error = await self.request("POST", uri, body=data, auth=True)
        if error:
            return order_id, error
        if result["result"]:
            return order_id, None
        return order_id, result

    async def revoke_orders(self, symbol, order_ids=None, client_oids=None):
        """Cancelling multiple open orders with order_id，Maximum 10 orders can be cancelled at a time for each
            trading pair.

        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_ids: Order id list, default is `None`.
            client_oids: Client order id list, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_ids` and `order_oids` must exist one, using order_ids first.
        """
        uri = "/api/spot/v3/cancel_batch_orders"
        if order_ids:
            if len(order_ids) > 10:
                logger.warn("only revoke 10 orders per request!", caller=self)
            body = [
                {
                    "instrument_id": symbol,
                    "order_ids": order_ids[:10]
                }
            ]
        elif client_oids:
            if len(client_oids) > 10:
                logger.warn("only revoke 10 orders per request!", caller=self)
            body = [
                {
                    "instrument_id": symbol,
                    "client_oids": client_oids[:10]
                }
            ]
        else:
            return None, "order id list error!"
        result, error = await self.request("POST", uri, body=body, auth=True)
        return result, error

    async def get_open_orders(self, symbol, limit=100):
        """Get order details by order id.

        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            limit: order count to return, max is 100, default is 100.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/spot/v3/orders_pending"
        params = {
            "instrument_id": symbol,
            "limit": limit
        }
        result, error = await self.request("GET", uri, params=params, auth=True)
        return result, error

    async def get_order_status(self, symbol, order_id=None, client_oid=None):
        """Get order status.
        Args:
            symbol: Trading pair, e.g. `BTC-USDT`.
            order_id: Order id.
            client_oid: Client order id, default is `None`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            `order_id` and `order_oid` must exist one, using order_id first.
        """
        if order_id:
            uri = "/api/spot/v3/orders/{order_id}".format(order_id=order_id)
        elif client_oid:
            uri = "/api/spot/v3/orders/{client_oid}".format(client_oid=client_oid)
        else:
            return None, "order id error!"
        params = {
            "instrument_id": symbol
        }
        result, error = await self.request("GET", uri, params=params, auth=True)
        return result, error

    async def request(self, method, uri, params=None, body=None, headers=None, auth=False):
        """Do HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `DELETE` / `PUT`.
            uri: HTTP request uri.
            params: HTTP query params.
            body: HTTP request body.
            headers: HTTP request headers.
            auth: If this request requires authentication.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        if params:
            query = "&".join(["{}={}".format(k, params[k]) for k in sorted(params.keys())])
            uri += "?" + query
        url = urljoin(self._host, uri)

        if auth:
            timestamp = str(time.time()).split(".")[0] + "." + str(time.time()).split(".")[1][:3]
            if body:
                body = json.dumps(body)
            else:
                body = ""
            message = str(timestamp) + str.upper(method) + uri + str(body)
            mac = hmac.new(bytes(self._secret_key, encoding="utf8"), bytes(message, encoding="utf-8"),
                           digestmod="sha256")
            d = mac.digest()
            sign = base64.b64encode(d)

            if not headers:
                headers = {}
            headers["Content-Type"] = "application/json"
            headers["OK-ACCESS-KEY"] = self._access_key.encode().decode()
            headers["OK-ACCESS-SIGN"] = sign.decode()
            headers["OK-ACCESS-TIMESTAMP"] = str(timestamp)
            headers["OK-ACCESS-PASSPHRASE"] = self._passphrase
        _, success, error = await AsyncHttpRequests.fetch(method, url, body=body, headers=headers, timeout=10)
        return success, error


class OKExTrade:
    """OKEx Trade module. You can initialize trade object with some attributes in kwargs.

    Attributes:
        account: Account name for this trade exchange.
        strategy: What's name would you want to created for your strategy.
        symbol: Symbol name for your trade.
        host: HTTP request host. (default "https://www.okex.com")
        wss: Websocket address. (default "wss://real.okex.com:8443")
        access_key: Account's ACCESS KEY.
        secret_key Account's SECRET KEY.
        passphrase API KEY Passphrase.
        order_update_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `order_update_callback` is like `async def on_order_update_callback(order: Order): pass` and this
            callback function will be executed asynchronous when some order state updated.
        init_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `init_callback` is like `async def on_init_callback(success: bool, **kwargs): pass`
            and this callback function will be executed asynchronous after Trade module object initialized done.
        error_callback: You can use this param to specify a async callback function when you initializing Trade
            module. `error_callback` is like `async def on_error_callback(error: Error, **kwargs): pass`
            and this callback function will be executed asynchronous when some error occur while trade module is running.
    """

    def __init__(self, **kwargs):
        """Initialize."""
        e = None
        if not kwargs.get("account"):
            e = Error("param account miss")
        if not kwargs.get("strategy"):
            e = Error("param strategy miss")
        if not kwargs.get("symbol"):
            e = Error("param symbol miss")
        if not kwargs.get("host"):
            kwargs["host"] = "https://www.okex.com"
        if not kwargs.get("wss"):
            kwargs["wss"] = "wss://real.okex.com:8443"
        if not kwargs.get("access_key"):
            e = Error("param access_key miss")
        if not kwargs.get("secret_key"):
            e = Error("param secret_key miss")
        if not kwargs.get("passphrase"):
            e = Error("param passphrase miss")
        if e:
            logger.error(e, caller=self)
            SingleTask.run(kwargs["error_callback"], e)
            SingleTask.run(kwargs["init_callback"], False)
            return

        self._account = kwargs["account"]
        self._strategy = kwargs["strategy"]
        self._platform = kwargs["platform"]
        self._symbol = kwargs["symbol"]
        self._host = kwargs["host"]
        self._wss = kwargs["wss"]
        self._access_key = kwargs["access_key"]
        self._secret_key = kwargs["secret_key"]
        self._passphrase = kwargs["passphrase"]
        self._order_update_callback = kwargs.get("order_update_callback")
        self._init_callback = kwargs.get("init_callback")
        self._error_callback = kwargs.get("error_callback")

        self._raw_symbol = self._symbol.replace("/", "-")
        self._order_channel = "spot/order:{symbol}".format(symbol=self._raw_symbol)

        url = self._wss + "/ws/v3"
        self._ws = Websocket(url, self.connected_callback, process_binary_callback=self.process_binary)

        self._assets = {}  # Asset object. e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
        self._orders = {}  # Order objects. e.g. {"order_id": Order, ... }

        # Initializing our REST API client.
        self._rest_api = OKExRestAPI(self._host, self._access_key, self._secret_key, self._passphrase)

        # Create a loop run task to send ping message to server per 5 seconds.
        LoopRunTask.register(self._send_heartbeat_msg, 5)

    @property
    def assets(self):
        return copy.copy(self._assets)

    @property
    def orders(self):
        return copy.copy(self._orders)

    @property
    def rest_api(self):
        return self._rest_api

    async def connected_callback(self):
        """After websocket connection created successfully, we will send a message to server for authentication."""
        timestamp = str(time.time()).split(".")[0] + "." + str(time.time()).split(".")[1][:3]
        message = str(timestamp) + "GET" + "/users/self/verify"
        mac = hmac.new(bytes(self._secret_key, encoding="utf8"), bytes(message, encoding="utf8"), digestmod="sha256")
        d = mac.digest()
        signature = base64.b64encode(d).decode()
        data = {
            "op": "login",
            "args": [self._access_key, self._passphrase, timestamp, signature]
        }
        await self._ws.send(data)

    async def _send_heartbeat_msg(self, *args, **kwargs):
        """Send ping to server."""
        hb = "ping"
        await self._ws.send(hb)

    @async_method_locker("OKExTrade.process_binary.locker")
    async def process_binary(self, raw):
        """Process binary message that received from websocket.

        Args:
            raw: Binary message received from websocket.

        Returns:
            None.
        """
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        msg = decompress.decompress(raw)
        msg += decompress.flush()
        msg = msg.decode()
        if msg == "pong":
            return
        logger.debug("msg:", msg, caller=self)
        msg = json.loads(msg)

        # Authorization message received.
        if msg.get("event") == "login":
            if not msg.get("success"):
                e = Error("Websocket connection authorized failed: {}".format(msg))
                logger.error(e, caller=self)
                SingleTask.run(self._error_callback, e)
                SingleTask.run(self._init_callback, False)
                return
            logger.info("Websocket connection authorized successfully.", caller=self)

            # Fetch orders from server. (open + partially filled)
            order_infos, error = await self._rest_api.get_open_orders(self._raw_symbol)
            if error:
                e = Error("get open orders error: {}".format(msg))
                SingleTask.run(self._error_callback, e)
                SingleTask.run(self._init_callback, False)
                return
            if len(order_infos) > 100:
                logger.warn("order length too long! (more than 100)", caller=self)
            for order_info in order_infos:
                order_info["ctime"] = order_info["created_at"]
                order_info["utime"] = order_info["timestamp"]
                self._update_order(order_info)

            # Subscribe order channel.
            data = {
                "op": "subscribe",
                "args": [self._order_channel]
            }
            await self._ws.send(data)
            return

        # Subscribe response message received.
        if msg.get("event") == "subscribe":
            if msg.get("channel") == self._order_channel:
                SingleTask.run(self._init_callback, True)
            else:
                e = Error("subscribe order event error: {}".format(msg))
                SingleTask.run(self._error_callback, e)
                SingleTask.run(self._init_callback, False)
            return

        # Order update message received.
        if msg.get("table") == "spot/order":
            for data in msg["data"]:
                data["ctime"] = data["timestamp"]
                data["utime"] = data["last_fill_time"]
                self._update_order(data)

    async def create_order(self, action, price, quantity, *args, **kwargs):
        """ Create an order.

        Args:
            action: Trade direction, `BUY` or `SELL`.
            price: Price of each order.
            quantity: The buying or selling quantity.

        Returns:
            order_id: Order id if created successfully, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        order_type = kwargs.get("order_type", ORDER_TYPE_LIMIT)
        client_order_id = kwargs.get("client_order_id")
        result, error = await self._rest_api.create_order(action, self._raw_symbol, price, quantity, order_type,
                                                          client_order_id)
        if error:
            SingleTask.run(self._error_callback, error)
            return None, error
        if not result["result"]:
            SingleTask.run(self._error_callback, result)
            return None, result
        return result["order_id"], None

    async def revoke_order(self, *order_ids):
        """Revoke (an) order(s).

        Args:
            order_ids: Order id list, you can set this param to 0 or multiple items. If you set 0 param, you can cancel
                all orders for this symbol(initialized in Trade object). If you set 1 param, you can cancel an order.
                If you set multiple param, you can cancel multiple orders. Do not set param length more than 100.

        Returns:
            Success or error, see bellow.

        NOTEs:
            DO NOT INPUT MORE THAT 10 ORDER IDs, you can invoke many times.
        """
        # If len(order_ids) == 0, you will cancel all orders for this symbol(initialized in Trade object).
        if len(order_ids) == 0:
            order_infos, error = await self._rest_api.get_open_orders(self._raw_symbol)
            if error:
                SingleTask.run(self._error_callback, error)
                return False, error
            if len(order_infos) > 100:
                logger.warn("order length too long! (more than 100)", caller=self)
            for order_info in order_infos:
                order_id = order_info["order_id"]
                _, error = await self._rest_api.revoke_order(self._raw_symbol, order_id)
                if error:
                    SingleTask.run(self._error_callback, error)
                    return False, error
            return True, None

        # If len(order_ids) == 1, you will cancel an order.
        if len(order_ids) == 1:
            success, error = await self._rest_api.revoke_order(self._raw_symbol, order_ids[0])
            if error:
                SingleTask.run(self._error_callback, error)
                return order_ids[0], error
            else:
                return order_ids[0], None

        # If len(order_ids) > 1, you will cancel multiple orders.
        if len(order_ids) > 1:
            success, error = [], []
            for order_id in order_ids:
                _, e = await self._rest_api.revoke_order(self._raw_symbol, order_id)
                if e:
                    SingleTask.run(self._error_callback, e)
                    error.append((order_id, e))
                else:
                    success.append(order_id)
            return success, error

    async def get_open_order_ids(self):
        """Get open order id list.

        Args:
            None.

        Returns:
            order_ids: Open order id list, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        success, error = await self._rest_api.get_open_orders(self._raw_symbol)
        if error:
            SingleTask.run(self._error_callback, error)
            return None, error
        else:
            if len(success) > 100:
                logger.warn("order length too long! (more than 100)", caller=self)
            order_ids = []
            for order_info in success:
                order_ids.append(order_info["order_id"])
            return order_ids, None

    def _update_order(self, order_info):
        """ Order update.

        Args:
            order_info: Order information.

        Returns:
            None.
        """
        order_id = str(order_info["order_id"])
        state = order_info["state"]
        remain = float(order_info["size"]) - float(order_info["filled_size"])
        ctime = tools.utctime_str_to_ms(order_info["ctime"])
        utime = tools.utctime_str_to_ms(order_info["utime"])

        if state == "-2":
            status = ORDER_STATUS_FAILED
        elif state == "-1":
            status = ORDER_STATUS_CANCELED
        elif state == "0":
            status = ORDER_STATUS_SUBMITTED
        elif state == "1":
            status = ORDER_STATUS_PARTIAL_FILLED
        elif state == "2":
            status = ORDER_STATUS_FILLED
        else:
            logger.error("status error! order_info:", order_info, caller=self)
            SingleTask.run(self._error_callback, "order status error.")
            return None

        order = self._orders.get(order_id)
        if not order:
            info = {
                "platform": self._platform,
                "account": self._account,
                "strategy": self._strategy,
                "order_id": order_id,
                "client_order_id": order_info["client_oid"],
                "action": ORDER_ACTION_BUY if order_info["side"] == "buy" else ORDER_ACTION_SELL,
                "symbol": self._symbol,
                "price": order_info["price"],
                "quantity": order_info["size"]
            }
            order = Order(**info)
            self._orders[order_id] = order
        order.remain = remain
        order.status = status
        order.ctime = ctime
        order.utime = utime

        SingleTask.run(self._order_update_callback, copy.copy(order))

        if status in [ORDER_STATUS_FAILED, ORDER_STATUS_CANCELED, ORDER_STATUS_FILLED]:
            self._orders.pop(order_id)
