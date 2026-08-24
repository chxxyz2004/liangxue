# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[User Instruction Summary]
- Date: 2026-08-24
- Context: 用户要求系统梳理教学机制并建立"自我进化"（档案式记忆）能力，理解他的想法
- Instructions:
  - 用户画像：新手小白，从零系统学习量学，最终目标是应用于A股实战交易。讲解必须通俗易懂、用生活化比喻，阐明内在逻辑与市场机理，不能照本宣科。
  - 关注股票池（算力产业链）：工业富联(601138)、胜宏科技(300476)、天孚通信(300394)、淳中科技(603516)、通富微电(002156)、长电科技(600584)、赛腾股份(603283)、环旭电子(601231)。教学复盘举例优先用这些股票。
  - 教学偏好：立足实战+联网更新盘面数据；客观剖析传统量学不足；深挖底层逻辑；现代量化升级；每课结束生成HTML讲义到 `/workspace/现代量学讲义/`；手把手教看盘复盘；引导式教学+留作业。
  - 沟通偏好：直接、有干货、不糊弄；用户是小白，术语要解释；用户对数据严谨性零容忍。
  - 讲义网站已部署于8000端口（后台终端管理），讲义目录含index.html导航页，更新讲义后用户通过预览链接阅读。

[User Instruction Summary]
- Date: 2026-08-24
- Context: 用户确认复盘日报需全量历史保留，不允许旧复盘被覆盖或删除
- Instructions:
  - 复盘日报永久保留：每一份复盘日报必须存为独立文件，命名格式 `复盘-YYYY-MM-DD.html`，只增不改，严禁覆盖或删除任何历史复盘文件。
  - 导航首页（index.html）按日期倒序展示复盘列表，新增日期排最上面，历史复盘入口始终保留、始终可点击打开。
  - 每次复盘完成后，同时提交git并推送到GitHub（`chxxyz2004/liangxue`），形成三重备份：工作区文件 + git历史 + GitHub远程仓库。
  - 用户明确要求"保留全部复盘日报"，这是硬性约定。

[User Instruction Summary]
- Date: 2026-08-24
- Context: 用户是手机端学习者，打字不便且易出错，要求作业以选择题方式布置
- Instructions:
  - 作业一律采用选择题形式：做成可交互HTML作业页面，用户点击选项即可作答，按"提交"后自动生成答案代码，用户复制粘贴即可反馈，无需打字。
  - 作业页面需手机友好（响应式布局、大按钮、点击选中高亮），放在 `/workspace/现代量学讲义/` 目录并在导航首页展示。
  - 用户回复答案代码后，我逐题批改并给出解析。
  - 说明：用户表述能力有限，讲解需更耐心、更通俗，避免一次灌输过多。

[User Instruction Summary]
- Date: 2026-08-24
- Context: 用户在学习量学课程时发现我举例"长电科技8月21日为倍量柱"与实际官方行情数据不符（实为缩量，量比0.79），严厉批评后要求固化承诺
- Instructions:
  - 严谨承诺1（数据必须核实）：在量学教学、复盘、举例中引用任何个股行情数据（价格、成交量、成交额、量比、融资余额等），必须先通过官方权威渠道（如新浪财经/东方财富等交易所行情接口）逐日拉取原始数据并核实，严禁凭记忆、凭搜索结果摘要或"先有结论后找数据"式的推断下结论。未核实的数据一律不得写入讲义或教学输出。
  - 严谨承诺2（标注来源）：讲义中每个案例必须标注数据来源与核验方式（如"新浪财经官方日K行情接口，逐日核验"），并计算逐日量比（成交量/前日成交量）作为量柱形态判定的数字依据，不凭视觉感觉。
  - 严谨承诺3（欢迎指正）：用户随时可以指出讲义或教学中任何一处数据不实，我应立即联网核查并更正，并向用户说明更正内容。用户指出的数据错误是最有价值的教学反馈。
  - 严谨承诺4（量学第一品格）：量学的第一品格是严谨，"宁缺毋滥"——当无法获取或核实到数据时，宁可明确标注"未核实/数据待补"，也不可编造或套用貌似合理的数值。
  - 用户对"信口开河胡扯数据"零容忍，这是用户最重视的教学底线。

[User Instruction Summary]
- Date: 2026-08-24
- Context: 用户因多次数据出错，要求建立本地行情数据库，不再每次临时拉数据
- Instructions:
  - 行情数据一律先本地化：`/workspace/行情数据库/kline/` 下已存8只关注股票+3大盘指数的300个交易日日K数据（新浪财经官方接口，覆盖一年有余，截至2026-08-24）。
  - 更新方式：每天收盘后（约15:30）运行 `python3 /workspace/行情数据库/update_data.py` 全量更新当日数据；讲课/复盘需要数据时直接 `python3 /workspace/行情数据库/query.py` 读本地库，禁止临时凭记忆或临时搜索拼数据。
  - 读库工具用法：`query.py`（8股总览）、`query.py 601138 30`（最近30日含量比/涨跌幅）、`query.py --pos`（250日位置百分位）。
  - 数据已提交git并推送GitHub，形成三重备份；更新后应重新提交推送。

