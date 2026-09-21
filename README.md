# 山河慢记

慢慢看山河，把每趟旅行的见闻留下来。

持续积累的个人旅行工程：行前做路书，途中记体验，回来再复盘。现有伊犁材料与2026中秋国庆探亲路书已归入统一首页，后续旅行放在同一个仓库。

仓库：[wrj3366/shanhe-manji](https://github.com/wrj3366/shanhe-manji)。沿用现有 Git 历史，本地目录仍为 `ili-route-map`，项目名称为“山河慢记”。

## 使用

```sh
python3 scripts/travel.py build
python3 -m http.server 8766 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8766/`。首页可以搜索旅行与笔记、筛选计划或已有记录，查看长期偏好和愿望。旧秋季路书仍在 `/autumn-homecoming/`；旧伊犁原首页保存在 `/ili-original.html`，其他旧页面URL保持不变。

以后在这个项目里直接说“计划去某地”或“今天这里不值得/这个酒店很好”，助手先读取 `AGENTS.md` 和偏好，再把信息写回对应档案。仅新增对话不会自动跨所有项目同步；持续记忆以仓库文件为准。

## 新增一趟旅行

```sh
python3 scripts/travel.py new 2027-05-example --title '五月旅行' --start 2027-05-01 --end 2027-05-05
python3 scripts/travel.py note 2027-05-example --date 2027-05-01 --title '第一天现场记录' --text '实际体验写在这里'
python3 scripts/travel.py check
```

`new` 生成档案但不会假装已经出行。`note` 写入真实反馈，不自动改变整趟旅行状态。也可以直接编辑JSON/Markdown，然后重新 `build`。网页以展示为主，不用“浏览器本地已保存”冒充写回仓库。

## 结构

```text
index.html / assets/         统一旅行首页与生成的展示数据
AGENTS.md                   后续助手的规划与记忆规则
data/preferences.json       有来源、状态和适用范围的偏好
trips/<id>/trip.json         标题、日期、状态、标签、链接
trips/<id>/plan.md           行前计划、取舍、待核实信息
trips/<id>/journal.json      用户真实反馈、记录来源与媒体说明
trips/<id>/review.md         旅后复盘
scripts/travel.py            新建、记日志、校验与生成展示数据
tests/                      CLI与数据约束测试
templates/                  新行程与日志使用说明
```

`assets/library-data.js` 从JSON生成，不手动编辑。它包含个人偏好与日志，和源目录一样不适合在未检查时整仓公开。

## 发布页面

```sh
python3 scripts/build_site.py
```

这会生成 `dist/`：旅行首页、各趟路书、页面资源，以及页面直接引用的档案说明。发布产物单独生成，不包含 Git 历史、CLI、测试、项目约定、原始JSON或未跟踪文件；首页展示的偏好和日志仍包含在生成的展示数据中。

`dist/` 不提交 Git。发布前会校验站内链接，并为发布版生成独立的项目简介。本站使用 **GitHub Pages**；`.github/workflows/pages.yml` 在每次推送 `main` 时自动运行测试、构建并发布 `dist/`。

首次发布需要在仓库 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。设置完成后，推送 `main` 或手动运行 **Publish GitHub Pages** 工作流。

默认站点地址：<https://wrj3366.github.io/shanhe-manji/>；秋季路书：<https://wrj3366.github.io/shanhe-manji/autumn-homecoming/>。以 Actions 部署成功及页面实际可访问为上线依据。

新增页面与引用的档案需要先纳入 Git 跟踪，再构建发布包。源代码推送到本仓库的 `main` 分支：`git push origin HEAD:main`。

后续更新先修改源资料，再运行数据校验、构建与测试，按当次授权推送 Git；Actions 会自动更新线上页面。Git 推送与网页部署是两个独立步骤，不把推送成功当作页面已上线。

## 资料边界

- 偏好分为已确认、当次背景、推测与愿望；下一次的明确要求优先。
- 伊犁有部分现场反馈，不等于逐日实际轨迹全部确认。原始材料与计划页面保留。
- 秋季探亲仍是规划，没有虚构的出行日记；日期过去不自动改为已完成。
- “两名成人、一辆燃油车、一间房”是既有预算假设，不是已确认的长期个人资料。
- 默认只保存到城市/县级位置。具体住址、证件、订单、联系方式不写进公开页。
- 参考图与实拍分别标记。现有伊犁外链图片不是用户自己的照片。

## 校验与版本

```sh
python3 scripts/travel.py check
python3 scripts/travel.py build
python3 -m unittest discover -s tests
```

本地提交记录每次变化。是否推送远端、是否发布某趟路书单独按用户授权处理；分享时可以只发布那趟路书，不默认公开整个旅行档案。
