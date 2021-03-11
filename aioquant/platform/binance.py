# -*- coding:utf-8 -*-

"""
Base on the public infos about aioquant project.

# 2021-03-11 add some functions and update some functions.
* The reason: https://binance-docs.github.io/apidocs/spot/cn/#185368440e

Reference:
* Binance API: https://binance-docs.github.io/apidocs/spot/cn/#185368440e
* Binance SPOT API on GitHub: https://github.com/binance/binance-spot-api-docs/blob/master/rest-api_CN.md
"""

import json
import copy
import hmac
import hashlib
from urllib.parse import urljoin

from aioquant.error import Error
from aioquant.utils import tools
from aioquant.utils import logger
from aioquant.order import Order
from aioquant.tasks import SingleTask, LoopRunTask
from aioquant.utils.decorator import async_method_locker
from aioquant.utils.web import Websocket, AsyncHttpRequests
from aioquant.order import ORDER_ACTION_SELL, ORDER_ACTION_BUY, ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET
from aioquant.order import ORDER_STATUS_SUBMITTED, ORDER_STATUS_PARTIAL_FILLED, ORDER_STATUS_FILLED, \
    ORDER_STATUS_CANCELED, ORDER_STATUS_FAILED


__all__ = ("BinanceRestAPI", "BinanceTrade", )


class BinanceRestAPI:
    """Binance REST API client.

    Attributes:
        host: HTTP request host.
        access_key: Account's ACCESS KEY.
        secret_key: Account's SECRET KEY.
    """

    def __init__(self, host, access_key, secret_key):
        """Initialize REST API client."""
        self._host = host
        self._access_key = access_key
        self._secret_key = secret_key

    async def get_user_account(self):
        """Get user account information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/account"
        ts = tools.get_cur_timestamp_ms()
        params = {
            "timestamp": str(ts)
        }
        success, error = await self.request("GET", uri, params, auth=True)
        return success, error

    async def get_server_time(self):
        """Get server time.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/time"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_exchange_info(self):
        """Get exchange information.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/exchangeInfo"
        success, error = await self.request("GET", uri)
        return success, error

    async def get_latest_ticker(self, symbol):
        """Get latest ticker.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/ticker/24hr"
        params = {
            "symbol": symbol
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_orderbook(self, symbol, limit: int=100):
        """Get orderbook.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            limit: Number of results per request. (default 100, max 5000. enum: 5, 10, 20, 50, 100, 500, 1000, 5000)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/depth"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def create_order(self, action, symbol, price, quantity, client_order_id=None):
        """Create an order.
        Args:
            action: Trade direction, `BUY` or `SELL`.
            symbol: Symbol name, e.g. `BTCUSDT`.
            price: Price of each contract.
            quantity: The buying or selling quantity.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        data = {
            "symbol": symbol,
            "side": action,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": price,
            "recvWindow": "5000",
            "newOrderRespType": "FULL",
            "timestamp": tools.get_cur_timestamp_ms()
        }
        if client_order_id:
            data["newClientOrderId"] = client_order_id
        success, error = await self.request("POST", uri, body=data, auth=True)
        return success, error

    async def revoke_order(self, symbol, order_id, client_order_id=None):
        """Cancelling an unfilled order.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            order_id: Order id.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        success, error = await self.request("DELETE", uri, params=params, auth=True)
        return success, error

    async def get_order_status(self, symbol, order_id, client_order_id):
        """Get order details by order id.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            order_id: Order id.
            client_order_id: Client order id.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": str(order_id),
            "origClientOrderId": client_order_id,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_all_orders(self, symbol):
        """Get all account orders; active, canceled, or filled.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/allOrders"
        params = {
            "symbol": symbol,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_open_orders(self, symbol):
        """Get all open order information.
        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/openOrders"
        params = {
            "symbol": symbol,
            "timestamp": tools.get_cur_timestamp_ms()
        }
        success, error = await self.request("GET", uri, params=params, auth=True)
        return success, error

    async def get_listen_key(self):
        """Get listen key, start a new user data stream.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/userDataStream"
        success, error = await self.request("POST", uri)
        return success, error

    async def put_listen_key(self, listen_key):
        """Keepalive a user data stream to prevent a time out.

        Args:
            listen_key: Listen key.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/userDataStream"
        params = {
            "listenKey": listen_key
        }
        success, error = await self.request("PUT", uri, params=params)
        return success, error

    async def delete_listen_key(self, listen_key):
        """Delete a listen key.

        Args:
            listen_key: Listen key.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v1/userDataStream"
        params = {
            "listenKey": listen_key
        }
        success, error = await self.request("DELETE", uri, params=params)
        return success, error

    async def get_klines(self, symbol: str, interval: str = "1m", start: int=0, end: int=0, limit: int=500):
        """Get Kline information.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            interval: Kline interval type, valid values: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            start: Start timestamp
            end: End timestamp
            limit: Number of results per request. (Default 500, max 1000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.

        Notes:
            If start and end time are not sent, the most recent klines are returned.
        """
        uri = "/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start and end:
            params["startTime"] = start
            params["endTime"] = end

        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def get_latest_trade(self, symbol: str, limit: int=500):
        """Get latest trade.

        Args:
            symbol: Symbol name, e.g. `BTCUSDT`.
            limit: Number of results per request. (Default 500, max 1000.)

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        uri = "/api/v3/trades"
        params = {
            "symbol": symbol,
            "limit": limit,
        }

        success, error = await self.request("GET", uri, params=params)
        return success, error

    async def request(self, method, uri, params=None, body=None, headers=None, auth=False):
        """Do HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `DELETE` / `PUT`.
            uri: HTTP request uri.
            params: HTTP query params.
            body:   HTTP request body.
            headers: HTTP request headers.
            auth: If this request requires authentication.

        Returns:
            success: Success results, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        url = urljoin(self._host, uri)
        data = {}
        if params:
            data.update(params)
        if body:
            data.update(body)

        if data:
            query = "&".join(["=".join([str(k), str(v)]) for k, v in data.items()])
        else:
            query = ""
        if auth and query:
            signature = hmac.new(self._secret_key.encode(), query.encode(), hashlib.sha256).hexdigest()
            query += "&signature={s}".format(s=signature)
        if query:
            url += ("?" + query)

        if not headers:
            headers = {}
        headers["X-MBX-APIKEY"] = self._access_key
        _, success, error = await AsyncHttpRequests.fetch(method, url, headers=headers, timeout=10, verify_ssl=False)
        return success, error


class BinanceTrade:
    """Binance Trade module. You can initialize trade object with some attributes in kwargs.

    Attributes:
        account: Account name for this trade exchange.
        strategy: What's name would you want to created for your strategy.
        symbol: Symbol name for your trade.
        host: HTTP request host. (default "https://api.binance.com")
        wss: Websocket address. (default "wss://stream.binance.com:9443")
        access_key: Account's ACCESS KEY.
        secret_key Account's SECRET KEY.
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
        """Initialize Trade module."""
        e = None
        if not kwargs.get("account"):
            e = Error("param account miss")
        if not kwargs.get("strategy"):
            e = Error("param strategy miss")
        if not kwargs.get("symbol"):
            e = Error("param symbol miss")
        if not kwargs.get("host"):
            kwargs["host"] = "https://api.binance.com"
        if not kwargs.get("wss"):
            kwargs["wss"] = "wss://stream.binance.com:9443"
        if not kwargs.get("access_key"):
            e = Error("param access_key miss")
        if not kwargs.get("secret_key"):
            e = Error("param secret_key miss")
        if e:
            logger.error(e, caller=self)
            SingleTask.run(kwargs["error_callback"], e)
            SingleTask.run(kwargs["init_callback"], False)

        self._account = kwargs["account"]
        self._strategy = kwargs["strategy"]
        self._platform = kwargs["platform"]
        self._symbol = kwargs["symbol"]
        self._host = kwargs["host"]
        self._wss = kwargs["wss"]
        self._access_key = kwargs["access_key"]
        self._secret_key = kwargs["secret_key"]
        self._order_update_callback = kwargs.get("order_update_callback")
        self._init_callback = kwargs.get("init_callback")
        self._error_callback = kwargs.get("error_callback")

        self._raw_symbol = self._symbol.replace("/", "")  # Row symbol name, same as Binance Exchange.
        self._listen_key = None  # Listen key for Websocket authentication.
        self._assets = {}  # Asset data. e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
        self._orders = {}  # Order data. e.g. {order_no: order, ... }

        # Initialize our REST API client.
        self._rest_api = BinanceRestAPI(self._host, self._access_key, self._secret_key)

        # Create a loop run task to reset listen key every 30 minutes.
        LoopRunTask.register(self._reset_listen_key, 60 * 30)

        # Create a coroutine to initialize Websocket connection.
        SingleTask.run(self._init_websocket)

        LoopRunTask.register(self._send_heartbeat_msg, 10)

    async def _send_heartbeat_msg(self, *args, **kwargs):
        await self._ws.ping()

    @property
    def assets(self):
        return copy.copy(self._assets)

    @property
    def orders(self):
        return copy.copy(self._orders)

    @property
    def rest_api(self):
        return self._rest_api

    async def _init_websocket(self):
        """Initialize Websocket connection.
        """
        # Get listen key first.
        success, error = await self._rest_api.get_listen_key()
        if error:
            e = Error("get listen key failed: {}".format(error))
            logger.error(e, caller=self)
            SingleTask.run(self._error_callback, e)
            SingleTask.run(self._init_callback, False)
            return
        self._listen_key = success["listenKey"]
        uri = "/ws/" + self._listen_key
        url = urljoin(self._wss, uri)
        self._ws = Websocket(url, self.connected_callback, process_callback=self.process)

    async def _reset_listen_key(self, *args, **kwargs):
        """Reset listen key."""
        if not self._listen_key:
            logger.error("listen key not initialized!", caller=self)
            return
        await self._rest_api.put_listen_key(self._listen_key)
        logger.info("reset listen key success!", caller=self)

    async def connected_callback(self):
        """After websocket connection created successfully, pull back all open order information."""
        logger.info("Websocket connection authorized successfully.", caller=self)
        order_infos, error = await self._rest_api.get_open_orders(self._raw_symbol)
        if error:
            e = Error("get open orders error: {}".format(error))
            SingleTask.run(self._error_callback, e)
            SingleTask.run(self._init_callback, False)
            return
        for order_info in order_infos:
            if order_info["status"] == "NEW":
                status = ORDER_STATUS_SUBMITTED
            elif order_info["status"] == "PARTIALLY_FILLED":
                status = ORDER_STATUS_PARTIAL_FILLED
            elif order_info["status"] == "FILLED":
                status = ORDER_STATUS_FILLED
            elif order_info["status"] == "CANCELED":
                status = ORDER_STATUS_CANCELED
            elif order_info["status"] == "REJECTED":
                status = ORDER_STATUS_FAILED
            elif order_info["status"] == "EXPIRED":
                status = ORDER_STATUS_FAILED
            else:
                logger.warn("unknown status:", order_info, caller=self)
                SingleTask.run(self._error_callback, "order status error.")
                continue

            order_id = str(order_info["orderId"])
            info = {
                "platform": self._platform,
                "account": self._account,
                "strategy": self._strategy,
                "order_id": order_id,
                "client_order_id": order_info["clientOrderId"],
                "action": ORDER_ACTION_BUY if order_info["side"] == "BUY" else ORDER_ACTION_SELL,
                "order_type": ORDER_TYPE_LIMIT if order_info["type"] == "LIMIT" else ORDER_TYPE_MARKET,
                "symbol": self._symbol,
                "price": order_info["price"],
                "quantity": order_info["origQty"],
                "remain": float(order_info["origQty"]) - float(order_info["executedQty"]),
                "status": status,
                "ctime": order_info["time"],
                "utime": order_info["updateTime"]
            }
            order = Order(**info)
            self._orders[order_id] = order
            SingleTask.run(self._order_update_callback, copy.copy(order))

        SingleTask.run(self._init_callback, True, None)

    async def create_order(self, action, price, quantity, *args, **kwargs):
        """Create an order.

        Args:
            action: Trade direction, `BUY` or `SELL`.
            price: Price of each order.
            quantity: The buying or selling quantity.

        Returns:
            order_id: Order id if created successfully, otherwise it's None.
            error: Error information, otherwise it's None.
        """
        client_order_id = kwargs["client_order_id"]
        result, error = await self._rest_api.create_order(action, self._raw_symbol, price, quantity, client_order_id)
        if error:
            SingleTask.run(self._error_callback, error)
            return None, error
        order_id = str(result["orderId"])
        return order_id, None

    async def revoke_order(self, *order_ids):
        """Revoke (an) order(s).

        Args:
            order_ids: Order id list, you can set this param to 0 or multiple items. If you set 0 param, you can cancel
                all orders for this symbol(initialized in Trade object). If you set 1 param, you can cancel an order.
                If you set multiple param, you can cancel multiple orders. Do not set param length more than 100.

        Returns:
            Success or error, see bellow.
        """
        # If len(order_nos) == 0, you will cancel all orders for this symbol(initialized in Trade object).
        if len(order_ids) == 0:
            order_infos, error = await self._rest_api.get_open_orders(self._raw_symbol)
            if error:
                SingleTask.run(self._error_callback, error)
                return False, error
            for order_info in order_infos:
                _, error = await self._rest_api.revoke_order(self._raw_symbol, order_info["orderId"])
                if error:
                    SingleTask.run(self._error_callback, error)
                    return False, error
            return True, None

        # If len(order_nos) == 1, you will cancel an order.
        if len(order_ids) == 1:
            success, error = await self._rest_api.revoke_order(self._raw_symbol, order_ids[0])
            if error:
                SingleTask.run(self._error_callback, error)
                return order_ids[0], error
            else:
                return order_ids[0], None

        # If len(order_nos) > 1, you will cancel multiple orders.
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
        """
        success, error = await self._rest_api.get_open_orders(self._raw_symbol)
        if error:
            SingleTask.run(self._error_callback, error)
            return None, error
        else:
            order_ids = []
            for order_info in success:
                order_id = str(order_info["orderId"])
                order_ids.append(order_id)
            return order_ids, None

    @async_method_locker("BinanceTrade.process.locker")
    async def process(self, msg):
        """Process message that received from Websocket connection.

        Args:
            msg: message received from Websocket connection.
        """
        logger.debug("msg:", json.dumps(msg), caller=self)
        e = msg.get("e")
        if e == "executionReport":  # Order update.
            if msg["s"] != self._raw_symbol:
                return
            order_id = str(msg["i"])
            if msg["X"] == "NEW":
                status = ORDER_STATUS_SUBMITTED
            elif msg["X"] == "PARTIALLY_FILLED":
                status = ORDER_STATUS_PARTIAL_FILLED
            elif msg["X"] == "FILLED":
                status = ORDER_STATUS_FILLED
            elif msg["X"] == "CANCELED":
                status = ORDER_STATUS_CANCELED
            elif msg["X"] == "REJECTED":
                status = ORDER_STATUS_FAILED
            elif msg["X"] == "EXPIRED":
                status = ORDER_STATUS_FAILED
            else:
                logger.warn("unknown status:", msg, caller=self)
                SingleTask.run(self._error_callback, "order status error.")
                return
            order = self._orders.get(order_id)
            if not order:
                info = {
                    "platform": self._platform,
                    "account": self._account,
                    "strategy": self._strategy,
                    "order_id": order_id,
                    "client_order_id": msg["c"],
                    "action": ORDER_ACTION_BUY if msg["S"] == "BUY" else ORDER_ACTION_SELL,
                    "order_type": ORDER_TYPE_LIMIT if msg["o"] == "LIMIT" else ORDER_TYPE_MARKET,
                    "symbol": self._symbol,
                    "price": msg["p"],
                    "quantity": msg["q"],
                    "ctime": msg["O"]
                }
                order = Order(**info)
                self._orders[order_id] = order
            order.remain = float(msg["q"]) - float(msg["z"])
            order.status = status
            order.utime = msg["T"]
            SingleTask.run(self._order_update_callback, copy.copy(order))

            if status in [ORDER_STATUS_FAILED, ORDER_STATUS_CANCELED, ORDER_STATUS_FILLED]:
                self._orders.pop(order_id)
