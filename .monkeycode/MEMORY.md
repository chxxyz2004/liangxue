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
- Date: 2026-08-27
- Context: 用户通过其他大模型优化了MEMORY.md，生成v4.1终极版，结构重组为10章节，新增五维看盘框架、检查清单、常见问题等
- Instructions:
  - 人设文件已从原始格式（336行）升级为v4.1终极版（429行），新版本位于 /workspace/MEMORY.md
  - 核心变化：结构重组为角色定位→用户画像→核心原则→数据规范→教学工作流→工具链→红线禁令→检查清单→常见问题→知识索引
  - 新增五维看盘框架（量/价/时/空/资金），要求每份报告必须覆盖五个维度，至少3个维度共振才可信
  - 新增「位置决定性质」原则作为最高优先级，所有信号必须结合250日百分位判断
  - 报告模板全部小白友好化，每个判断必须回答「是什么？为什么？我该怎么做？」
  - 新增检查清单和常见问题章节，便于快速查阅关键规则
  - 持仓股票（6只）：淳中科技(603516)、工业富联(601138)、赛腾股份(603283)、通富微电(002156)、环旭电子(601231)、胜宏科技(300476)
  - 关注股（2只）：天孚通信(300394)、长电科技(600584)
  - 用户设备：华为Mate 30 Pro，手机端学习为主
  - 看盘软件：通达信
  - 核心文件位置：/workspace/MEMORY.md（人设总纲）、/workspace/行情数据库/config.py（配置中心）
  - 系统端口：8000（讲义导航）、8086（Web工作台）
