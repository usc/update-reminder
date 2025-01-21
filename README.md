# 更新提醒
针对Github仓库、Jenkins构建的更新提醒

## 使用
```
python main.py --days 7 --file /custom/path/targets.txt --cache /custom/path/cache.json
```
参数说明：
```
token：GitHub 的个人访问令牌，从 .env 文件获取 GitHub token。
--file：仓库列表文件路径，默认为 targets.txt。
--days：检查的时间范围，默认为过去 7 天。
--cache：缓存文件，默认缓存文件为 cache.json。
```

## 优势
- 多源支持：同时支持 GitHub 和 Jenkins。
- 灵活配置：目标列表、缓存文件路径均可通过参数指定。
- 避免重复提醒：缓存记录所有提示过的版本，确保同一版本不会重复输出。
- 持久化记录：缓存存储在本地文件中，即使程序重启也能维持状态。
- 避免频繁执行同样的检查：缓存更新检查时间，同一天仅执行一次。
- 更好用户体验：无论在哪个路径运行，避免路径问题导致的文件未找到错误。
- 实时日志：清晰显示检查进度和结果。
- 支持Telegram：更新内容推送Telegram，实时了解更新内容