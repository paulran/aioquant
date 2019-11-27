
## Demo使用示例

本示例策略简单实现了在币安(Binance)交易所的`ETH/BTC` 订单薄买盘挂单吃毛刺的功能。  
策略首先订阅了 `ETH/BTC` 的订单薄实时行情，拿到买3(bid3)和买4(bid4)的价格，然后计算买3和买4的平均价格(price = (bid3+bid4)/2)，
同时判断是否已经有挂单。如果已经挂单，那么判断挂单价格是否超过当前bid3和bid4的价格区间，如果超过那么就撤单之后重新挂单；如果没有挂单，
那么直接使用price挂单。

> NOTE: 示例策略只是简单演示本框架的使用方法，策略本身还需要进一步优化，比如成交之后的追单，或对冲等。


#### 推荐创建如下结构的文件及文件夹:
```text
ProjectName
    |----- docs
    |       |----- README.md
    |----- scripts
    |       |----- run.sh
    |----- config.json
    |----- src
    |       |----- main.py
    |       |----- strategy
    |               |----- strategy1.py
    |               |----- strategy2.py
    |               |----- ...
    |----- .gitignore
    |----- README.md
```

#### 策略服务配置

策略服务配置文件为 [config.json](config.json)，其中:

- ACCOUNTS `list` 策略将使用的交易平台账户配置；
- strategy `string` 策略名称
- symbol `string` 策略运行交易对

> 服务配置文件使用方式: [配置文件](../../docs/configure/README.md)


##### 运行

```text
python src/main.py config.json
```
