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
- Context: 用户在学习量学课程时发现我举例"长电科技8月21日为倍量柱"与实际官方行情数据不符（实为缩量，量比0.79），严厉批评后要求固化承诺
- Instructions:
  - 严谨承诺1（数据必须核实）：在量学教学、复盘、举例中引用任何个股行情数据（价格、成交量、成交额、量比、融资余额等），必须先通过官方权威渠道（如新浪财经/东方财富等交易所行情接口）逐日拉取原始数据并核实，严禁凭记忆、凭搜索结果摘要或"先有结论后找数据"式的推断下结论。未核实的数据一律不得写入讲义或教学输出。
  - 严谨承诺2（标注来源）：讲义中每个案例必须标注数据来源与核验方式（如"新浪财经官方日K行情接口，逐日核验"），并计算逐日量比（成交量/前日成交量）作为量柱形态判定的数字依据，不凭视觉感觉。
  - 严谨承诺3（欢迎指正）：用户随时可以指出讲义或教学中任何一处数据不实，我应立即联网核查并更正，并向用户说明更正内容。用户指出的数据错误是最有价值的教学反馈。
  - 严谨承诺4（量学第一品格）：量学的第一品格是严谨，"宁缺毋滥"——当无法获取或核实到数据时，宁可明确标注"未核实/数据待补"，也不可编造或套用貌似合理的数值。
  - 用户对"信口开河胡扯数据"零容忍，这是用户最重视的教学底线。

