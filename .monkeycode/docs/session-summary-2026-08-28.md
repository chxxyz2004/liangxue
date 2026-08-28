## Goal
- 完成量学系统核心文件重构、持仓数据同步、隐私保护及第二阶段课程规划

## Constraints & Preferences
- A股颜色惯例：红色涨、绿色跌
- 未来函数零容忍
- 报告命名：盘前预案/盘中盯盘/午间资金识别/收盘资金识别
- 移动端优先设计
- 用户设备：华为Mate 30 Pro，手机端学习为主
- 看盘软件：通达信
- 用户对数据准确性零容忍
- 持仓成本/股数/盈亏为个人隐私，不推送GitHub

## Progress
### Done
- 持仓数据更新为实盘截图（2026-08-27）：淳中300股@41.02、富联500股@57.35、胜宏100股@249.58、通富100股@64.26、环旭200股@45.06、赛腾200股@46.19
- 导航页今日行动指引更新（淳中+128%止盈纪律）
- 修复 generate_report.py、auto_evening_review.sh 引用 config.py
- 修复 update_data.py、pull_5min.py 引用 config.py（移除中贝/华建僵尸股）
- 修复 generate_deep_report.py、dashboard_api.py、dashboard_v2.py、simple_dashboard.py 引用 config.py
- 根目录 config.py 改为桥接文件转发正式配置，已加入 gitignore 并从 git 移除跟踪
- MEMORY.md 已 gitignore 并从 git 移除
- 现代量学讲义/index.html 已 gitignore 并从 git 移除
- 新增 config.example.py 配置模板（不含真实数据）
- 8000端口讲义服务重启成功，8086端口Web工作台正常运行
- 第一阶段课程（第1-10课）已全部完成
- **第二阶段第①课「通达信工具落地」已完成**：前复权设置/量比查看/画线实操，含5题测验+5项作业
- **第二阶段第②课「每日盯盘模板与心理体检」已完成**：盘前45分钟6件事、盘中30分钟检查点、收盘6步、心理体检10题
- 导航页已整合课程列表（第一阶段10课+第二阶段12课预告）
- MEMORY.md 已更新至 v4.3

### In Progress
- 无

### Blocked
- 腾讯日K接口被WAF临时拦截（501），本地数据8/27 15:30已更新完整，不影响使用；明日15:30 cron拉数需关注是否恢复

## Key Decisions
- 所有脚本统一引用 /workspace/行情数据库/config.py 作为唯一数据源，禁止硬编码
- 根目录旧 config.py（含900/1100股等旧数据）改为桥接文件，转发到正式配置，防止误导入
- 持仓敏感数据（成本/股数/止损线）全部 gitignore，不再推送到 GitHub
- 第二阶段的优先顺序维持 2026-08-25 确定版：①通达信工具落地 → ②战法深化 → ③看盘八法精讲 → ④实盘纪律训练

## Next Steps
- 明日 09:25 验证 crontab 自动生成盘前预案（腾讯WAF是否恢复）
- 准备并讲授第二阶段第③课：看盘八法精讲
- 若腾讯接口持续被WAF拦截，排查网络策略或更换数据源

## Critical Context
- 持仓（2026-08-27实盘）：淳中300股@41.023（现价93.60,+128%）、富联500股@57.348（+11.4%）、胜宏100股@249.581（+5.4%，止盈区256-260）、通富100股@64.26（-4.7%）、环旭200股@45.062（-38.9%）、赛腾200股@46.186（+5%）
- 关注池：天孚通信(sz300394)、长电科技(sh600584)
- 淳中纪律：反弹93-95减1手，再破89.24清仓；胜宏止盈256-260已超分批止盈区
- 总盈亏：+17,279元（收益率+19.07%）
- 8000端口讲义导航：https://8000-202312279de3cd0a.monkeycode-ai.online
- 8086端口Web工作台：https://8086-202312279de3cd0a.monkeycode-ai.online
- crontab 6条定时任务运行中（cron服务正常）
- 第一阶段课程已完成（第01-10课 + 强化课 + 对照表），学情档案位于 .monkeycode/docs/学情档案.md
- 第二阶段第①课已完成（第11课：通达信工具落地）
- 第二阶段第②课已完成（第12课：每日盯盘模板心理体检）
- 学习进度：12/20课（60%）

## Relevant Files
- `/workspace/.monkeycode/MEMORY.md` — 核心人设总纲v4.3（已gitignore，不推送）
- `/workspace/行情数据库/config.py` — 统一配置中心v3.7（唯一数据源，含真实持仓数据）
- `/workspace/行情数据库/config.example.py` — 配置模板（不含真实数据，已提交）
- `/workspace/config.py` — 桥接文件，转发到行情数据库/config.py（已gitignore）
- `/workspace/行情数据库/server.py` — Web服务v2.0（8086端口，引用config.py）
- `/workspace/现代量学讲义/第11课-通达信工具落地.html` — 讲义第11课（第二阶段第①课）
- `/workspace/现代量学讲义/第12课-每日盯盘模板心理体检.html` — 讲义第12课（第二阶段第②课）
- `/workspace/现代量学讲义/index.html` — 导航页（已gitignore，本地保留）
- `/workspace/.monkeycode/docs/学情档案.md` — 学习进度记录
- `/workspace/MEMORY.md` — 用户上传源文件（已gitignore，不推送）

## Daily Action Summary
- 2026-08-28 完成：第二阶段第②课「每日盯盘模板与心理体检」
- 讲义726行，手机适配，含5题测验+5项作业
- 学习进度更新为12/20课（60%）
- 预览地址：https://8000-202312279de3cd0a.monkeycode-ai.online/第12课-每日盯盘模板心理体检.html