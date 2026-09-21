# 我们的旅行日志

持续积累的个人旅行工程：行前做路书，途中记体验，回来再复盘。现有伊犁材料与2026中秋国庆探亲路书已归入统一首页，后续旅行放在同一个仓库。

本地目录：`/Users/jack/Documents/livenet/ili-route-map`。沿用现有 Git 历史和目录，显示名称升级为“我们的旅行日志”；远端仍是原来的 `wrjvszq/yili`，本次不更名、不推送、不公开部署。Codex 的独立侧边栏项目尚未注册，不把仓库名称当成已创建的应用项目。

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
