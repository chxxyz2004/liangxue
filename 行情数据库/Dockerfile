FROM python:3.11-slim

WORKDIR /workspace/行情数据库

# 复制必要文件
COPY server.py .
COPY dashboard.html .
COPY index.html .
COPY kline/ ./kline/
COPY kline_5min/ ./kline_5min/
COPY meta.json .

# 暴露端口
EXPOSE 8086

# 启动命令
CMD ["python3", "server.py", "8086"]
