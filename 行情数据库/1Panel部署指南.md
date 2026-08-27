# 量学系统 - 1Panel Docker 部署指南

## 方式一：使用 1Panel 容器创建（推荐）

### 步骤

1. **登录 1Panel 面板**
   ```
   http://<Ubuntu内网IP>:端口
   ```

2. **进入容器页面**
   - 左侧菜单 → 容器 → 容器 → 创建

3. **填写容器配置**

   | 配置项 | 值 |
   |--------|-----|
   | 容器名称 | `liangxue` |
   | 镜像 | `python:3.11-slim` |
   | 启动命令 | `python3 /opt/liangxue/server.py 8086` |
   | 端口映射 | `8086:8086` |
   | 重启策略 | 始终重启 |

4. **挂载数据卷**（重要！）
   
   点击"高级选项" → "挂载" → 添加：
   
   | 类型 | 宿主机路径 | 容器路径 |
   |------|-----------|---------|
   | 目录 | `/opt/liangxue/kline` | `/workspace/行情数据库/kline` |
   | 目录 | `/opt/liangxue/kline_5min` | `/workspace/行情数据库/kline_5min` |

5. **创建并启动**

---

## 方式二：使用 docker-compose（进阶）

### 1. SSH 登录 Ubuntu
```bash
ssh root@<Ubuntu内网IP>
```

### 2. 拉取代码
```bash
mkdir -p /opt/liangxue
cd /opt/liangxue
git clone https://github.com/chxxyz2004/liangxue.git
cd liangxue/行情数据库
```

### 3. 启动容器
```bash
# 首次启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 重启
docker-compose restart
```

### 4. 配置 Nginx 反代（可选）

在 1Panel → 网站 → 添加站点：
- 域名：`stock.yourdomain.com`
- 反向代理：`http://127.0.0.1:8086`

---

## 定时任务（数据每日更新）

### 1Panel 计划任务
```
类型: Shell脚本
名称: 量学数据更新
命令: cd /opt/liangxue/行情数据库 && python3 update_data.py
周期: 每天 09:00
```

---

## 管理命令

```bash
# 进入容器
docker exec -it liangxue bash

# 查看日志
docker logs -f liangxue

# 重启服务
docker restart liangxue

# 更新代码
cd /opt/liangxue/liangxue && git pull
docker-compose up -d --build
```

---

## 访问地址

| 类型 | 地址 |
|------|------|
| 内网直接访问 | `http://<Ubuntu_IP>:8086` |
| 外网（配置反代后） | `https://stock.yourdomain.com` |
| API测试 | `http://<Ubuntu_IP>:8086/api/overview` |

---

## 备份数据

```bash
# 备份数据目录
tar czf /backup/liangxue-$(date +%Y%m%d).tar.gz /opt/liangxue/kline/ /opt/liangxue/kline_5min/

# 推送到 GitHub（代码已自动同步）
cd /opt/liangxue/liangxue && git add -A && git commit -m "backup: $(date)" && git push
```
