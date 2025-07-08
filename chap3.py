# 【例3-1】
from mcp.server import Server
from mcp.server.stdio import stdio_server

# 创建MCP服务器实例
app = Server("example-server")

# 定义资源列表的处理函数
@app.list_resources()
async def list_resources():
    return [
        {"uri": "example://resource", "name": "示例资源"}
    ]

# 启动服务器
async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



# 【例3-2】
# MCP风格的错误结构（模拟）
class MCPError(Exception):
    def __init__(self, code, message):
        self.code = code  # 类似MCP标准定义，如 -32602 为参数错误
        self.message = message

def mcp_server_handle(request: dict):
    # 模拟服务端检查请求
    if "method" not in request:
        raise MCPError(code=-32600, message="Invalid Request: missing method")
    if request["method"] not in ["ping", "status"]:
        raise MCPError(code=-32601, message="Method not found")
    return {"result": f"Executed {request['method']} successfully"}



# 【例3-3】
class DataVersion:
    def __init__(self):
        self.version = 0
        self.data = {}

    def update_data(self, key, value):
        self.version += 1
        self.data[key] = (value, self.version)

    def get_data(self, key):
        return self.data.get(key, (None, 0))



# 【例3-4】
prompt_template = {
    "name": "analyze_code",
    "description": "Analyze code for potential improvements",
    "arguments": [
        {
            "name": "language",
            "description": "Programming language",
            "required": True
        },
        {
            "name": "code_snippet",
            "description": "Code snippet to analyze",
            "required": True
        }
    ]
}



# 【例3-5】
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp import types

# 创建 MCP 服务器实例
mcp = FastMCP("DynamicResourceServer")

# 动态资源字典，模拟资源的动态更新
dynamic_resources = {
    "resource1": "初始内容"
}

# 定义动态资源获取函数
@mcp.resource("dynamic://{resource_id}")
async def get_dynamic_resource(resource_id: str) -> str:
    """根据资源 ID 返回对应的内容"""
    return dynamic_resources.get(resource_id, "资源未找到")

# 定义更新资源的工具函数
@mcp.tool()
async def update_resource(resource_id: str, new_content: str) -> str:
    """更新指定资源的内容"""
    if resource_id in dynamic_resources:
        dynamic_resources[resource_id] = new_content
        # 通知客户端资源列表已更改
        await mcp.notify(types.ListResourcesChangedNotification())
        return f"资源 {resource_id} 已更新。"
    else:
        return f"资源 {resource_id} 不存在。"

# 运行服务器
if __name__ == "__main__":
    mcp.run()
