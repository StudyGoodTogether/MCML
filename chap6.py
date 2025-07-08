# 【例6-1】
import mcp
import httpx

# 创建MCP服务器实例
app = mcp.server.FastMCP()

# 定义一个工具函数，用于执行网络搜索
@app.tool()
def web_search(query: str) -> str:
    """
    使用Bing搜索引擎进行网络搜索，并返回摘要结果。
    """
    response = httpx.get(
        "https://api.bing.microsoft.com/v7.0/search",
        params={"q": query},
        headers={"Ocp-Apim-Subscription-Key": "your_api_key"}
    )
    response.raise_for_status()
    data = response.json()
    snippets = [item["snippet"] for item in data["webPages"]["value"]]
    return "\n".join(snippets)

# 启动MCP服务器，使用stdio传输层
if __name__ == "__main__":
    app.run(transport="stdio")



# 【例6-2】
import mcp
import httpx

# 创建MCP服务器实例
app = mcp.server.FastMCP()

# 定义并注册工具函数
@app.tool()
def web_search(query: str) -> str:
    """
    使用Bing搜索引擎进行网络搜索，并返回摘要结果。
    """
    response = httpx.get(
        "https://api.bing.microsoft.com/v7.0/search",
        params={"q": query},
        headers={"Ocp-Apim-Subscription-Key": "your_api_key"}
    )
    response.raise_for_status()
    data = response.json()
    snippets = [item["snippet"] for item in data["webPages"]["value"]]
    return "\n".join(snippets)

# 启动MCP服务器，使用stdio传输层
if __name__ == "__main__":
    app.run(transport="stdio")

# docker-compose.yml
version: "3.9"

services:
  mcp_server:
    image: python:3.11-slim
    container_name: mcpsrv
    working_dir: /app
    volumes:
      - ./mcp_server:/app
    command: ["uv", "run", "start_mcp.py"]
    ports:
      - "8080:8080"
    environment:
      MCP_LOG_LEVEL: "DEBUG"
      MODEL_API_ENDPOINT: "http://model_svc:5000/api"
      DB_HOST: "db_svc"
      DB_USER: "mcp_user"
      DB_PASS: "mcp_pass"
    depends_on:
      - model_svc
      - db_svc
    networks:
      - mcp_net

  model_svc:
    image: python:3.11
    container_name: modelsvc
    working_dir: /model
    volumes:
      - ./model_svc:/model
    command: ["python", "model_api.py"]
    expose:
      - "5000"
    networks:
      - mcp_net

  db_svc:
    image: postgres:15
    container_name: mcpdb
    environment:
      POSTGRES_USER: "mcp_user"
      POSTGRES_PASSWORD: "mcp_pass"
      POSTGRES_DB: "mcp_data"
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - mcp_net

  logstash_svc:
    image: docker.elastic.co/logstash/logstash:8.5.0
    container_name: mcplog
    volumes:
      - ./logstash/config:/usr/share/logstash/config
    depends_on:
      - mcp_server
    networks:
      - mcp_net

volumes:
  db_data:

networks:
  mcp_net:
    driver: bridge

# 【例6-3】
import os
import time
import asyncio
import json
import random
from typing import Dict, Any

import mcp
import httpx

# Prometheus Python客户端
from prometheus_client import (
    start_http_server,
    Counter,
    Summary,
    Histogram
)

# 创建Metrics
REQUEST_COUNT = Counter(
    'mcp_request_count',
    'Total number of requests processed',
    ['method']
)

REQUEST_LATENCY = Histogram(
    'mcp_request_latency_seconds',
    'Latency of requests in seconds',
    ['method']
)

# MCP服务器实例
app = mcp.server.FastMCP("ticketing-server")

# 模拟演唱会票务数据（场次，库存信息）
concert_data = {
    "concert_001": {"name": "StarSinger World Tour", "tickets_left": 500},
    "concert_002": {"name": "RockLegends Night", "tickets_left": 300}
}

# 模拟日志输出函数：整合到Logstash或Loki
def log_event(level: str, message: str, extra: Dict[str, Any] = None):
    """
    输出结构化日志，兼容Logstash格式
    """
    log_record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level,
        "message": message,
        "extra": extra or {}
    }
    print(json.dumps(log_record, ensure_ascii=False))

@app.tool()
def query_tickets(concert_id: str) -> str:
    """
    查询某场演唱会门票剩余数量
    """
    start_time = time.time()
    REQUEST_COUNT.labels(method="query_tickets").inc()
    with REQUEST_LATENCY.labels(method="query_tickets").time():
        if concert_id not in concert_data:
            log_event("ERROR", f"Concert ID {concert_id} not found", {"concert_id": concert_id})
            return f"Concert {concert_id} does not exist."
        info = concert_data[concert_id]
        log_event("INFO", f"Queried tickets for {concert_id}", info)
        return f"{info['name']} has {info['tickets_left']} tickets left."

@app.tool()
def buy_tickets(concert_id: str, quantity: int) -> str:
    """
    购票操作，减少库存并返回下单结果
    """
    REQUEST_COUNT.labels(method="buy_tickets").inc()
    with REQUEST_LATENCY.labels(method="buy_tickets").time():
        if concert_id not in concert_data:
            log_event("WARN", "Invalid concert ID for buy_tickets", {"concert_id": concert_id})
            return "Concert not found."
        if concert_data[concert_id]['tickets_left'] < quantity:
            log_event("WARN", "Not enough tickets left", {"concert_id": concert_id, "quantity": quantity})
            return "Insufficient tickets."
        concert_data[concert_id]['tickets_left'] -= quantity
        order_id = f"order_{random.randint(1000,9999)}"
        log_event("INFO", "Tickets purchased", {"concert_id": concert_id, "quantity": quantity, "order_id": order_id})
        return f"Order {order_id} placed successfully for {quantity} tickets."

@app.tool()
def refund_tickets(order_id: str, concert_id: str, quantity: int) -> str:
    """
    退票操作，增加库存
    """
    REQUEST_COUNT.labels(method="refund_tickets").inc()
    with REQUEST_LATENCY.labels(method="refund_tickets").time():
        if concert_id not in concert_data:
            log_event("ERROR", "Refund with invalid concert ID", {"concert_id": concert_id})
            return "Invalid concert ID."
        # 简化：假设可直接退票，不检查订单状态
        concert_data[concert_id]['tickets_left'] += quantity
        log_event("INFO", "Tickets refunded", {"concert_id": concert_id, "order_id": order_id, "quantity": quantity})
        return f"Refunded {quantity} tickets for {concert_id}, order {order_id}."

async def main():
    # 启动Prometheus HTTP Server，用于暴露 /metrics 接口
    prometheus_port = 9100
    print(f"Starting Prometheus metrics server on port {prometheus_port}...")
    start_http_server(prometheus_port)

    # 启动MCP服务器
    print("Starting MCP server on stdio transport...")
    app.run(transport="stdio")

if __name__ == "__main__":
    asyncio.run(main())



# 【例6-4】
import os
import asyncio
import json
from typing import Dict, Any

import mcp
import httpx
from httpx import HTTPStatusError

# 初始化 MCP 服务器实例
app = mcp.server.FastMCP("secure-mcp-server")

# OAuth2 配置
OAUTH2_TOKEN_URL = "https://auth.example.com/token"
OAUTH2_CLIENT_ID = "your_client_id"
OAUTH2_CLIENT_SECRET = "your_client_secret"
OAUTH2_SCOPE = "read:secure_data"

# 存储访问令牌
access_token = None

async def fetch_access_token() -> str:
    """
    从 OAuth2 授权服务器获取访问令牌
    """
    global access_token
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                OAUTH2_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": OAUTH2_CLIENT_ID,
                    "client_secret": OAUTH2_CLIENT_SECRET,
                    "scope": OAUTH2_SCOPE,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]
            return access_token
        except HTTPStatusError as e:
            print(f"获取访问令牌失败: {e}")
            return ""

async def validate_token(token: str) -> bool:
    """
    验证访问令牌的有效性
    """
    # 在实际应用中，应向授权服务器验证令牌
    # 此处简化处理，假设令牌有效
    return token == access_token

@app.tool()
async def secure_data_access(token: str, data_id: str) -> Dict[str, Any]:
    """
    受保护的数据访问工具函数

    Args:
        token: 访问令牌
        data_id: 数据标识符

    Returns:
        包含数据的字典
    """
    if not await validate_token(token):
        return {"error": "无效的访问令牌"}

    # 模拟数据访问
    data_store = {
        "data_001": {"name": "机密报告", "content": "这是一个机密报告的内容。"},
        "data_002": {"name": "财务数据", "content": "这是财务数据的内容。"},
    }

    data = data_store.get(data_id, None)
    if data is None:
        return {"error": "数据未找到"}

    return data

async def main():
    # 获取访问令牌
    token = await fetch_access_token()
    if not token:
        print("无法获取访问令牌，退出程序。")
        return

    # 启动 MCP 服务器
    print("启动 MCP 服务器...")
    app.run(transport="stdio")

if __name__ == "__main__":
    asyncio.run(main())