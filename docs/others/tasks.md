
## 定时任务 & 协程任务


##### 1. 注册定时任务
定时任务模块可以注册任意多个回调函数，利用服务器每秒执行一次心跳的过程，创建新的协程，在协程里执行回调函数。

```python
# 导入模块
from aioquant.tasks import LoopRunTask

# 定义回调函数
async def function_callback(*args, **kwargs):
    pass

# 回调间隔时间(秒)
callback_interval = 5

# 注册回调函数
task_id = LoopRunTask.register(function_callback, callback_interval)

# 取消回调函数
LoopRunTask.unregister(task_id)  # 假设此定时任务已经不需要，那么取消此任务回调
```

> 注意:
- 回调函数 `function_callback` 必须是 `async` 异步的，且入参必须包含 `*args` 和 `**kwargs`；
- 回调时间间隔 `callback_interval` 为秒，默认为1秒；
- 回调函数将会在心跳执行的时候被执行，因此可以对心跳次数 `kwargs["heart_beat_count"]` 取余，来确定是否该执行当前任务；


##### 2. 协程任务
协程可以并发执行，提高程序运行效率。

```python
# 导入模块
from aioquant.tasks import SingleTask

# 定义回调函数
async def function_callback(*args, **kwargs):
    pass
    
# 执行协程任务
SingleTask.run(function_callback, *args, **kwargs)
```

> 注意:
- 回调函数 `function_callback` 必须是 `async` 异步的;
