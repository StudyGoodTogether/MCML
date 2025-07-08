# 【例10-1】
import os
import time
import random
import json
import asyncio
from typing import Dict, List, Any

import mcp
from mcp.server import FastMCP
from mcp.server.stdio import stdio_server
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

#############################
# Mock: local FAQ knowledge base
#############################
FAQ_DB = {
    "shipping_cost": "国际运费按重量与地区计算, 国内免运费活动持续至年底.",
    "refund_policy": "订单可在7日内申请无理由退货, 售后会在3日内处理.",
    "exchange_process": "交换商品需先提交工单, 待客服审核后发起换货流程."
}

#############################
# Mock: local Ticket system
#############################
TICKET_DB: Dict[str, Dict[str, Any]] = {}

def create_ticket(user_id: str, subject: str, content: str) -> str:
    ticket_id = f"TK-{random.randint(1000,9999)}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    TICKET_DB[ticket_id] = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "subject": subject,
        "content": content,
        "status": "open",
        "create_time": now
    }
    return ticket_id

def get_ticket(ticket_id: str) -> Dict[str, Any]:
    return TICKET_DB.get(ticket_id, {})

#############################
# Mock: local Order system
#############################
ORDER_DB = {
    "OD-2023001": {"order_id": "OD-2023001", "items": ["Laptop"], "status": "shipped", "total_price": 5999, "user_id": "U1001"},
    "OD-2023002": {"order_id": "OD-2023002", "items": ["Keyboard", "Mouse"], "status": "delivered", "total_price": 199, "user_id": "U1002"}
}

#############################
# Build MCP server
#############################
app = FastMCP("customer-service-demo")

@app.tool()
def tool_faq_query(keyword: str) -> Dict[str, Any]:
    """
    模拟FAQ库关键字查询:
    - 在FAQ_DB中查找与keyword最相关的问题
    - 若找不到, 返回提示
    """
    result = {}
    for k, v in FAQ_DB.items():
        if keyword.lower() in k.lower():
            result[k] = v
    if not result:
        return {"message": f"No FAQ found for '{keyword}'"}
    return {"faq_found": result}

@app.tool()
def tool_submit_ticket(user_id: str, subject: str, content: str) -> Dict[str, Any]:
    """
    提交工单, 返回ticket_id
    """
    t_id = create_ticket(user_id, subject, content)
    return {"ticket_id": t_id, "status": "open"}

@app.tool()
def tool_get_ticket(ticket_id: str) -> Dict[str, Any]:
    """
    查看工单详情
    """
    t = get_ticket(ticket_id)
    if not t:
        return {"error": "ticket_not_found"}
    return t

@app.tool()
def tool_query_order(order_id: str) -> Dict[str, Any]:
    """
    查询订单详情
    """
    if order_id not in ORDER_DB:
        return {"error": "order_not_found"}
    return ORDER_DB[order_id]

@app.tool()
def tool_list_orders(user_id: str) -> Dict[str, Any]:
    """
    列出该用户的全部订单
    """
    result = []
    for k, v in ORDER_DB.items():
        if v["user_id"] == user_id:
            result.append(v)
    if not result:
        return {"error": "no_orders_for_user"}
    return {"orders": result}

#############################
# demonstration with server & client
#############################
async def run_server():
    print("=== MCP客服助理服务器启动... ===")
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

async def run_client():
    print("=== 客户端等待5秒后启动... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(command="python", args=[os.path.abspath(__file__)])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化客服助理demo会话...")
            await session.initialize()

            # Step1: FAQ查询
            keyword1 = "refund"
            print(f"[Client] FAQ查询: {keyword1}")
            res_faq1 = await session.call_tool("tool_faq_query", {"keyword": keyword1})
            print("[Client] FAQ查询结果1:", res_faq1)

            # Step2: 未命中的FAQ查询
            keyword2 = "membership"
            print(f"[Client] FAQ查询: {keyword2}")
            res_faq2 = await session.call_tool("tool_faq_query", {"keyword": keyword2})
            print("[Client] FAQ查询结果2:", res_faq2)

            # Step3: 提交工单
            user_id = "U1002"
            subject = "Returning item not found"
            content = "I want to return an item but can't find order status"
            print(f"[Client] 提交工单 user_id={user_id}")
            t_res = await session.call_tool("tool_submit_ticket", {
                "user_id": user_id,
                "subject": subject,
                "content": content
            })
            print("[Client] 工单提交结果:", t_res)

            # Step4: 查看工单
            t_id = t_res.get("ticket_id")
            if t_id:
                print("[Client] 查看工单详情")
                t_view = await session.call_tool("tool_get_ticket", {"ticket_id": t_id})
                print("[Client] 工单详情:", t_view)

            # Step5: 查询订单
            order_id = "OD-2023002"
            print("[Client] 查询订单:", order_id)
            o_res = await session.call_tool("tool_query_order", {
                "order_id": order_id
            })
            print("[Client] 订单详情:", o_res)

            # Step6: 列出用户全部订单
            print("[Client] 列出用户全部订单 user_id=U1002")
            all_o = await session.call_tool("tool_list_orders", {"user_id": "U1002"})
            print("[Client] 用户订单列表:", all_o)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例10-2】
import os
import time
import random
import json
import asyncio
from typing import Dict, Any, List

import mcp
from mcp.server import FastMCP
from mcp.server.stdio import stdio_server
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

########################################
# Mock Data: finance glossary & product info
########################################
FINANCE_GLOSSARY = {
    "ETF": "指数基金的一种, 可在交易所买卖, 通常追踪特定市场指数.",
    "PE Ratio": "市盈率, 表示股票价格与每股收益的比率, 用于价值评估.",
    "Yield Curve": "收益率曲线, 展示不同到期期限债券的收益率关系, 常被用于预测经济走势."
}

PRODUCT_DB = {
    "FundA": {"name": "Global Growth Fund A", "annual_interest": 0.06, "risk_level": "medium"},
    "BondX": {"name": "Corporate Bond X", "annual_interest": 0.04, "risk_level": "low"}
}

########################################
# Mock user accounts & transactions
########################################
USER_ACCOUNT_DB = {
    "U3001": {
        "name": "Alice",
        "balance": 15000.0,
        "transactions": [
            {"date": "2025-03-01", "desc": "Salary", "amount": 8000},
            {"date": "2025-03-15", "desc": "CreditCard Payment", "amount": -3000},
        ]
    },
    "U3002": {
        "name": "Bob",
        "balance": 32000.0,
        "transactions": [
            {"date": "2025-02-28", "desc": "Salary", "amount": 12000},
            {"date": "2025-03-05", "desc": "Stock Purchase", "amount": -5000},
        ]
    }
}

########################################
# Risk test
########################################
RISK_QUESTIONS = [
    "对投资波动的接受度如何(高/中/低)?",
    "期望投资期限是多久(短期/中长期)?"
]
# 仅示例, 简单决定risk_score
def compute_risk_score(answers: List[str]) -> str:
    score = 0
    for a in answers:
        if "高" in a or "long" in a:
            score += 2
        elif "中" in a:
            score += 1
    if score>=3:
        return "激进风险偏好"
    elif score>=2:
        return "平衡风险偏好"
    else:
        return "保守风险偏好"

########################################
# Build MCP server
########################################
app = FastMCP("finance-qa-demo")

@app.tool()
def tool_finance_glossary(term: str) -> Dict[str, Any]:
    """
    查询金融术语解释
    """
    key = term.lower().replace(" ", "")
    found = []
    for k, v in FINANCE_GLOSSARY.items():
        if key in k.lower().replace(" ", ""):
            found.append({k: v})
    if not found:
        return {"message": f"No explanation found for '{term}'"}
    return {"explanations": found}

@app.tool()
def tool_product_simulation(product_id: str, principal: float, years: float) -> Dict[str, Any]:
    """
    模拟产品的收益, 返回简单复利计算
    """
    if product_id not in PRODUCT_DB:
        return {"error": "invalid product_id"}
    p = PRODUCT_DB[product_id]
    rate = p["annual_interest"]
    final = principal * ((1+rate)**years)
    return {
        "product_name": p["name"],
        "annual_rate": rate,
        "risk_level": p["risk_level"],
        "principal": principal,
        "years": years,
        "estimated_value": round(final, 2)
    }

@app.tool()
def tool_check_account(user_id: str) -> Dict[str, Any]:
    """
    查看用户账户信息与最近交易
    """
    if user_id not in USER_ACCOUNT_DB:
        return {"error": "user_not_found"}
    acc = USER_ACCOUNT_DB[user_id]
    return {
        "name": acc["name"],
        "balance": acc["balance"],
        "recent_transactions": acc["transactions"]
    }

@app.tool()
def tool_risk_survey(answers: List[str]) -> Dict[str, Any]:
    """
    根据问题回答计算一个简单的风险类型
    """
    rtype = compute_risk_score(answers)
    return {"risk_type": rtype}

@app.tool()
def tool_list_products() -> Dict[str, Any]:
    """
    列出可投产品信息
    """
    result = []
    for pid, info in PRODUCT_DB.items():
        result.append({"product_id": pid, "name": info["name"], "rate": info["annual_interest"]})
    return {"products": result}

###############################
# demonstration
###############################
async def run_server():
    print("=== MCP金融问答服务器启动... ===")
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

async def run_client():
    print("=== 客户端等待5秒后开始连接... ===")
    await asyncio.sleep(5)
    # MCP stdio transport
    from mcp.client.stdio import StdioServerParameters, stdio_client
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] Finance QA session init...")
            await session.initialize()

            # Step1: 查询金融术语
            glossary_res = await session.call_tool("tool_finance_glossary", {"term": "Yield Curve"})
            print("[Client] 金融术语查询:", glossary_res)

            # Step2: 模拟某产品收益
            product_sim = await session.call_tool("tool_product_simulation", {
                "product_id": "FundA",
                "principal": 10000,
                "years": 2
            })
            print("[Client] 产品收益模拟:", product_sim)

            # Step3: 查看用户账户
            account_view = await session.call_tool("tool_check_account", {"user_id": "U3002"})
            print("[Client] 用户账户信息:", account_view)

            # Step4: 风险评估问卷
            answers = ["中", "longterm"]
            risk_eval = await session.call_tool("tool_risk_survey", {
                "answers": answers
            })
            print("[Client] 风险偏好:", risk_eval)

            # Step5: 列出可投产品
            prod_list = await session.call_tool("tool_list_products", {})
            print("[Client] 可投产品列表:", prod_list)

async def main():
    import asyncio
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例10-3】
import asyncio
import mcp
from mcp.server import FastMCP

app = FastMCP("agent-workflow-server")

@app.tool()
def init_workflow_context(agent_id: str) -> dict:
    # 模拟创建工作流上下文，返回空任务列表与状态信息
    return {"agent_id": agent_id, "workflow_context": {"tasks": [], "status": "idle"}}

async def run_server():
    print("[Server] Starting MCP Agent Workflow Server...")
    await app.run_stdio()

if __name__ == "__main__":
    asyncio.run(run_server())



# 【例10-4】
import time
import random
import mcp
from mcp.server import FastMCP

app = FastMCP("agent-workflow-server")

# 全局内存存储Agent信息与任务数据库
AGENT_REGISTRY = {}
TASK_DB = {}

@app.tool()
def register_agent(agent_id: str, role: str) -> dict:
    # 注册Agent，记录ID、角色与注册时间
    if agent_id in AGENT_REGISTRY:
        return {"error": "Agent already registered", "agent_id": agent_id}
    AGENT_REGISTRY[agent_id] = {
        "agent_id": agent_id,
        "role": role,
        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"message": f"Agent {agent_id} registered as {role}"}

@app.tool()
def create_task(agent_id: str, task_desc: str) -> dict:
    # 为已注册的Agent创建任务，生成唯一任务ID
    if agent_id not in AGENT_REGISTRY:
        return {"error": "Agent not registered", "agent_id": agent_id}
    task_id = f"TASK-{random.randint(1000,9999)}"
    TASK_DB[task_id] = {
        "task_id": task_id,
        "agent_id": agent_id,
        "description": task_desc,
        "status": "created",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"message": "Task created", "task_id": task_id, "status": "created"}

if __name__ == "__main__":
    # 测试工具函数独立运行
    print(register_agent("agent_A", "workflow_manager"))
    print(create_task("agent_A", "Process customer query"))



# 【例10-5】
import time
import random
import mcp
from mcp.server import FastMCP

app = FastMCP("agent-workflow-server")

# 假设TASK_DB为全局任务数据库，共享于整个服务
TASK_DB = {}

@app.tool()
def dispatch_task(task_id: str, next_step: str) -> dict:
    # 将任务状态更新为指定下一阶段，并记录日志
    if task_id not in TASK_DB:
        return {"error": "Task not found", "task_id": task_id}
    TASK_DB[task_id]["status"] = next_step
    TASK_DB[task_id].setdefault("log", []).append(f"{time.strftime('%H:%M:%S')} - Dispatched to {next_step}")
    return {"message": f"Task {task_id} dispatched to {next_step}", "status": next_step}

@app.tool()
def complete_task(task_id: str) -> dict:
    # 将任务状态标记为completed，并记录完成日志
    if task_id not in TASK_DB:
        return {"error": "Task not found", "task_id": task_id}
    TASK_DB[task_id]["status"] = "completed"
    TASK_DB[task_id].setdefault("log", []).append(f"{time.strftime('%H:%M:%S')} - Task completed")
    return {"message": f"Task {task_id} completed", "status": "completed", "log": TASK_DB[task_id].get("log", [])}

if __name__ == "__main__":
    # 模拟任务记录并测试状态更新工具
    TASK_DB["TASK-1234"] = {
        "task_id": "TASK-1234",
        "agent_id": "agent_A",
        "description": "Demo Task",
        "status": "created",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    print(dispatch_task("TASK-1234", "processing"))
    print(complete_task("TASK-1234"))



# 【例10-6】
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code Block 4: 客户端工作流平台演示
该客户端代码模拟一个完整的工作流平台交互流程，包括Agent注册、任务创建、任务调度与任务完成，
通过MCP的stdio传输接口进行Tool调用，展示工作流平台在金融客服场景中的落地效果。
"""
import os
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def run_client():
    print("[Client] Waiting 5 seconds for server startup...")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]  # 服务器与客户端共用同一文件，仅为示例
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] Client session initialized")
            await session.initialize()
            
            # 注册Agent
            reg_res = await session.call_tool("register_agent", {"agent_id": "agent_A", "role": "workflow_manager"})
            print("[Client] Agent registration:", reg_res)
            
            # 创建任务
            task_res = await session.call_tool("create_task", {"agent_id": "agent_A", "task_desc": "Handle customer financial query"})
            print("[Client] Task creation:", task_res)
            task_id = task_res.get("task_id", "TASK-0000")
            
            # 模拟任务派发到processing阶段
            disp_res = await session.call_tool("dispatch_task", {"task_id": task_id, "next_step": "processing"})
            print("[Client] Task dispatch:", disp_res)
            
            # 模拟任务完成
            comp_res = await session.call_tool("complete_task", {"task_id": task_id})
            print("[Client] Task completion:", comp_res)
            
            # 查看任务最终状态（此处假设另有show_task工具，示例中直接打印TASK_DB内容）
            # 为演示，调用complete_task返回的日志已包含状态信息

async def main():
    await run_client()

if __name__ == "__main__":
    asyncio.run(main())



# 【例10-7】
# -------------------( Dockerfile )-------------------
#   mock Dockerfile for building an MCP content classification service
DOCKERFILE_CONTENT = r'''
# Using Python 3.9 as base
FROM python:3.9-slim

WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
CMD ["python", "mcp_server.py"]
'''

# -------------------( Knative Service )-------------------
#   mock YAML for serverless deployment in K8s with Knative
KNATIVE_SERVICE_YAML = r'''
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mcp-content-classifier
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/class: kpa.autoscaling.knative.dev
        autoscaling.knative.dev/metric: "concurrency"
        autoscaling.knative.dev/target: "1"
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "5"
    spec:
      containers:
        - image: myrepo/mcp-content-classifier:latest
          ports:
            - containerPort: 8080
          env:
            - name: ENV
              value: "production"
'''

# -------------------( mcp_server.py )-------------------
#   MCP服务器代码, 提供一个内容分类Tool
import time
import random
import asyncio
import mcp
from mcp.server import FastMCP
from mcp.server.http import http_server

app = FastMCP("content-classifier")

MOCK_CATEGORIES = ["Sports", "Finance", "Technology", "Health", "Entertainment"]

@app.tool()
def classify_content(text: str) -> dict:
    """
    内容分类, mock随机分配一个类别
    """
    category = random.choice(MOCK_CATEGORIES)
    return {"category": category, "original_text": text, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

@app.tool()
def service_status() -> dict:
    """
    查看服务状态
    """
    return {"status": "running", "uptime": time.strftime("%H:%M:%S")}

async def run_mcp_server():
    print("[Server] MCP Content Classifier starting, listening on 8080")
    # use HTTP server for demonstration
    await app.run_http(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    asyncio.run(run_mcp_server())

# -------------------( client.py )-------------------
#   客户端测试脚本, 调用classify_content多次以观察Knative自动扩缩情况
#   场景新颖：模拟高并发请求, 观察serverless弹性
import os
import time
import json
import random
import asyncio
from mcp.client.http import http_client
from mcp import ClientSession

TEST_TEXTS = [
    "A new achievement in football",
    "Stock markets are volatile",
    "Quantum computing revolution",
    "Tips for healthy diet",
    "Box office hits this summer"
]

async def run_load_test(server_url: str, concurrency: int, requests_per_worker: int):
    print(f"[Client] Starting load test with concurrency={concurrency}, requests_per_worker={requests_per_worker}")
    async def worker_task(worker_id: int):
        async with http_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for i in range(requests_per_worker):
                    text = random.choice(TEST_TEXTS)
                    res = await session.call_tool("classify_content", {"text": text})
                    print(f"[Worker {worker_id}] classification result:", res)
                    await asyncio.sleep(0.2)

    tasks = []
    for w in range(concurrency):
        tasks.append(asyncio.create_task(worker_task(w)))
    await asyncio.gather(*tasks)
    print("[Client] Load test finished")

if __name__ == "__main__":
    # Suppose Knative domain is assigned as below
    # In real scenario: http://mcp-content-classifier.default.1.2.3.4.sslip.io or so
    server_url = "http://localhost:8080"
    asyncio.run(run_load_test(server_url, concurrency=3, requests_per_worker=5))