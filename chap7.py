# 【例7-1】
from mcp.server import FastMCP

app = FastMCP("hotel_booking_server")

# 定义Slot
app.slot("check_in_date")
app.slot("check_out_date")
app.slot("room_type")

@app.tool()
def book_hotel(check_in_date: str, check_out_date: str, room_type: str) -> str:
    # 模拟预订酒店的逻辑
    return f"Hotel booked from {check_in_date} to {check_out_date} for a {room_type} room."

# 在对话过程中填充Slot
app.set_slot("check_in_date", "2025-06-01")
app.set_slot("check_out_date", "2025-06-05")
app.set_slot("room_type", "Deluxe")

# 调用工具时，自动从Slot中获取参数
response = app.call_tool("book_hotel")
print(response)  # 输出：Hotel booked from 2025-06-01 to 2025-06-05 for a Deluxe room.



# 【例7-2】
import os
import time
import json
import random
import asyncio
from typing import Dict, List, Any

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 全局仓库记录，key为货物ID，value为属性字典
WAREHOUSE_DB: Dict[str, Dict[str, Any]] = {}

# ============ 服务器端逻辑 ============

app = FastMCP("warehouse-inventory-server")

@app.tool()
def add_product(product_id: str, name: str, quantity: int = 0) -> Dict[str, Any]:
    """
    新增货物记录工具：
      - 若product_id已存在，则返回错误
      - 否则在仓库DB中创建一条记录

    返回:
      {
        "status": "success" 或 "error",
        "message": 描述信息,
        "record": 新创建或已存在的货物记录
      }
    """
    if product_id in WAREHOUSE_DB:
        return {
            "status": "error",
            "message": f"Product {product_id} already exists",
            "record": WAREHOUSE_DB[product_id]
        }
    WAREHOUSE_DB[product_id] = {
        "product_id": product_id,
        "name": name,
        "quantity": quantity,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    return {
        "status": "success",
        "message": f"Product {product_id} added successfully",
        "record": WAREHOUSE_DB[product_id]
    }

@app.tool()
def restock_product(product_id: str, amount: int) -> Dict[str, Any]:
    """
    入库补货工具：
      - product_id 若不存在则返回错误
      - 否则给对应货物记录增加 amount 数量

    返回:
      {
        "status": "success" 或 "error",
        "message": 描述信息,
        "record": 更新后的货物记录
      }
    """
    if product_id not in WAREHOUSE_DB:
        return {
            "status": "error",
            "message": f"Product {product_id} not found"
        }
    old_qty = WAREHOUSE_DB[product_id]["quantity"]
    new_qty = old_qty + amount
    WAREHOUSE_DB[product_id]["quantity"] = new_qty
    return {
        "status": "success",
        "message": f"Restocked {product_id} by {amount}, old qty={old_qty}, new qty={new_qty}",
        "record": WAREHOUSE_DB[product_id]
    }

@app.tool()
def ship_product(product_id: str, amount: int) -> Dict[str, Any]:
    """
    发货工具：
      - product_id 若不存在则返回错误
      - 若库存不足则返回错误
      - 否则扣减库存并返回发货详情

    返回:
      {
        "status": "success" 或 "error",
        "message": 描述信息,
        "shipment_id": 唯一发货ID,
        "record": 更新后的货物记录
      }
    """
    if product_id not in WAREHOUSE_DB:
        return {
            "status": "error",
            "message": f"Product {product_id} not found"
        }
    current_qty = WAREHOUSE_DB[product_id]["quantity"]
    if amount > current_qty:
        return {
            "status": "error",
            "message": f"Insufficient stock for {product_id}, current={current_qty}, request={amount}"
        }
    shipment_id = f"SHIP-{random.randint(1000,9999)}"
    WAREHOUSE_DB[product_id]["quantity"] = current_qty - amount
    return {
        "status": "success",
        "message": f"Shipped {amount} of {product_id}, remaining={WAREHOUSE_DB[product_id]['quantity']}",
        "shipment_id": shipment_id,
        "record": WAREHOUSE_DB[product_id]
    }

@app.tool()
def check_inventory() -> Dict[str, List[Dict[str, Any]]]:
    """
    查看当前库存信息：
      - 返回所有产品的记录列表

    返回:
      {
        "products": [
          { "product_id": ..., "name": ..., "quantity": ..., ... },
          ...
        ]
      }
    """
    products_info = list(WAREHOUSE_DB.values())
    return {"products": products_info}

# ============ MCP服务器与客户端协同演示 ============

async def run_server():
    """
    以stdio方式启动MCP服务器
    """
    print("=== MCP服务器启动(warehouse-inventory-server) ===")
    app.run(transport="stdio")

async def run_client():
    """
    模拟客户端调用：添加货物、补货、发货及查看库存
    """
    print("=== 客户端等待3秒后开始连接... ===")
    await asyncio.sleep(3)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)],
    )
    async with stdio_client(server_params) as (read, write):
        # 建立会话
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[Client] 开始调用工具接口...")

            # Step1: 添加货物
            add_res = await session.call_tool("add_product", {
                "product_id": "p1001",
                "name": "Smartphone XS",
                "quantity": 20
            })
            print("[Client] 添加货物结果:", add_res)

            # Step2: 再次添加同ID货物，触发已存在错误
            add_res2 = await session.call_tool("add_product", {
                "product_id": "p1001",
                "name": "Smartphone XX",
                "quantity": 100
            })
            print("[Client] 再次添加同货物:", add_res2)

            # Step3: 补货
            restock_res = await session.call_tool("restock_product", {
                "product_id": "p1001",
                "amount": 5
            })
            print("[Client] 补货结果:", restock_res)

            # Step4: 发货
            shipment_res = await session.call_tool("ship_product", {
                "product_id": "p1001",
                "amount": 10
            })
            print("[Client] 发货结果:", shipment_res)

            # Step5: 发货时库存不足示例
            insufficient_res = await session.call_tool("ship_product", {
                "product_id": "p1001",
                "amount": 50
            })
            print("[Client] 发货不足示例:", insufficient_res)

            # Step6: 查看库存信息
            inv_res = await session.call_tool("check_inventory", {})
            print("[Client] 查看库存信息:", inv_res)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例7-3】
import asyncio
import os
import time
import random
import json
from typing import Dict, Any, List

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 模拟外部数据
VENUE_SCHEDULE = {
    "venue_001": {"name": "City Concert Hall", "available_dates": ["2025-07-01", "2025-07-05"]},
    "venue_002": {"name": "Downtown Theater", "available_dates": ["2025-07-03", "2025-07-10"]}
}

CELEBRITY_LIST = [
    {"name": "Alice Superstar", "date_available": "2025-07-05", "fee": 100000},
    {"name": "Bob Rockstar",  "date_available": "2025-07-03", "fee": 80000},
    {"name": "Charlie Dancer","date_available": "2025-07-05", "fee": 60000}
]

BIG_SCREEN_INFO = [
    {"id": "screenA", "rental_date": "2025-07-03", "price_per_day": 5000},
    {"id": "screenB", "rental_date": "2025-07-05", "price_per_day": 4500}
]

app = FastMCP("event-planner-server")

@app.tool()
def fetch_venue_schedule() -> Dict[str, Any]:
    """
    并行调用示例：获取场地日程
    返回值:
      {
        "venues": [
          {
            "id": ...,
            "name": ...,
            "available_dates": [...]
          }, ...
        ]
      }
    """
    # 模拟网络或数据库查询
    data_list = []
    for vid, info in VENUE_SCHEDULE.items():
        data_list.append({
            "id": vid,
            "name": info["name"],
            "available_dates": info["available_dates"]
        })
    return {"venues": data_list}

@app.tool()
def fetch_celebrities() -> Dict[str, Any]:
    """
    并行调用示例：获取嘉宾列表
    返回值:
      {
        "celebrities": [
          {
            "name": ...,
            "date_available": ...,
            "fee": ...
          }, ...
        ]
      }
    """
    data_list = []
    for celeb in CELEBRITY_LIST:
        data_list.append(celeb)
    return {"celebrities": data_list}

@app.tool()
def fetch_big_screen_info() -> Dict[str, Any]:
    """
    并行调用示例：获取大屏租赁信息
    返回值:
      {
        "screens": [
          {
            "id": ...,
            "rental_date": ...,
            "price_per_day": ...
          }, ...
        ]
      }
    """
    data_list = []
    for s in BIG_SCREEN_INFO:
        data_list.append(s)
    return {"screens": data_list}

@app.tool()
def finalize_plan(venue_id: str, date_chosen: str, celeb_name: str, screen_id: str) -> Dict[str, Any]:
    """
    串行调用示例：基于上一步选定的信息，最终生成活动策划方案
    返回值:
      {
        "status": "success" or "error",
        "message": "Final plan generated",
        "plan_detail": {
          "venue": ...,
          "date": ...,
          "celebrity": ...,
          "big_screen": ...
        }
      }
    """
    # 简化：只做字段组合
    plan_id = f"PLAN-{random.randint(1000,9999)}"
    return {
        "status": "success",
        "message": f"Plan {plan_id} is created successfully",
        "plan_detail": {
            "venue": venue_id,
            "date": date_chosen,
            "celebrity": celeb_name,
            "big_screen": screen_id
        }
    }

async def run_server():
    print("=== MCP服务器启动：Event Planner ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待3秒后开始连接... ===")
    await asyncio.sleep(3)

    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[Client] 初始化完毕，开始工具调用 (并行 + 串行)")

            # Step1: 并行调用3个工具：获取场地、嘉宾、大屏信息
            # 并行方法：使用 asyncio.gather 提升效率
            fetch_tasks = [
                session.call_tool("fetch_venue_schedule", {}),
                session.call_tool("fetch_celebrities", {}),
                session.call_tool("fetch_big_screen_info", {})
            ]
            results = await asyncio.gather(*fetch_tasks)
            # 分别解析
            venue_info = results[0]   # { "venues": [...] }
            celeb_info = results[1]   # { "celebrities": [...] }
            screen_info = results[2]  # { "screens": [...] }

            print("[Client] 并行获取场地:", venue_info)
            print("[Client] 并行获取嘉宾:", celeb_info)
            print("[Client] 并行获取大屏:", screen_info)

            # Step2: 串行调用：基于获取的并行结果，挑选场地/嘉宾/大屏后再调用 finalize_plan
            # 简化逻辑：选择场地venues[0], date=venues[0].available_dates[0], celeb=celebrities[0], screen=screens[0]
            chosen_venue = venue_info["venues"][0]["id"]
            chosen_date = venue_info["venues"][0]["available_dates"][0]
            chosen_celeb = celeb_info["celebrities"][0]["name"]
            chosen_screen = screen_info["screens"][0]["id"]

            finalize_res = await session.call_tool("finalize_plan", {
                "venue_id": chosen_venue,
                "date_chosen": chosen_date,
                "celeb_name": chosen_celeb,
                "screen_id": chosen_screen
            })
            print("[Client] 串行执行 finalize_plan 结果:", finalize_res)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例7-4】
"""
MCP协议电子邮件缓存业务场景示例。

该脚本同时包含：
1. MCP服务器端：提供工具函数 store_email 和 get_emails，用于缓存电子邮件并查询缓存。
2. 模拟客户端：演示调用工具，发送邮件存储请求和邮件查询请求。

运行方式：
python email_cache_mcp.py

输出示例展示了请求-响应流程和最终结果。
"""

import os
import asyncio
import json
import random
import time
from typing import Any, Dict, List

import mcp
import httpx

from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 全局邮件缓存结构，用于演示
EMAIL_CACHE: Dict[str, List[Dict[str, Any]]] = {
    # mailbox -> [ {id, subject, content, timestamp}, ... ]
}

# 创建 MCP服务器实例
app = FastMCP("email-cache-server")

@app.tool()
def store_email(mailbox: str, subject: str, content: str) -> Dict[str, Any]:
    """
    存储电子邮件内容到指定邮箱，返回存储后的邮件信息。

    Args:
        mailbox: 邮箱标识
        subject: 邮件主题
        content: 邮件正文

    Returns:
        包含邮件ID、主题、存储时间等信息的字典
    """
    # 若该邮箱不存在，则初始化
    if mailbox not in EMAIL_CACHE:
        EMAIL_CACHE[mailbox] = []

    email_id = f"mail_{random.randint(10000, 99999)}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 存储邮件内容
    EMAIL_CACHE[mailbox].append({
        "id": email_id,
        "subject": subject,
        "content": content,
        "timestamp": timestamp
    })
    return {
        "mailbox": mailbox,
        "id": email_id,
        "subject": subject,
        "timestamp": timestamp
    }

@app.tool()
def get_emails(mailbox: str, limit: int = 10) -> Dict[str, Any]:
    """
    获取指定邮箱最近几封邮件信息。

    Args:
        mailbox: 邮箱标识
        limit: 限制返回的邮件条数

    Returns:
        包含邮箱信息与邮件列表的字典
    """
    if mailbox not in EMAIL_CACHE:
        return {
            "mailbox": mailbox,
            "emails": []
        }
    # 取最新的 limit 封邮件
    emails = EMAIL_CACHE[mailbox][-limit:]
    return {
        "mailbox": mailbox,
        "emails": emails
    }

@app.tool()
def parse_email_content(mailbox: str, email_id: str) -> Dict[str, Any]:
    """
    解析指定邮箱中某封邮件的正文，模拟提取关键信息的逻辑。

    Args:
        mailbox: 邮箱标识
        email_id: 邮件ID

    Returns:
        包含提取结果的字典
    """
    if mailbox not in EMAIL_CACHE:
        return {"error": "mailbox_not_found"}
    for mail in EMAIL_CACHE[mailbox]:
        if mail["id"] == email_id:
            content = mail["content"]
            # 模拟解析，假设只提取关键词列表
            keywords = extract_keywords(content)
            return {
                "mailbox": mailbox,
                "email_id": email_id,
                "keywords": keywords
            }
    return {"error": "email_not_found"}

def extract_keywords(content: str) -> List[str]:
    """
    模拟内容解析，简单切词或正则拆分。
    这里只是演示，可扩展更复杂的NLP逻辑。
    """
    # 简单用空格或标点拆分
    raw_words = content.replace(",", "").replace(".", "").split()
    # 去重并简单过滤
    unique_words = list(set([w.lower() for w in raw_words if len(w) > 2]))
    return unique_words


# ============ 以下为启动服务器与模拟客户端请求的逻辑 ============

async def run_mcp_server():
    """
    以stdio方式启动MCP服务器
    """
    print("=== MCP服务器启动中，等待客户端连接... ===")
    app.run(transport="stdio")

async def run_mcp_client():
    """
    模拟客户端调用过程，向MCP服务器发送存储邮件、获取邮件与解析邮件的请求。
    """
    # 准备服务器调用参数
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)],
    )

    # 等待服务器启动稳定
    print("=== 客户端等待3秒后再启动... ===")
    await asyncio.sleep(3)

    print("=== 客户端开始连接MCP服务器... ===")
    async with stdio_client(server_params) as (read, write):
        # 建立MCP客户端会话
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()
            print("[Client] 初始化完成，开始调用工具...")

            # Step1: 存储若干封邮件
            mailbox = "inbox_userA"
            subjects = ["Meeting Schedule", "Welcome Offer", "Sale Notice"]
            contents = [
                "This is a notice about the meeting schedule, check details below.",
                "Hello there, we prepared a welcome offer for you, please review it!",
                "Huge discount on electronics, limited time only, best sale ever!"
            ]
            for i in range(len(subjects)):
                store_result = await session.call_tool("store_email", {
                    "mailbox": mailbox,
                    "subject": subjects[i],
                    "content": contents[i]
                })
                print(f"[Client] 存储邮件结果: {store_result}")

            # Step2: 获取最新邮件
            get_result = await session.call_tool("get_emails", {
                "mailbox": mailbox,
                "limit": 5
            })
            print("[Client] 获取邮件列表:", get_result)

            # Step3: 解析某封邮件内容
            if "emails" in get_result and len(get_result["emails"]) > 0:
                target_id = get_result["emails"][0]["id"]
                parse_res = await session.call_tool("parse_email_content", {
                    "mailbox": mailbox,
                    "email_id": target_id
                })
                print("[Client] 解析邮件内容:", parse_res)

async def main():
    """
    同时运行MCP服务器与客户端，演示完整请求-响应流程
    """
    # 同时运行服务器与客户端任务
    server_task = asyncio.create_task(run_mcp_server())
    client_task = asyncio.create_task(run_mcp_client())

    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例7-5】
import os
import time
import json
import random
import asyncio
from typing import Dict, Any, List

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 模拟多个微服务的内部数据
ORDER_DB: Dict[str, Dict[str, Any]] = {}
DELIVERY_DB: Dict[str, Dict[str, Any]] = {}
NOTIFICATION_EVENTS: List[Dict[str, Any]] = []

# 用于模拟Webhook事件推送
WEBHOOK_SUBSCRIBERS: List[str] = []

############## 微服务函数 ##############

def place_order(user_id: str, food_item: str, address: str) -> Dict[str, Any]:
    """
    订单服务(OrderService)：下单逻辑
    - 创建订单并存储在ORDER_DB
    - 返回订单ID、状态等
    """
    order_id = f"ORD-{random.randint(1000,9999)}"
    ORDER_DB[order_id] = {
        "order_id": order_id,
        "user_id": user_id,
        "food_item": food_item,
        "address": address,
        "status": "CREATED",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return ORDER_DB[order_id]

def dispatch_delivery(order_id: str) -> Dict[str, Any]:
    """
    配送服务(DeliveryService)：分配骑手并启动配送
    - 若订单存在且状态正确，则创建配送记录
    - 返回配送信息
    """
    if order_id not in ORDER_DB:
        return {"error": f"Order {order_id} not found"}
    if ORDER_DB[order_id]["status"] != "CREATED":
        return {"error": f"Order {order_id} status invalid for delivery"}
    ORDER_DB[order_id]["status"] = "DISPATCHING"
    delivery_id = f"DLV-{random.randint(1000,9999)}"
    DELIVERY_DB[delivery_id] = {
        "delivery_id": delivery_id,
        "order_id": order_id,
        "rider": f"Rider-{random.randint(100,999)}",
        "status": "ON_ROAD",
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return DELIVERY_DB[delivery_id]

def check_delivery(delivery_id: str) -> Dict[str, Any]:
    """
    配送服务(DeliveryService)：查询配送状态
    """
    if delivery_id not in DELIVERY_DB:
        return {"error": "delivery_not_found"}
    return DELIVERY_DB[delivery_id]

def notify_event(event_type: str, data: Dict[str, Any]) -> bool:
    """
    通知服务(NotifyService)：模拟Webhook事件推送
    - 订阅者列表在WEBHOOK_SUBSCRIBERS中
    - 事件发生时，将事件记录添加到NOTIFICATION_EVENTS
    - 不实际向外发送HTTP请求，仅记录发生的事件
    """
    event_record = {
        "type": event_type,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }
    NOTIFICATION_EVENTS.append(event_record)
    # 模拟向所有Webhook订阅者发送事件
    # In real scenario, we'd do HTTP POST to each subscriber
    return True

############## MCP服务器定义 ##############

app = FastMCP("food-delivery-server")

@app.tool()
def tool_subscribe_webhook(url: str) -> Dict[str, Any]:
    """
    工具：订阅Webhook事件
    - 将url加入WEBHOOK_SUBSCRIBERS列表，后续事件发生时可POST
    - 当前示例仅模拟记录
    """
    WEBHOOK_SUBSCRIBERS.append(url)
    return {"message": f"Subscribed {url} to Webhook events."}

@app.tool()
def tool_place_order(user_id: str, food_item: str, address: str) -> Dict[str, Any]:
    """
    工具：调用订单服务(OrderService)创建新订单，触发通知事件
    """
    order_info = place_order(user_id, food_item, address)
    if "order_id" in order_info:
        # 触发通知事件
        notify_event("ORDER_CREATED", order_info)
    return {"order_info": order_info}

@app.tool()
def tool_dispatch_delivery(order_id: str) -> Dict[str, Any]:
    """
    工具：调用配送服务(DeliveryService)分配骑手进行配送
    """
    delivery_info = dispatch_delivery(order_id)
    if "delivery_id" in delivery_info:
        notify_event("DELIVERY_STARTED", delivery_info)
    return {"delivery_info": delivery_info}

@app.tool()
def tool_check_delivery(delivery_id: str) -> Dict[str, Any]:
    """
    工具：调用配送服务查询配送状态
    """
    info = check_delivery(delivery_id)
    return {"delivery_status": info}

@app.tool()
def tool_list_events() -> Dict[str, Any]:
    """
    工具：查看所有已记录的通知事件(Webhook事件)
    """
    return {"notification_events": NOTIFICATION_EVENTS}
############## 模拟客户端 ##############
async def run_server():
    print("=== MCP服务器(food-delivery-server) 即将启动... ===")
    app.run(transport="stdio")
async def run_client():
    # 等待服务器就绪
    print("=== 客户端等待5秒后启动... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化客户端...")
            await session.initialize()
            print("[Client] 开始调用工具...")

            # 订阅Webhook
            sub_res = await session.call_tool("tool_subscribe_webhook", {
                "url": "http://example.com/webhook"
            })
            print("[Client] 订阅Webhook返回:", sub_res)

            # 下单
            order_res = await session.call_tool("tool_place_order", {
                "user_id": "USER_123",
                "food_item": "Pizza Pepperoni",
                "address": "1234 Elm Street"
            })
            print("[Client] 下单返回:", order_res)

            # 尝试进行配送
            if "order_info" in order_res and "order_id" in order_res["order_info"]:
                the_order_id = order_res["order_info"]["order_id"]
                dispatch_res = await session.call_tool("tool_dispatch_delivery", {
                    "order_id": the_order_id
                })
                print("[Client] 分配配送返回:", dispatch_res)

                # 查询配送状态
                if "delivery_info" in dispatch_res and "delivery_id" in dispatch_res["delivery_info"]:
                    the_dlv_id = dispatch_res["delivery_info"]["delivery_id"]
                    check_res = await session.call_tool("tool_check_delivery", {
                        "delivery_id": the_dlv_id
                    })
                    print("[Client] 查询配送返回:", check_res)

            # 查看当前所有通知事件
            ev_res = await session.call_tool("tool_list_events", {})
            print("[Client] 查询通知事件:", ev_res)


async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())