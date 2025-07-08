# 【例5-1】
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import random
import time

# 模拟MCP核心API模块
class MCPClient:
    def __init__(self, server_url):
        # 初始化MCP客户端实例，设定服务器URL
        self.server_url = server_url
        self.session_id = random.randint(1000, 9999)
        self.context = {}  # 用于存储上下文Slot

    async def initialize(self):
        # 模拟客户端初始化，与服务器建立连接
        print(f"初始化 MCP 客户端，连接到服务器: {self.server_url}")
        await asyncio.sleep(0.1)  # 模拟网络延时
        print("初始化完成。")

    async def list_resources(self):
        # 模拟调用服务器的 list_resources 接口
        print("调用 list_resources API...")
        await asyncio.sleep(0.1)
        resources = [
            {"uri": "resource://exchange_rate", "name": "汇率数据", "version": "1.0.0"},
            {"uri": "resource://payment_fee", "name": "手续费数据", "version": "1.0.0"}
        ]
        print("返回资源列表:")
        print(json.dumps(resources, indent=2, ensure_ascii=False))
        return resources

    async def read_resource(self, uri):
        # 模拟读取指定资源的内容
        print(f"读取资源: {uri}")
        await asyncio.sleep(0.1)
        if uri == "resource://exchange_rate":
            # 模拟返回汇率数据
            data = {"USD_CNY": 6.45, "EUR_CNY": 7.80}
        elif uri == "resource://payment_fee":
            data = {"credit_card_fee": 0.03, "paypal_fee": 0.05}
        else:
            data = {}
        print("资源内容:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data

    async def call_tool(self, tool_name, params):
        # 模拟调用工具 API
        print(f"调用工具: {tool_name}，参数: {params}")
        await asyncio.sleep(0.2)  # 模拟工具执行延时
        if tool_name == "calculate_payment":
            # 根据汇率和手续费计算支付金额
            amount = params.get("amount", 0)
            exchange_rate = params.get("exchange_rate", 1)
            fee_rate = params.get("fee_rate", 0)
            net_amount = amount * exchange_rate * (1 - fee_rate)
            result = {"net_amount": net_amount, "currency": "CNY"}
        else:
            result = {"error": "Unknown tool"}
        print("工具调用返回:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    async def update_context(self, key, value):
        # 更新本地上下文状态
        self.context[key] = value
        print(f"上下文更新: {key} -> {value}")

    async def invoke(self, method, params):
        # 模拟通用API调用（请求与响应封装）
        request = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 10000),
            "method": method,
            "params": params
        }
        print(f"发送请求: {json.dumps(request, indent=2, ensure_ascii=False)}")
        await asyncio.sleep(0.1)
        # 模拟响应逻辑
        if method == "process_payment":
            # 调用支付处理工具，整合上下文数据
            result = {"status": "success", "details": "Payment processed successfully."}
        else:
            result = {"error": "Method not found"}
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": result
        }
        print("收到响应:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return response

# 模拟支付业务中的核心流程：读取资源、调用工具、更新上下文、发送支付请求
async def main():
    # 初始化 MCP 客户端实例
    client = MCPClient("https://mcp.payment.example.com")
    await client.initialize()

    # 列出服务器资源，获取汇率和手续费数据
    resources = await client.list_resources()

    # 读取汇率数据
    exchange_data = await client.read_resource("resource://exchange_rate")
    # 读取手续费数据
    fee_data = await client.read_resource("resource://payment_fee")

    # 更新本地上下文，存储资源数据
    await client.update_context("exchange_rate", exchange_data["USD_CNY"])
    await client.update_context("fee_rate", fee_data["credit_card_fee"])

    # 调用支付计算工具：计算支付金额
    tool_params = {
        "amount": 100,  # 假设支付原始金额为 100 美元
        "exchange_rate": client.context.get("exchange_rate", 1),
        "fee_rate": client.context.get("fee_rate", 0)
    }
    tool_result = await client.call_tool("calculate_payment", tool_params)
    await client.update_context("payment_result", tool_result)

    # 发起支付处理请求，整合上下文数据
    invoke_params = {
        "session": {
            "client_id": "client_001",
            "context": client.context
        },
        "order": {
            "order_id": "order_123456",
            "amount": 100
        }
    }
    response = await client.invoke("process_payment", invoke_params)
    print("最终支付处理响应:")
    print(json.dumps(response, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())



# 【例5-2】
import asyncio
import json
import random
import time
from typing import Any, Dict, List

# =========================
# MCP 服务器端实现
# =========================

class CustomResourceHook:
    """
    自定义资源访问钩子，用于在访问资源前后执行额外逻辑
    例如权限验证、缓存处理、日志审计等
    """
    def __init__(self, resource_name: str):
        self.resource_name = resource_name

    def before_read(self, context: Dict[str, Any]) -> None:
        """
        在读取资源前的回调，可进行权限校验或参数检查
        """
        user_role = context.get("user_role", "guest")
        if user_role not in ["admin", "manager"]:
            raise PermissionError(f"用户角色 {user_role} 无权访问资源 {self.resource_name}")

    def after_read(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        在读取资源后，对返回的数据做二次处理或审计记录
        """
        # 简化：此处仅打印日志
        print(f"资源 {self.resource_name} 读取成功，数据条目数: {len(data)}")
        return data

class ShippingCalculator:
    """
    自定义工具：计算跨境电商的配送费用与到达时效
    """
    def __init__(self):
        self.base_rate = 10.0  # 基础配送费
        self.weight_rate = 2.0 # 每kg的费用

    def calculate_shipping(self, destination: str, weight_kg: float) -> Dict[str, Any]:
        """
        返回运费和预计时效
        """
        if destination == "domestic":
            cost = self.base_rate + weight_kg * self.weight_rate
            eta_days = 3
        else:
            # 国际配送
            cost = self.base_rate * 2 + weight_kg * self.weight_rate * 1.5
            eta_days = 10
        return {
            "cost": round(cost, 2),
            "eta_days": eta_days,
            "destination": destination
        }

class MCPServer:
    """
    模拟的MCP服务器，支持自定义工具与资源访问钩子
    """
    def __init__(self):
        self.inventory_hook = CustomResourceHook("inventory")
        self.shipping_calc = ShippingCalculator()

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据method分发给对应的处理函数
        """
        method = request.get("method")
        params = request.get("params", {})
        if method == "read_resource":
            return await self._read_resource(params)
        elif method == "call_tool":
            return await self._call_tool(params)
        elif method == "inject_context":
            return await self._inject_context(params)
        else:
            return {"error": f"Unknown method {method}"}

    async def _read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri", "")
        context = params.get("context", {})
        # 检测资源钩子
        if "inventory" in uri:
            # 读取前置操作
            self.inventory_hook.before_read(context)
        # 模拟资源数据
        resource_data = {
            "iphone13": 25,
            "galaxyS22": 40,
            "macbookAir": 10
        }
        if "inventory" in uri:
            resource_data = self.inventory_hook.after_read(resource_data)
        return resource_data

    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("tool_name", "")
        tool_params = params.get("tool_params", {})
        if tool_name == "shipping_calc":
            destination = tool_params.get("destination", "domestic")
            weight_kg = tool_params.get("weight_kg", 1.0)
            result = self.shipping_calc.calculate_shipping(destination, weight_kg)
            return result
        else:
            return {"error": "Tool not found"}

    async def _inject_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        context_key = params.get("key", "")
        context_value = params.get("value", "")
        # 模拟对上下文的处理，可以存储到Server的Session等
        return {"updated": True, "key": context_key, "value": context_value}

# =========================
# MCP 客户端实现
# =========================

class MCPClient:
    """
    自定义客户端：支持对MCPServer的调用，可扩展错误处理与上下文管理
    """
    def __init__(self, server: MCPServer):
        self.server = server
        self.local_context = {}

    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送请求到MCP服务器，并获取响应
        可自定义错误捕获与重试等逻辑
        """
        request = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 99999),
            "method": method,
            "params": params
        }
        print(f"[Client] 发送请求: {json.dumps(request, indent=2, ensure_ascii=False)}")
        response = await self.server.handle_request(request)
        print(f"[Client] 收到响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        return response

    async def read_inventory(self):
        """
        读取库存资源并存储于本地上下文
        """
        params = {
            "uri": "resource://inventory",
            "context": {"user_role": "manager"}  # 仅manager可访问
        }
        res = await self.send_request("read_resource", params)
        if "error" not in res:
            self.local_context["inventory"] = res
        else:
            print("[Client] 读取库存失败，执行错误处理")

    async def calc_shipping(self, destination: str, weight: float):
        """
        调用自定义工具进行运费与时效计算
        """
        params = {
            "tool_name": "shipping_calc",
            "tool_params": {
                "destination": destination,
                "weight_kg": weight
            }
        }
        res = await self.send_request("call_tool", params)
        return res

    async def inject_local_context(self, key: str, value: Any):
        """
        将本地上下文注入到Server的上下文中
        """
        params = {"key": key, "value": value}
        res = await self.send_request("inject_context", params)
        return res

# =========================
# 演示主流程
# =========================

async def main():
    # 初始化服务器与客户端
    server = MCPServer()
    client = MCPClient(server)

    # 读取库存资源
    await client.read_inventory()

    # 显示本地缓存的库存信息
    print("[Client] 本地上下文库存:", client.local_context.get("inventory", {}))

    # 模拟计算国内运费
    domestic_res = await client.calc_shipping("domestic", 2.5)
    print("[Client] 国内运费计算结果:", domestic_res)

    # 模拟计算国际运费
    international_res = await client.calc_shipping("international", 5.0)
    print("[Client] 国际运费计算结果:", international_res)

    # 向服务器注入一个key-value上下文
    context_inject_res = await client.inject_local_context("promotion_code", "VIP2025")
    print("[Client] 上下文注入结果:", context_inject_res)

    # 再次读取库存资源，这次模拟切换用户角色(guest) 无访问权限
    params = {
        "uri": "resource://inventory",
        "context": {"user_role": "guest"}
    }
    await client.send_request("read_resource", params)


if __name__ == "__main__":
    asyncio.run(main())
