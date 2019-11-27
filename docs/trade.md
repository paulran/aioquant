## 交易

通过交易模块(trade)，可以在任意交易平台发起交易，包括下单(create_order)、撤单(revoke_order)、查询订单状态(order status)、
查询未完全成交订单(get_open_order_ids)等功能；

策略完成下单之后，底层框架将定时或实时将最新的订单状态更新通过策略注册的回调函数传递给策略，策略能够在第一时间感知到订单状态更新数据；


### 1. 交易模块使用

#### 1.1 简单使用示例

> 此处以在 `Binance` 交易所上的 `ETH/BTC` 交易对创建一个买单为例：

```python
# 导入模块
from aioquant import const
from aioquant import order
from aioquant.trade import Trade
from aioquant.utils import logger
from aioquant.order import Order

# 初始化
platform = const.BINANCE  # 交易平台 假设是binance
account = "abc@gmail.com"  # 交易账户
access_key = "ABC123"  # ACCESS KEY
secret_key = "abc123"  # SECRET KEY
symbol = "ETH/BTC"  # 交易对
strategy_name = "my_test_strategy"  # 自定义的策略名称

# 注册订单更新回调函数，注意此处注册的回调函数是 `async` 异步函数，回调参数为 `order` 对象，数据结构请查看下边的介绍。
async def on_event_order_update(order: Order):
    logger.info("order:", order)

# 创建trade对象
trader = Trade(strategy_name, platform, symbol, account=account, access_key=access_key, secret_key=secret_key, 
                order_update_callback=on_event_order_update)

# 下单
action = order.ORDER_ACTION_BUY  # 买单
price = "11.11"  # 委托价格
quantity = "22.22"  # 委托数量
order_id, error = await trader.create_order(action, price, quantity)  # 注意，此函数需要在 `async` 异步函数里执行


# 撤单
order_id, error = await trader.revoke_order(order_id)  # 注意，此函数需要在 `async` 异步函数里执行


# 查询所有未成交订单id列表
order_ids, error = await trader.get_open_order_ids()  # 注意，此函数需要在 `async` 异步函数里执行


# 查询当前所有未成交订单数据
orders = trader.orders  # orders是一个dict，key为order_id，value为order对象
order = trader.orders.get(order_id)  # 提取订单号为 order_id 的订单对象
```

#### 1.2 Trade交易模块初始化

初始化Trade交易模块需要传入一些必要的参数来指定需要交易的必要信息，比如：交易策略名称、交易平台、交易对、交易账户、账户的AK等等。

```python
from aioquant.const import BINANCE
from aioquant.trade import Trade

platform = BINANCE  # 交易平台 假设是binance
account = "abc@gmail.com"  # 交易账户
access_key = "ABC123"  # ACCESS KEY
secret_key = "abc123"  # SECRET KEY
symbol = "ETH/BTC"  # 交易对
strategy_name = "my_test_strategy"  # 自定义的策略名称

```

- 简单初始化方式
```python
trader = Trade(strategy_name, platform, symbol, account=account, access_key=access_key, secret_key=secret_key)
```

- 如果需要实时获取到已提交委托单的实时变化情况，那么可以在初始化的时候指定订单更新回调函数
```python
from aioquant.order import Order  # 导入订单模块

# 当委托单有任何变化，将通过此函数回调变化信息，order为订单对象，下文里将对 `Order` 有专题说明
async def on_event_order_update(order: Order):
    print("order update:", order)

trader = Trade(strategy_name, platform, symbol, account=account, access_key=access_key, secret_key=secret_key,
                order_update_callback=on_event_order_update)
```

- 如果是期货，需要实时获取到当前持仓变化情况，那么可以在初始化的时候指定持仓的更新回调函数
```python
from aioquant.position import Position  # 导入持仓模块

# 当持仓有任何变化，将通过此函数回调变化信息，position为持仓对象，下文里将对 `Position` 有专题说明
async def on_event_position_update(position: Position):
    print("position update:", position)

trader = Trade(strategy_name, platform, symbol, account=account, access_key=access_key, secret_key=secret_key,
                order_update_callback=on_event_order_update, position_update_callback=on_event_position_update)
```

- 如果希望判断交易模块的初始化状态，比如网络连接是否正常、订阅订单/持仓数据是否正常等等，那么可以在初始化的时候指定初始化成功状态更新回调函数
```python
from aioquant.error import Error  # 引入错误模块

# 初始化Trade模块成功或者失败，都将回调此函数
# 如果成功，success将是True，error将是None
# 如果失败，success将是False，error将携带失败信息
async def on_event_init_success_callback(success: bool, error: Error, **kwargs):
    print("initialize trade module status:", success, "error:", error)

trader = Trade(strategy_name, platform, symbol, account=account, access_key=access_key, secret_key=secret_key,
                order_update_callback=on_event_order_update, position_update_callback=on_event_position_update,
                init_success_callback=on_event_init_success_callback)
```

#### 1.3 创建委托单
`Trade.create_order` 可以创建任意的委托单，包括现货和期货，并且入参只有4个！

```python
async def create_order(self, action, price, quantity, *args, **kwargs):
    """ 创建委托单
    @param action 交易方向 BUY/SELL
    @param price 委托价格
    @param quantity 委托数量(当为负数时，代表合约操作空单)
    @return (order_id, error) 如果成功，order_id为委托单号，error为None，否则order_id为None，error为失败信息
    """
``` 
> 注意:
- 入参 `action` 可以引入使用 `from quant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL`
- 入参 `price` 最好是字符串格式，因为这样能保持原始精度，否则在数据传输过程中可能损失精度
- 入参 `quantity` 最好是字符串格式，理由和 `price` 一样；另外，当为合约委托单的时候，`quantity` 有正负之分，正代表多仓，负代表空仓
- 返回 `(order_id, error)` 如果成功，`order_id` 为创建的委托单号，`error` 为None；如果失败，`order_id` 为None，`error` 为 `Error` 对象携带的错误信息

#### 1.4 撤销委托单
`Trade.revoke_order` 可以撤销任意多个委托单。

```python
async def revoke_order(self, *order_ids):
    """ 撤销委托单
    @param order_ids 订单号列表，可传入任意多个，如果不传入，那么就撤销所有订单
    @return (success, error) success为撤单成功列表，error为撤单失败的列表
    """
```
> 注意:
- 入参 `order_ids` 是一个可变参数，可以为空，或者任意多个参数
    - 如果 `order_ids` 为空，即 `trader.revoke_order()` 这样调用，那么代表撤销此交易对下的所有委托单；
    - 如果 `order_ids` 为一个参数，即 `trader.revoke_order(order_id)` 这样调用（其中order_id为委托单号），那么代表只撤销order_id的委托单；
    - 如果 `order_ids` 为多个参数，即 `trader.revoke_order(order_id1, order_id2, order_id3)` 这样调用（其中order_id1, order_id2, order_id3为委托单号），那么代表撤销order_id1, order_id2, order_id3的委托单；
- 返回 `(success, error)`，如果成功，那么 `success` 为成功信息，`error` 为None；如果失败，那么 `success` 为None，`error` 为 `Error` 对象，携带的错误信息；

#### 1.5 获取未完成委托单id列表
`Trade.get_open_order_ids` 可以获取当前所有未完全成交的委托单号，包括 `已提交但未成交`、`部分成交` 的所有委托单号。

```python
async def get_open_order_ids(self):
    """ 获取未完成委托单id列表
    @return (result, error) result为成功获取的未成交订单列表，error如果成功为None，如果不成功为错误信息
    """
```
> 注意:
- 返回 `(result, error)` 如果成功，那么 `result` 为委托单号列表，`error` 为None；如果失败，`result` 为None，`error` 为 `Error` 对象，携带的错误信息；

#### 1.6 获取当前所有订单对象

`Trade.orders` 可以提取当前 `Trade` 模块里所有的委托单信息，`dict` 格式，`key` 为委托单id，`value` 为 `Order` 委托单对象。

#### 1.7 获取当前的持仓对象

`Trade.position` 可以提取当前 `Trade` 模块里的持仓信息，即 `Position` 对象，仅限合约使用。


### 2. 订单模块

所有订单相关的数据常量和对象在框架的 `quant.order` 模块下，`Trade` 模块在推送订单信息回调的时候，携带的 `order` 参数即此模块。

#### 2.1 订单类型
```python
from aioquant import order

order.ORDER_TYPE_LIMIT  # 限价单
order.ORDER_TYPE_MARKET  # 市价单
```

#### 2.2 订单操作
```python
from aioquant import order

order.ORDER_ACTION_BUY  # 买入
order.ORDER_ACTION_SELL  # 卖出
```

#### 2.3 订单状态
```python
from aioquant import order

order.ORDER_STATUS_NONE  # 新创建的订单，无状态
order.ORDER_STATUS_SUBMITTED  # 已提交
order.ORDER_STATUS_PARTIAL_FILLED  # 部分成交
order.ORDER_STATUS_FILLED  # 完全成交
order.ORDER_STATUS_CANCELED  # 取消
order.ORDER_STATUS_FAILED  # 失败
```

#### 2.4 合约订单类型
```python
from aioquant import order

order.TRADE_TYPE_NONE  # 未知订单类型，比如订单不是由 thenextquant 框架创建，且某些平台的订单不能判断订单类型
order.TRADE_TYPE_BUY_OPEN  # 买入开多 action=BUY, quantity>0
order.TRADE_TYPE_SELL_OPEN  # 卖出开空 action=SELL, quantity<0
order.TRADE_TYPE_SELL_CLOSE  # 卖出平多 action=SELL, quantity>0
order.TRADE_TYPE_BUY_CLOSE  # 买入平空 action=BUY, quantity<0
```
> 注意： 仅限合约订单使用。

#### 2.5 订单对象
```python
from aioquant import order

o = order.Order(...)  # 初始化订单对象

o.platform  # 交易平台
o.account  # 交易账户
o.strategy  # 策略名称
o.order_id  # 委托单号
o.client_order_id  # 自定义客户端订单id
o.action  # 买卖类型 SELL-卖，BUY-买
o.order_type  # 委托单类型 MKT-市价，LMT-限价
o.symbol  # 交易对 如: ETH/BTC
o.price  # 委托价格
o.quantity  # 委托数量（限价单）
o.remain  # 剩余未成交数量
o.status  # 委托单状态
o.timestamp  # 创建订单时间戳(毫秒)
o.avg_price  # 成交均价
o.trade_type  # 合约订单类型 开多/开空/平多/平空
o.ctime  # 创建订单时间戳
o.utime  # 交易所订单更新时间
```


### 3. 持仓模块

所有持仓相关的对象在框架的 `quant.position` 模块下，`Trade` 模块在推送持仓信息回调的时候，携带的 `position` 参数即此模块。

#### 3.1 持仓对象

```python
from aioquant.position import Position

p = Position(...)  # 初始化持仓对象

p.platform  # 交易平台
p.account  # 交易账户
p.strategy  # 策略名称
p.symbol  # 交易对
p.short_quantity  # 空仓数量
p.short_avg_price  # 空仓平均价格
p.long_quantity  # 多仓数量
p.long_avg_price  # 多仓平均价格
p.liquid_price  # 预估爆仓价格
p.utime  # 更新时间戳(毫秒)
``` 
