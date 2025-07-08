# 【例8-1】
import os
import time
import json
import random
import asyncio
from typing import Dict, Any

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 全局数据结构，模拟Agent状态存储
AGENT_STATE_DB: Dict[str, Dict[str, Any]] = {
    "raw_material_agent": {
        "agent": "raw_material_agent",
        "status": "idle",
        "task_id": None,
        "last_update": None
    },
    "assembly_agent": {
        "agent": "assembly_agent",
        "status": "idle",
        "task_id": None,
        "last_update": None
    },
    "quality_agent": {
        "agent": "quality_agent",
        "status": "idle",
        "task_id": None,
        "last_update": None
    },
    "shipping_agent": {
        "agent": "shipping_agent",
        "status": "idle",
        "task_id": None,
        "last_update": None
    }
}

# 模拟已存在的订单或任务
TASK_DB: Dict[str, Dict[str, Any]] = {}

app = FastMCP("factory-agent-server")

def _update_agent_state(agent_id: str, status: str, task_id: str):
    """
    内部辅助函数，用于更新AGENT_STATE_DB
    """
    if agent_id not in AGENT_STATE_DB:
        raise ValueError(f"Invalid agent_id={agent_id}")
    AGENT_STATE_DB[agent_id]["status"] = status
    AGENT_STATE_DB[agent_id]["task_id"] = task_id
    AGENT_STATE_DB[agent_id]["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")

@app.tool()
def tool_create_task(order_id: str) -> Dict[str, Any]:
    """
    工具函数: 创建一项生产任务, 并分配给raw_material_agent进入原料处理阶段
    """
    if order_id in TASK_DB:
        return {"error": f"Task for order {order_id} already exists"}
    task_id = f"TASK-{random.randint(1000,9999)}"
    TASK_DB[order_id] = {
        "task_id": task_id,
        "order_id": order_id,
        "stage": "RAW_MATERIAL",
        "progress": "pending",
        "log": []
    }
    # 分配给raw_material_agent
    _update_agent_state("raw_material_agent", "busy", task_id)
    TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - raw_material_agent assigned.")
    return {"task_id": task_id, "order_id": order_id, "stage": "RAW_MATERIAL"}

@app.tool()
def tool_update_raw_material(order_id: str) -> Dict[str, Any]:
    """
    工具函数: 模拟原料处理完成, 将raw_material_agent置为idle, 并将任务推进到assembly_agent
    """
    if order_id not in TASK_DB:
        return {"error": "No such task"}
    if TASK_DB[order_id]["stage"] != "RAW_MATERIAL":
        return {"error": f"Task stage mismatch, current={TASK_DB[order_id]['stage']}"}
    # 更新raw_material_agent状态
    _update_agent_state("raw_material_agent", "idle", None)
    # 分配给assembly_agent
    _update_agent_state("assembly_agent", "busy", TASK_DB[order_id]["task_id"])
    TASK_DB[order_id]["stage"] = "ASSEMBLY"
    TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - raw_material_agent done, assembly_agent assigned.")
    return {"order_id": order_id, "new_stage": "ASSEMBLY"}

@app.tool()
def tool_assembly_done(order_id: str) -> Dict[str, Any]:
    """
    工具函数: 模拟组装完成, 将assembly_agent置为idle, 并将任务推进到quality_agent
    """
    if order_id not in TASK_DB:
        return {"error": "No such task"}
    if TASK_DB[order_id]["stage"] != "ASSEMBLY":
        return {"error": f"Task stage mismatch, current={TASK_DB[order_id]['stage']}"}
    _update_agent_state("assembly_agent", "idle", None)
    _update_agent_state("quality_agent", "busy", TASK_DB[order_id]["task_id"])
    TASK_DB[order_id]["stage"] = "QUALITY"
    TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - assembly_agent done, quality_agent assigned.")
    return {"order_id": order_id, "new_stage": "QUALITY"}

@app.tool()
def tool_quality_check(order_id: str, pass_check: bool) -> Dict[str, Any]:
    """
    工具函数: 模拟质检操作, 质检通过则转给shipping_agent进行发货, 不通过则返回错误
    """
    if order_id not in TASK_DB:
        return {"error": "No such task"}
    if TASK_DB[order_id]["stage"] != "QUALITY":
        return {"error": f"Task stage mismatch, current={TASK_DB[order_id]['stage']}"}
    _update_agent_state("quality_agent", "idle", None)
    if not pass_check:
        TASK_DB[order_id]["progress"] = "failed"
        TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - quality_agent failed check.")
        return {"order_id": order_id, "error": "Quality check failed"}
    _update_agent_state("shipping_agent", "busy", TASK_DB[order_id]["task_id"])
    TASK_DB[order_id]["stage"] = "SHIPPING"
    TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - quality_agent done, shipping_agent assigned.")
    return {"order_id": order_id, "new_stage": "SHIPPING"}

@app.tool()
def tool_ship_order(order_id: str) -> Dict[str, Any]:
    """
    工具函数: 模拟发货流程, 将shipping_agent置为idle, 任务标记为completed
    """
    if order_id not in TASK_DB:
        return {"error": "No such task"}
    if TASK_DB[order_id]["stage"] != "SHIPPING":
        return {"error": f"Task stage mismatch, current={TASK_DB[order_id]['stage']}"}
    _update_agent_state("shipping_agent", "idle", None)
    TASK_DB[order_id]["progress"] = "completed"
    TASK_DB[order_id]["log"].append(f"{time.strftime('%H:%M:%S')} - shipping_agent finished shipping.")
    return {"order_id": order_id, "status": "completed"}

@app.tool()
def tool_check_agent_state(agent_id: str) -> Dict[str, Any]:
    """
    工具函数: 查询指定agent的当前状态
    """
    if agent_id not in AGENT_STATE_DB:
        return {"error": "agent_not_found"}
    return AGENT_STATE_DB[agent_id]

@app.tool()
def tool_check_task(order_id: str) -> Dict[str, Any]:
    """
    工具函数: 查询当前订单的任务状态
    """
    if order_id not in TASK_DB:
        return {"error": "task_not_found"}
    return TASK_DB[order_id]

############# MCP服务器与客户端演示 #############

async def run_server():
    print("=== MCP服务器(factory-agent-server)启动... ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待3秒后再连接... ===")
    await asyncio.sleep(3)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化客户端完成...")
            await session.initialize()

            # Step1: 创建Task
            order_id = "ORDER-ABC123"
            create_res = await session.call_tool("tool_create_task", {
                "order_id": order_id
            })
            print("[Client] 创建任务结果:", create_res)

            # Step2: 原料处理完成
            raw_res = await session.call_tool("tool_update_raw_material", {
                "order_id": order_id
            })
            print("[Client] 原料处理结果:", raw_res)

            # Step3: 组装完成
            asm_res = await session.call_tool("tool_assembly_done", {
                "order_id": order_id
            })
            print("[Client] 组装结果:", asm_res)

            # Step4: 质检
            qlty_res = await session.call_tool("tool_quality_check", {
                "order_id": order_id,
                "pass_check": True
            })
            print("[Client] 质检结果:", qlty_res)

            # Step5: 发货
            ship_res = await session.call_tool("tool_ship_order", {
                "order_id": order_id
            })
            print("[Client] 发货结果:", ship_res)

            # Step6: 查询某个Agent状态
            state_res = await session.call_tool("tool_check_agent_state", {
                "agent_id": "shipping_agent"
            })
            print("[Client] 查询shipping_agent状态:", state_res)

            # Step7: 最终查看订单任务状态
            task_res = await session.call_tool("tool_check_task", {
                "order_id": order_id
            })
            print("[Client] 订单任务完整状态:", task_res)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例8-2】
import json
import time

# MCP上下文存储
context_store = {}

def update_context(user_id, slot, value):
    """
    更新用户的上下文信息。
    """
    if user_id not in context_store:
        context_store[user_id] = {}
    context_store[user_id][slot] = value

def get_context(user_id, slot):
    """
    获取用户的上下文信息。
    """
    return context_store.get(user_id, {}).get(slot, None)

def recognize_intent(user_input):
    """
    简单的意图识别函数。
    """
    if "打开" in user_input and "灯" in user_input:
        return "turn_on_light"
    elif "播放" in user_input and "音乐" in user_input:
        return "play_music"
    else:
        return "unknown"

def generate_plan(intent):
    """
    根据意图生成执行计划。
    """
    if intent == "turn_on_light":
        return ["check_light_status", "send_turn_on_command"]
    elif intent == "play_music":
        return ["check_speaker_status", "send_play_command"]
    else:
        return []

def execute_plan(plan):
    """
    执行生成的计划。
    """
    for action in plan:
        if action == "check_light_status":
            print("检查灯的状态...")
            time.sleep(1)
            print("灯处于关闭状态。")
        elif action == "send_turn_on_command":
            print("发送开灯指令...")
            time.sleep(1)
            print("灯已打开。")
        elif action == "check_speaker_status":
            print("检查音响的状态...")
            time.sleep(1)
            print("音响处于空闲状态。")
        elif action == "send_play_command":
            print("发送播放音乐指令...")
            time.sleep(1)
            print("音乐开始播放。")
        else:
            print(f"未知的动作：{action}")

# 模拟用户交互
user_id = "user_001"
user_input = "请帮我打开客厅的灯。"

# 更新上下文
update_context(user_id, "last_command", user_input)

# 意图识别
intent = recognize_intent(user_input)
print(f"识别的意图：{intent}")

# 计划生成
plan = generate_plan(intent)
print(f"生成的计划：{plan}")

# 执行计划
execute_plan(plan)



# 【例8-3】
import os
import json
import time
import random
import asyncio
from typing import Dict, Any

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

############## 全局数据结构 ##############
TASK_DB: Dict[str, Dict[str, Any]] = {}
# 每个任务: { "task_id":..., "status":..., "slots":..., "log":[], ...}

DRONE_STATE_DB: Dict[str, Dict[str, Any]] = {
    # 模拟多台无人机状态
    "drone_001": {"drone_id": "drone_001", "status": "idle", "current_task": None},
    "drone_002": {"drone_id": "drone_002", "status": "idle", "current_task": None},
}

############## MCP服务器定义 ##############
app = FastMCP("drone-farm-server")

def _update_drone_state(drone_id: str, new_status: str, task_id: str = None):
    if drone_id not in DRONE_STATE_DB:
        raise ValueError("Invalid drone_id")
    DRONE_STATE_DB[drone_id]["status"] = new_status
    DRONE_STATE_DB[drone_id]["current_task"] = task_id

def _append_task_log(task_id: str, message: str):
    if task_id in TASK_DB:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        TASK_DB[task_id]["log"].append(f"{now} - {message}")

@app.tool()
def tool_create_scan_task(field_location: str, drone_id: str) -> Dict[str, Any]:
    """
    创建巡检任务, 将任务状态置为 PREPARATION
    并分配给指定无人机
    """
    task_id = f"SCAN-{random.randint(1000,9999)}"
    TASK_DB[task_id] = {
        "task_id": task_id,
        "status": "PREPARATION",
        "field_location": field_location,
        "log": []
    }
    _append_task_log(task_id, f"Task created for field={field_location}, assigned to drone={drone_id}")
    _update_drone_state(drone_id, "busy", task_id)
    return {"task_id": task_id, "status": "PREPARATION", "drone": drone_id}

@app.tool()
def tool_task_preparation(task_id: str, drone_id: str) -> Dict[str, Any]:
    """
    执行任务准备操作, 将状态从 PREPARATION 切换到 TAKEOFF
    """
    if task_id not in TASK_DB:
        return {"error": "Task not found"}
    if TASK_DB[task_id]["status"] != "PREPARATION":
        return {"error": f"Invalid status: {TASK_DB[task_id]['status']}, expected=PREPARATION"}
    # 模拟准备动作...
    time.sleep(1)
    TASK_DB[task_id]["status"] = "TAKEOFF"
    _append_task_log(task_id, f"Preparation done, next=TAKEOFF, drone={drone_id}")
    return {"task_id": task_id, "new_status": "TAKEOFF"}

@app.tool()
def tool_drone_takeoff(task_id: str, drone_id: str) -> Dict[str, Any]:
    """
    让无人机起飞, 状态切换到SCANNING
    """
    if task_id not in TASK_DB:
        return {"error": "Task not found"}
    if TASK_DB[task_id]["status"] != "TAKEOFF":
        return {"error": f"Invalid status: {TASK_DB[task_id]['status']}, expected=TAKEOFF"}
    # 模拟起飞动作...
    time.sleep(1)
    TASK_DB[task_id]["status"] = "SCANNING"
    _append_task_log(task_id, f"Drone took off, next=SCANNING, drone={drone_id}")
    return {"task_id": task_id, "new_status": "SCANNING"}

@app.tool()
def tool_drone_scanning(task_id: str, drone_id: str) -> Dict[str, Any]:
    """
    模拟农田巡检过程, 状态从SCANNING到PROCESSING
    """
    if task_id not in TASK_DB:
        return {"error": "Task not found"}
    if TASK_DB[task_id]["status"] != "SCANNING":
        return {"error": f"Invalid status: {TASK_DB[task_id]['status']}, expected=SCANNING"}
    # 模拟巡检扫描动作...
    time.sleep(2)
    TASK_DB[task_id]["status"] = "PROCESSING"
    _append_task_log(task_id, f"Scanning done, data collected, next=PROCESSING, drone={drone_id}")
    return {"task_id": task_id, "new_status": "PROCESSING"}

@app.tool()
def tool_data_processing(task_id: str, drone_id: str) -> Dict[str, Any]:
    """
    模拟图像/传感器数据处理, 状态从PROCESSING到REPORTING
    """
    if task_id not in TASK_DB:
        return {"error": "Task not found"}
    if TASK_DB[task_id]["status"] != "PROCESSING":
        return {"error": f"Invalid status: {TASK_DB[task_id]['status']}, expected=PROCESSING"}
    # 模拟处理过程...
    time.sleep(2)
    TASK_DB[task_id]["status"] = "REPORTING"
    _append_task_log(task_id, f"Data processing done, next=REPORTING, drone={drone_id}")
    return {"task_id": task_id, "new_status": "REPORTING"}

@app.tool()
def tool_generate_report(task_id: str, drone_id: str) -> Dict[str, Any]:
    """
    最终报告生成, 状态从REPORTING到DONE, drone可切回idle
    """
    if task_id not in TASK_DB:
        return {"error": "Task not found"}
    if TASK_DB[task_id]["status"] != "REPORTING":
        return {"error": f"Invalid status: {TASK_DB[task_id]['status']}, expected=REPORTING"}
    # 模拟报告生成...
    time.sleep(1)
    TASK_DB[task_id]["status"] = "DONE"
    _append_task_log(task_id, f"Report generated, status=DONE, drone={drone_id}")
    # 无人机空闲
    _update_drone_state(drone_id, "idle")
    return {"task_id": task_id, "status": "DONE"}

@app.tool()
def tool_show_task(task_id: str) -> Dict[str, Any]:
    """
    查看任务详情
    """
    if task_id not in TASK_DB:
        return {"error": "task_not_found"}
    return TASK_DB[task_id]

@app.tool()
def tool_show_drone(drone_id: str) -> Dict[str, Any]:
    """
    查看无人机状态
    """
    if drone_id not in DRONE_STATE_DB:
        return {"error": "drone_not_found"}
    return DRONE_STATE_DB[drone_id]

############### 服务器与客户端演示 ###############
async def run_server():
    print("=== MCP服务器(drone-farm-server)启动... ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待5秒后再连接... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化完成, 开始演示状态驱动任务流...")

            # 1. 创建巡检任务
            create_res = await session.call_tool("tool_create_scan_task", {
                "field_location": "Farm Sector A",
                "drone_id": "drone_001"
            })
            print("[Client] 创建任务:", create_res)
            task_id = create_res.get("task_id")

            # 2. 任务处于PREPARATION阶段
            prep_res = await session.call_tool("tool_task_preparation", {
                "task_id": task_id,
                "drone_id": "drone_001"
            })
            print("[Client] 任务准备:", prep_res)

            # 3. 让无人机起飞, 进入SCANNING阶段
            takeoff_res = await session.call_tool("tool_drone_takeoff", {
                "task_id": task_id,
                "drone_id": "drone_001"
            })
            print("[Client] 起飞:", takeoff_res)

            # 4. 执行SCANNING
            scan_res = await session.call_tool("tool_drone_scanning", {
                "task_id": task_id,
                "drone_id": "drone_001"
            })
            print("[Client] 扫描:", scan_res)

            # 5. 数据处理PROCESSING
            proc_res = await session.call_tool("tool_data_processing", {
                "task_id": task_id,
                "drone_id": "drone_001"
            })
            print("[Client] 数据处理:", proc_res)

            # 6. 最终报告REPORTING -> DONE
            rep_res = await session.call_tool("tool_generate_report", {
                "task_id": task_id,
                "drone_id": "drone_001"
            })
            print("[Client] 生成报告:", rep_res)

            # 7. 查看任务详情
            show_task = await session.call_tool("tool_show_task", {
                "task_id": task_id
            })
            print("[Client] 任务详情:", show_task)

            # 8. 查看无人机状态
            show_drone = await session.call_tool("tool_show_drone", {
                "drone_id": "drone_001"
            })
            print("[Client] 无人机状态:", show_drone)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例8-4】
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

############### 全局数据结构 ###############
# 记录已注册的Agent
AGENT_DB: Dict[str, Dict[str, Any]] = {}
# 存储Agent之间的消息
# 格式: MESSAGES_DB[agent_id] = list of message dict
MESSAGES_DB: Dict[str, List[Dict[str, Any]]] = {}

app = FastMCP("agent-message-server")

def _init_agent_inbox(agent_id: str):
    """
    若对应Agent收件箱未初始化, 则创建空列表
    """
    if agent_id not in MESSAGES_DB:
        MESSAGES_DB[agent_id] = []

def _append_message(receiver_id: str, msg: Dict[str, Any]):
    """
    向receiver_id的收件箱追加一条消息
    """
    _init_agent_inbox(receiver_id)
    MESSAGES_DB[receiver_id].append(msg)

@app.tool()
def tool_register_agent(agent_id: str, description: str) -> Dict[str, Any]:
    """
    注册Agent, 记录其ID与描述信息,
    并在MESSAGES_DB中初始化收件箱
    """
    if agent_id in AGENT_DB:
        return {"error": "Agent ID already registered"}
    AGENT_DB[agent_id] = {
        "agent_id": agent_id,
        "description": description,
        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _init_agent_inbox(agent_id)
    return {"message": f"Agent {agent_id} registered successfully"}

@app.tool()
def tool_list_agents() -> Dict[str, Any]:
    """
    查看所有已注册的Agent信息
    """
    return {"agents": list(AGENT_DB.values())}

@app.tool()
def tool_send_message(sender_id: str, receiver_id: str, content: str) -> Dict[str, Any]:
    """
    发送消息给另一个Agent, 存储到receiver的收件箱
    """
    if sender_id not in AGENT_DB:
        return {"error": f"Sender {sender_id} not registered"}
    if receiver_id not in AGENT_DB:
        return {"error": f"Receiver {receiver_id} not registered"}
    msg_id = f"msg-{random.randint(1000,9999)}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    new_msg = {
        "msg_id": msg_id,
        "from": sender_id,
        "to": receiver_id,
        "content": content,
        "timestamp": timestamp
    }
    _append_message(receiver_id, new_msg)
    return {"message": "Message sent", "msg_id": msg_id}

@app.tool()
def tool_fetch_inbox(agent_id: str) -> Dict[str, Any]:
    """
    查看Agent的收件箱消息列表
    """
    if agent_id not in AGENT_DB:
        return {"error": f"Agent {agent_id} not found"}
    msgs = MESSAGES_DB.get(agent_id, [])
    return {"agent_inbox": msgs}

@app.tool()
def tool_fetch_message_detail(agent_id: str, msg_id: str) -> Dict[str, Any]:
    """
    查看收件箱中具体某条消息的详情
    """
    if agent_id not in AGENT_DB:
        return {"error": f"Agent {agent_id} not found"}
    inbox = MESSAGES_DB.get(agent_id, [])
    for msg in inbox:
        if msg["msg_id"] == msg_id:
            return {"message_detail": msg}
    return {"error": "message_not_found"}

############### 服务器与客户端演示 ###############
async def run_server():
    print("=== MCP服务器(agent-message-server)启动... ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待5秒后连接... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化完成, 开始Agent-to-Agent消息协议演示")
            await session.initialize()

            # 1. 注册Agent alpha
            alpha_res = await session.call_tool("tool_register_agent", {
                "agent_id": "alpha",
                "description": "Primary Decision Maker"
            })
            print("[Client] 注册alpha结果:", alpha_res)

            # 2. 注册Agent bravo
            bravo_res = await session.call_tool("tool_register_agent", {
                "agent_id": "bravo",
                "description": "Secondary Executor Agent"
            })
            print("[Client] 注册bravo结果:", bravo_res)

            # 3. 查看所有Agent
            list_agents = await session.call_tool("tool_list_agents", {})
            print("[Client] 查看所有Agent:", list_agents)

            # 4. alpha 向 bravo 发送消息
            send_msg_1 = await session.call_tool("tool_send_message", {
                "sender_id": "alpha",
                "receiver_id": "bravo",
                "content": "Hello Bravo, please confirm readiness."
            })
            print("[Client] alpha->bravo消息:", send_msg_1)

            # 5. bravo 向 alpha 回复消息
            send_msg_2 = await session.call_tool("tool_send_message", {
                "sender_id": "bravo",
                "receiver_id": "alpha",
                "content": "Hi Alpha, I'm ready for instructions."
            })
            print("[Client] bravo->alpha消息:", send_msg_2)

            # 6. 检查 bravo 收件箱
            bravo_inbox = await session.call_tool("tool_fetch_inbox", {
                "agent_id": "bravo"
            })
            print("[Client] bravo收件箱:", bravo_inbox)

            # 7. 检查 alpha 收件箱
            alpha_inbox = await session.call_tool("tool_fetch_inbox", {
                "agent_id": "alpha"
            })
            print("[Client] alpha收件箱:", alpha_inbox)

            # 8. 查看 alpha收件箱第一条消息详情
            alpha_msgs = alpha_inbox.get("agent_inbox", [])
            if alpha_msgs:
                msg_detail = await session.call_tool("tool_fetch_message_detail", {
                    "agent_id": "alpha",
                    "msg_id": alpha_msgs[0]["msg_id"]
                })
                print("[Client] alpha第一条消息详情:", msg_detail)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例8-5】
import os
import time
import json
import random
import asyncio
from typing import Dict, Any

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# -------------- 全局存储结构 --------------
# order context slot, key=order_id, value=slot data
ORDER_SLOT_DB: Dict[str, Dict[str, Any]] = {}
# Agent注册信息
AGENT_DB: Dict[str, Dict[str, Any]] = {}

app = FastMCP("ecommerce-agent-server")

def ensure_slot(order_id: str):
    """
    若订单Slot尚未创建, 初始化之
    """
    if order_id not in ORDER_SLOT_DB:
        ORDER_SLOT_DB[order_id] = {
            "order_id": order_id,
            "items": [],       # 记录产品和数量
            "total_price": 0,
            "payment_status": "unpaid",
            "inventory_status": "not_reserved",
            "history": []
        }

def record_history(order_id: str, message: str):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    ORDER_SLOT_DB[order_id]["history"].append(f"{now} - {message}")

@app.tool()
def register_agent(agent_id: str, role: str) -> Dict[str, Any]:
    """
    注册Agent, 仅示例用, 记录Agent role等信息
    """
    if agent_id in AGENT_DB:
        return {"error": "Agent already registered"}
    AGENT_DB[agent_id] = {
        "agent_id": agent_id,
        "role": role,
        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"message": f"Agent {agent_id} with role={role} registered successfully"}

@app.tool()
def create_order(order_id: str) -> Dict[str, Any]:
    """
    创建订单Slot, 并初始化状态
    """
    if order_id in ORDER_SLOT_DB:
        return {"error": f"OrderSlot {order_id} already exists"}
    ensure_slot(order_id)
    record_history(order_id, "Order created")
    return {"order_id": order_id, "status": "Slot created"}

@app.tool()
def add_item_to_order(order_id: str, product: str, quantity: int, price_each: float) -> Dict[str, Any]:
    """
    向订单中添加产品, 累加total_price
    """
    if order_id not in ORDER_SLOT_DB:
        return {"error": "Order not found"}
    ORDER_SLOT_DB[order_id]["items"].append({
        "product": product,
        "quantity": quantity,
        "price_each": price_each
    })
    old_price = ORDER_SLOT_DB[order_id]["total_price"]
    new_price = old_price + quantity * price_each
    ORDER_SLOT_DB[order_id]["total_price"] = new_price
    record_history(order_id, f"Added item {product}, quantity={quantity}, new total={new_price}")
    return {
        "order_id": order_id,
        "items_count": len(ORDER_SLOT_DB[order_id]["items"]),
        "total_price": new_price
    }

@app.tool()
def inventory_reserve(agent_id: str, order_id: str) -> Dict[str, Any]:
    """
    inventory_agent调用, 预留库存, 更新OrderSlot中inventory_status
    """
    if agent_id not in AGENT_DB or AGENT_DB[agent_id]["role"] != "inventory":
        return {"error": "Agent not authorized or not found"}
    if order_id not in ORDER_SLOT_DB:
        return {"error": "Order not found"}
    if ORDER_SLOT_DB[order_id]["inventory_status"] != "not_reserved":
        return {"error": f"Inventory already reserved or invalid status={ORDER_SLOT_DB[order_id]['inventory_status']}"}
    # 模拟检查库存逻辑
    time.sleep(1)
    ORDER_SLOT_DB[order_id]["inventory_status"] = "reserved"
    record_history(order_id, f"Inventory reserved by {agent_id}")
    return {"order_id": order_id, "inventory_status": "reserved"}

@app.tool()
def payment_charge(agent_id: str, order_id: str) -> Dict[str, Any]:
    """
    payment_agent调用, 扣款并更新OrderSlot中payment_status
    """
    if agent_id not in AGENT_DB or AGENT_DB[agent_id]["role"] != "payment":
        return {"error": "Agent not authorized or not found"}
    if order_id not in ORDER_SLOT_DB:
        return {"error": "Order not found"}
    if ORDER_SLOT_DB[order_id]["payment_status"] != "unpaid":
        return {"error": f"Payment already done or invalid status={ORDER_SLOT_DB[order_id]['payment_status']}"}
    # 模拟扣款逻辑
    time.sleep(1)
    ORDER_SLOT_DB[order_id]["payment_status"] = "paid"
    record_history(order_id, f"Payment done by {agent_id}")
    return {"order_id": order_id, "payment_status": "paid"}

@app.tool()
def complete_order(order_id: str) -> Dict[str, Any]:
    """
    最后完成订单, inventory_status应为reserved, payment_status应为paid
    """
    if order_id not in ORDER_SLOT_DB:
        return {"error": "Order not found"}
    slot = ORDER_SLOT_DB[order_id]
    if slot["inventory_status"] != "reserved":
        return {"error": "Cannot complete, inventory not reserved"}
    if slot["payment_status"] != "paid":
        return {"error": "Cannot complete, payment not done"}
    record_history(order_id, "Order completed successfully")
    return {"order_id": order_id, "final_status": "completed"}

@app.tool()
def show_order_slot(order_id: str) -> Dict[str, Any]:
    """
    查看订单Slot所有信息
    """
    if order_id not in ORDER_SLOT_DB:
        return {"error": "Order not found"}
    return ORDER_SLOT_DB[order_id]

################# 服务器与客户端演示 #################
async def run_server():
    print("=== MCP服务器(ecommerce-agent-server)启动... ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待5秒后开始连接... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化完成, 开始跨Agent上下文协同Slot绑定演示")
            await session.initialize()

            # 1. 注册inventory_agent
            inv_reg = await session.call_tool("register_agent", {
                "agent_id": "inventory_agent",
                "role": "inventory"
            })
            print("[Client] 注册inventory_agent:", inv_reg)

            # 2. 注册payment_agent
            pay_reg = await session.call_tool("register_agent", {
                "agent_id": "payment_agent",
                "role": "payment"
            })
            print("[Client] 注册payment_agent:", pay_reg)

            # 3. 创建订单Slot
            order_id = "ORDER-XYZ001"
            create_slot = await session.call_tool("create_order", {
                "order_id": order_id
            })
            print("[Client] 创建订单Slot:", create_slot)

            # 4. 添加多种商品到订单
            add_item1 = await session.call_tool("add_item_to_order", {
                "order_id": order_id,
                "product": "Book",
                "quantity": 2,
                "price_each": 10.0
            })
            print("[Client] 加入商品1:", add_item1)
            add_item2 = await session.call_tool("add_item_to_order", {
                "order_id": order_id,
                "product": "Pen",
                "quantity": 5,
                "price_each": 1.5
            })
            print("[Client] 加入商品2:", add_item2)

            # 5. inventory_agent 预留库存
            reserve_res = await session.call_tool("inventory_reserve", {
                "agent_id": "inventory_agent",
                "order_id": order_id
            })
            print("[Client] 库存预留:", reserve_res)

            # 6. payment_agent 支付扣款
            pay_res = await session.call_tool("payment_charge", {
                "agent_id": "payment_agent",
                "order_id": order_id
            })
            print("[Client] 支付扣款:", pay_res)

            # 7. 最终完成订单
            complete_res = await session.call_tool("complete_order", {
                "order_id": order_id
            })
            print("[Client] 完成订单:", complete_res)

            # 8. 查看订单Slot最终状态
            final_slot = await session.call_tool("show_order_slot", {
                "order_id": order_id
            })
            print("[Client] 查看订单Slot:", final_slot)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())