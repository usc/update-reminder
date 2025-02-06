# 更新提醒
针对Github仓库、Jenkins构建的更新提醒

## 使用
### 运行
```
python main.py --days 7 --file /custom/path/targets.txt --cache /custom/path/cache.json --updates /custom/path/updates.txt
```
参数说明：
```
--days：检查的时间范围，默认为过去 7 天。
--file：仓库列表文件路径，默认名为 targets.txt，请自行创建。
--cache：缓存文件，默认缓存文件为 cache.json。
--updates：更新内容文件，默认为 updates.txt。
```
### 环境变量
配置放到 `.env` 文件中，其中
```
# Github的个人访问令牌
GITHUB_TOKEN=

# Telegram Bot配置，具体如何创建机器人及获取配置请查找网络
TELEGRAM_CHAT_ID=
TELEGRAM_BOT_TOKEN=

# Email配置
SMTP_SERVER=
SMTP_PORT=
SENDER_EMAIL=
EMAIL_PASSWORD=
RECEIVER_EMAIL=
## 是否cc给发件人，不配置默认为true
CC_SENDER= 

```


## 优势
- 多源支持：同时支持 GitHub 和 Jenkins。
- 灵活配置：目标列表、缓存文件路径均可通过参数指定。
- 避免重复提醒：缓存记录所有提示过的版本，确保同一版本不会重复输出。
- 持久化记录：缓存存储在本地文件中，即使程序重启也能维持状态。
- 避免频繁执行同样的检查：缓存更新检查时间，同一天仅执行一次。
- 更好用户体验：无论在哪个路径运行，避免路径问题导致的文件未找到错误。
- 实时日志：清晰显示检查进度和结果。
- 支持Telegram：更新内容推送Telegram，实时了解更新内容。
- 支持Email：把更新内容通过email发送。