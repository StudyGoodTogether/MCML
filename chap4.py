# 【例4-1】
import mcp
import uuid

# 创建MCP客户端实例
client = mcp.Client("https://payment-gateway.example.com/mcp")

# 生成唯一的会话ID
session_id = str(uuid.uuid4())

# 初始化支付会话
init_response = client.send_request(
    method="session/initiate",
    params={
        "session_id": session_id,
        "user_id": "user_12345",
        "payment_method": "credit_card",
        "amount": 100.00,
        "currency": "USD"
    }
)

print(init_response)



# 【例4-2】
import asyncio
import json
import random

# 定义服务器支持的协议版本
SERVER_SUPPORTED_VERSIONS = ["1.0.0", "1.1.0", "2.0.0"]

class MCPServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info('peername')
        print(f"服务器：与客户端 {self.peername} 建立连接。")

    def data_received(self, data):
        message = data.decode()
        print(f"服务器：收到数据：{message}")
        try:
            request = json.loads(message)
            if request["method"] == "negotiate_version":
                self.handle_version_negotiation(request)
            else:
                self.send_error("未知的方法")
        except json.JSONDecodeError:
            self.send_error("无效的JSON格式")

    def handle_version_negotiation(self, request):
        client_versions = request.get("params", {}).get("versions", [])
        compatible_version = self.find_compatible_version(client_versions)
        if compatible_version:
            response = {
                "jsonrpc": "2.0",
                "result": {"version": compatible_version},
                "id": request.get("id")
            }
            print(f"服务器：协商出兼容的协议版本：{compatible_version}")
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": "没有兼容的协议版本"},
                "id": request.get("id")
            }
            print("服务器：没有找到兼容的协议版本")
        self.transport.write(json.dumps(response).encode())

    def find_compatible_version(self, client_versions):
        for version in client_versions:
            if version in SERVER_SUPPORTED_VERSIONS:
                return version
        return None

    def send_error(self, message):
        response = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": message},
            "id": None
        }
        self.transport.write(json.dumps(response).encode())

class MCPClient:
    def __init__(self, loop, server_host, server_port, supported_versions):
        self.loop = loop
        self.server_host = server_host
        self.server_port = server_port
        self.supported_versions = supported_versions

    async def negotiate_version(self):
        reader, writer = await asyncio.open_connection(self.server_host, self.server_port, loop=self.loop)
        request = {
            "jsonrpc": "2.0",
            "method": "negotiate_version",
            "params": {"versions": self.supported_versions},
            "id": random.randint(1, 1000)
        }
        print(f"客户端：发送版本协商请求：{request}")
        writer.write(json.dumps(request).encode())
        await writer.drain()
        response_data = await reader.read(1024)
        response = json.loads(response_data.decode())
        if "result" in response:
            negotiated_version = response["result"]["version"]
            print(f"客户端：协商出的协议版本为：{negotiated_version}")
        else:
            error_message = response.get("error", {}).get("message", "未知错误")
            print(f"客户端：版本协商失败，错误信息：{error_message}")
        writer.close()
        await writer.wait_closed()

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda: MCPServerProtocol(), '127.0.0.1', 8888)
    print("服务器：启动，等待客户端连接...")

    # 模拟客户端支持的协议版本
    client_supported_versions = ["1.1.0", "2.0.0", "2.1.0"]
    client = MCPClient(loop, '127.0.0.1', 8888, client_supported_versions)
    await client.negotiate_version()

    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())



# 【例4-3】
import asyncio
import json

# 定义服务器支持的能力
SERVER_CAPABILITIES = {
    "prompts": True,
    "resources": True,
    "tools": True,
    "logging": True,
    "experimental": False
}

class MCPServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info('peername')
        print(f"服务器：与客户端 {self.peername} 建立连接。")

    def data_received(self, data):
        message = data.decode()
        print(f"服务器：收到数据：{message}")
        try:
            request = json.loads(message)
            if request["method"] == "initialize":
                self.handle_initialize(request)
            else:
                self.send_error("未知的方法")
        except json.JSONDecodeError:
            self.send_error("无效的JSON格式")

    def handle_initialize(self, request):
        client_capabilities = request.get("params", {}).get("capabilities", {})
        negotiated_capabilities = self.negotiate_capabilities(client_capabilities)
        response = {
            "jsonrpc": "2.0",
            "result": {"capabilities": negotiated_capabilities},
            "id": request.get("id")
        }
        print(f"服务器：协商出的能力集：{negotiated_capabilities}")
        self.transport.write(json.dumps(response).encode())

    def negotiate_capabilities(self, client_capabilities):
        negotiated = {}
        for capability, supported in client_capabilities.items():
            if supported and SERVER_CAPABILITIES.get(capability, False):
                negotiated[capability] = True
            else:
                negotiated[capability] = False
        return negotiated

    def send_error(self, message):
        response = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": message},
            "id": None
        }
        self.transport.write(json.dumps(response).encode())

class MCPClient:
    def __init__(self, loop, server_host, server_port, capabilities):
        self.loop = loop
        self.server_host = server_host
        self.server_port = server_port
        self.capabilities = capabilities

    async def initialize(self):
        reader, writer = await asyncio.open_connection(self.server_host, self.server_port, loop=self.loop)
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"capabilities": self.capabilities},
            "id": 1
        }
        print(f"客户端：发送初始化请求：{request}")
        writer.write(json.dumps(request).encode())
        await writer.drain()
        response_data = await reader.read(1024)
        response = json.loads(response_data.decode())
        if "result" in response:
            negotiated_capabilities = response["result"]["capabilities"]
            print(f"客户端：协商出的能力集：{negotiated_capabilities}")
        else:
            error_message = response.get("error", {}).get("message", "未知错误")
            print(f"客户端：初始化失败，错误信息：{error_message}")
        writer.close()
        await writer.wait_closed()

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda: MCPServerProtocol(), '127.0.0.1', 8888)
    print("服务器：启动，等待客户端连接...")

    # 模拟客户端支持的能力
    client_capabilities = {
        "prompts": True,
        "resources": False,
        "tools": True,
        "logging": False,
        "experimental": True
    }
    client = MCPClient(loop, '127.0.0.1', 8888, client_capabilities)
    await client.initialize()

    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())