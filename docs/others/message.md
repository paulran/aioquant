## 消息推送 & 拨打电话


##### 1. 推送钉钉消息

> 使用  

```python
    from quant.utils.dingding import DingTalk
    
    await DingTalk.send_text_msg(access_token, content, phones, is_at_all)
```

> 说明  
- 钉钉群消息每个 `access_token` 每分钟推送消息不能超过20条；


##### 2. 推送Telegram消息

> 使用  

```python
    from quant.utils.telegram import TelegramBot
    
    await TelegramBot.send_text_msg(token, chat_id, content)
```


##### 3. 拨打电话

> 使用  

```python
    from quant.utils.twilio import Twilio
    
    await Twilio.call_phone(account_sid, token, _from, to)
```
