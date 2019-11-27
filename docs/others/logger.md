
## 日志打印

日志可以分多个级别，打印到控制台或者文件，文件可以按天分割存储。


##### 1. 日志配置
```json
{
    "LOG": {
        "console": true,
        "level": "DEBUG",
        "path": "/var/log/servers/aioquant",
        "name": "quant.log",
        "clear": true,
        "backup_count": 5
    }
}
```
**参数说明**:
- console `boolean` 是否打印到控制台，`true 打印到控制台` / `false 打印到文件`，可选，默认为 `true`
- level `string` 日志打印级别 `DEBUG`/ `INFO`，可选，默认为 `DEBUG`
- path `string` 日志存储路径，可选，默认为 `/var/log/servers/aioquant`
- name `string` 日志文件名，可选，默认为 `quant.log`
- clear `boolean` 初始化的时候，是否清理之前的日志文件，`true 清理` / `false 不清理`，可选，默认为 `false`
- backup_count `int` 保存按天分割的日志文件个数，默认0为永久保存所有日志文件，可选，默认为 `0`

> 配置文件可参考 [服务配置模块](../configure/README.md);


##### 2. 导入日志模块

```python
from aioquant.utils import logger

logger.debug("a:", 1, "b:", 2)
logger.info("start strategy success!", caller=self)  # 假设在某个类函数下调用，可以打印类名和函数名
logger.warn("something may notice to me ...")
logger.error("ERROR: server down!")
logger.exception("something wrong!")
```


##### 3. INFO日志
```python
def info(*args, **kwargs):
```

##### 4. WARNING日志
```python
def warn(*args, **kwargs):
```

##### 4. DEBUG日志
```python
def debug(*args, **kwargs):
```

##### 5. ERROR日志
````python
def error(*args, **kwargs):
````

##### 6. EXCEPTION日志
```python
def exception(*args, **kwargs):
```


> 注意:
- 所有函数的 `args` 和 `kwargs` 可以传入任意值，将会按照python的输出格式打印；
- 在 `kwargs` 中指定 `caller=self` 或 `caller=cls`，可以在日志中打印出类名及函数名信息；
