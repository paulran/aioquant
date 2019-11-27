
## 进程锁 & 线程锁

当业务复杂到使用多进程或多线程的时候，并发提高的同时，对内存共享也需要使用锁来解决资源争夺问题。


##### 1. 线程（协程）锁

> 使用  

```python
    from quant.utils.decorator import async_method_locker
    
    @async_method_locker("unique_locker_name")
    async def func_foo():
        pass
```

- 函数定义
```python
def async_method_locker(name, wait=True):
    """ 异步方法加锁，用于多个协程执行同一个单列的函数时候，避免共享内存相互修改
    @param name 锁名称
    @param wait 如果被锁是否等待，True等待执行完成再返回，False不等待直接返回
    * NOTE: 此装饰器需要加到async异步方法上
    """
```

> 说明  
- `async_method_locker` 为装饰器，需要装饰到 `async` 异步函数上；
- 装饰器需要传入一个参数 `name`，作为此函数的锁名；
- 参数 `wait` 可选，如果被锁是否等待，True等待执行完成再返回，False不等待直接返回
