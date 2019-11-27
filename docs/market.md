## 行情

通过行情模块(market)，可以订阅任意交易所的任意交易对的实时行情，包括订单薄(Orderbook)、K线(KLine)、成交(Trade)，
根据不同交易所提供的行情信息，实时将行情信息推送给策略；

在订阅行情之前，需要先部署 [Market 行情服务器](https://github.com/TheNextQuant/Market)，行情服务器将通过 REST API 或 Websocket 的方式从交易所获取实时行情信息，
并将行情信息按照统一的数据格式打包，通过事件的形式发布至事件中心；


### 1. 行情模块使用

> 此处以订单薄使用为例，订阅Binance的 `ETH/BTC` 交易对订单薄数据
```python
# 导入模块
from aioquant import const
from aioquant.utils import logger
from aioquant.market import Market, Orderbook


# 订阅订单薄行情，注意此处注册的回调函数是 `async` 异步函数，回调参数为 `orderbook` 对象，数据结构查看下边的介绍。
async def on_event_orderbook_update(orderbook: Orderbook):
    logger.info("orderbook:", orderbook)
    logger.info("platform:", orderbook.platform)  # 打印行情平台
    logger.info("symbol:", orderbook.symbol)  # 打印行情交易对
    logger.info("asks:", orderbook.asks)  # 打印卖盘数据
    logger.info("bids:", orderbook.bids)  # 打印买盘数据 
    logger.info("timestamp:", orderbook.timestamp)  # 打印行情更新时间戳(毫秒)
    

Market(const.MARKET_TYPE_ORDERBOOK, const.BINANCE, "ETH/BTC", on_event_orderbook_update)
```

> 使用同样的方式，可以订阅任意的行情
```python
from aioquant import const

const.MARKET_TYPE_ORDERBOOK  # 订单薄(Orderbook)
const.MARKET_TYPE_KLINE  # 1分钟K线(KLine)
const.MARKET_TYPE_KLINE_5M  # 5分钟K线(KLine)
const.MARKET_TYPE_KLINE_15M  # 15分钟K线(KLine)
const.MARKET_TYPE_TRADE  # 成交(Trade)
```


### 2. 行情对象数据结构

所有交易平台的行情，全部使用统一的数据结构；

#### 2.1 订单薄(Orderbook)

- 订单薄模块
```python
from aioquant.market import Orderbook

Orderbook.platform  # 订单薄平台
Orderbook.symbol  # 订单薄交易对
Orderbook.asks  # 订单薄买盘数据
Orderbook.bids  # 订单薄买盘数据
Orderbook.timestamp  # 订单薄更新时间戳(毫秒)
Orderbook.data  # 订单薄数据
```

- 订单薄数据结构
```json
{
    "platform": "binance",
    "symbol": "ETH/USDT",
    "asks": [
        ["8680.70000000", "0.00200000"]
    ],
    "bids": [
        ["8680.60000000", "2.82696138"]
    ],
    "timestamp": 1558949307370
}
```

- 字段说明
    - platform `string` 交易平台
    - symbol `string` 交易对
    - asks `list` 卖盘，一般默认前10档数据，一般 `price 价格` 和 `quantity 数量` 的精度为小数点后8位 `[[price, quantity], ...]`
    - bids `list` 买盘，一般默认前10档数据，一般 `price 价格` 和 `quantity 数量` 的精度为小数点后8位 `[[price, quantity], ...]`
    - timestamp `int` 时间戳(毫秒)


#### 2.2 K线(KLine)

- K线模块
```python
from aioquant.market import Kline

Kline.platform  # 交易平台
Kline.symbol  # 交易对
Kline.open  # 开盘价
Kline.high  # 最高价
Kline.low  # 最低价
Kline.close  # 收盘价
Kline.volume  # 成交量
Kline.timestamp  # 时间戳(毫秒)
Kline.data  # K线数据
```

- K线数据结构
```json
{
    "platform": "okex",
    "symbol": "BTC/USDT",
    "open": "8665.50000000",
    "high": "8668.40000000",
    "low": "8660.00000000",
    "close": "8660.00000000",
    "volume": "73.14728136",
    "timestamp": 1558946340000
}
```

- 字段说明
    - platform `string` 交易平台
    - symbol `string` 交易对
    - open `string` 开盘价，一般精度为小数点后8位
    - high `string` 最高价，一般精度为小数点后8位
    - low `string` 最低价，一般精度为小数点后8位
    - close `string` 收盘价，一般精度为小数点后8位
    - volume `string` 成交量，一般精度为小数点后8位
    - timestamp `int` 时间戳(毫秒)


#### 2.3 成交(Trade)

- 成交模块
```python
from aioquant.market import Trade

Trade.platform  # 交易平台
Trade.symbol  # 交易对
Trade.action  # 操作类型 BUY 买入 / SELL 卖出
Trade.price  # 价格
Trade.quantity  # 数量
Trade.timestamp  # 时间戳(毫秒)
```

- 成交数据结构
```json
{
    "platform": "okex", 
    "symbol": "BTC/USDT", 
    "action": "SELL", 
    "price": "8686.40000000", 
    "quantity": "0.00200000", 
    "timestamp": 1558949571111,
}
```

- 字段说明
    - platform `string` 交易平台
    - symbol `string` 交易对
    - action `string` 操作类型 BUY 买入 / SELL 卖出
    - price `string` 价格，一般精度为小数点后8位
    - quantity `string` 数量，一般精度为小数点后8位
    - timestamp `int` 时间戳(毫秒)
