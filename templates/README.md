# 新行程与日志模板

优先使用 `python3 scripts/travel.py new YYYY-MM-destination --title '旅行标题' --start YYYY-MM-DD --end YYYY-MM-DD`，会生成统一的元信息、空日志、计划与复盘文件。未确定日期时省略日期参数，保留为“想去”。

行前先写：出发地、时长、同行人、预算是否明确、核心体验、驾驶上限、当前偏好适用范围、航班/住宿/景区待核实信息。互动页面如需要，放该行程目录下 `page/index.html`，在 `trip.json.links` 中登记仓库相对路径。

每天反馈可以只说：
> 今天去了哪里，最喜欢什么，哪里不值得，开车累不累，实际花费，哪张照片想留下。

对话中的真实反馈写入 `journal.json`，推测留在 `plan.md` 待确认。照片使用 `media` 记录来源与说明，不自动抓取外链作为个人实拍。

旅行后补 `review.md`：计划与实际差异、值得再去/可跳过、住宿与交通体验、下次怎么改。需要形成长期偏好时，写入 `data/preferences.json` 并带来源与 `confirmed/context/inferred/wishlist` 状态。
