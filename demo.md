以下是基于MCP协议与大模型集成实战的模块化代码示例，涵盖核心功能与常见应用场景。代码以Python为主，结合MCP官方文档的典型实现方式（注：实际代码需根据具体MCP库版本调整）。
---
### **模块一：MCP协议基础（Server与Client设置）**
#### 1.1 MCP Server基础代码（模拟天气查询工具）
```python
from fastapi import FastAPI
from pydantic import BaseModel
import json
app = FastAPI()
# 模拟天气查询工具
class WeatherTool:
    def get_weather(self, city: str):
        # 模拟API调用
        return {"city": city, "temperature": "25°C", "condition": "Sunny"}
# MCP Server实现
class MCP_Server:
    def __init__(self):
        self.tools = {"weather": WeatherTool()}
    
    async def handle_request(self, request_data):
        """处理MCP Client的JSON请求"""
        tool_name = request_data["tool"]
        params = request_data["params"]
        tool = self.tools.get(tool_name)
        
        if tool_name == "weather":
            result = tool.get_weather(params["city"])
        else:
            result = {"error": "Tool not found"}
        
        return {"result": result}
# 启动Server（需配合FastAPI/MCP库）
server = MCP_Server()
```
#### 1.2 MCP Client基础代码（发送查询请求）
```python
import requests
class MCP_Client:
    def __init__(self, server_url):
        self.server_url = server_url
    
    def query_tool(self, tool_name, params):
        """向Server发送请求并获取响应"""
        payload = {
            "tool": tool_name,
            "params": params
        }
        response = requests.post(f"{self.server_url}/mcp", json=payload)
        return response.json()
# 使用示例
client = MCP_Client("http://localhost:8000")
result = client.query_tool("weather", {"city": "Beijing"})
print(result)  # 输出: {"result": {"city": "Beijing", "temperature": "25°C"}}
```
---
### **模块二：实战集成（大模型+MCP）**
#### 2.1 大模型调用MCP工具的流程（伪代码）
```python
from transformers import pipeline
# 初始化大模型
model = pipeline("text-generation")
def model_with_mcp(user_input):
    # 1. 模型分析输入是否需要工具
    if "weather" in user_input:
        # 2. 通过MCP Client查询天气
        weather_data = client.query_tool("weather", {"city": "Beijing"})
        # 3. 将结果融入模型回复
        response = f"当前天气：{weather_data['result']['temperature']}"
    else:
        response = model(user_input)[0]["generated_text"]
    return response
# 示例
print(model_with_mcp("今天北京的天气怎么样？"))
```
#### 2.2 JSON请求/响应格式示例
```json
// Client发送的请求
{
  "tool": "weather",
  "params": {"city": "Beijing"},
  "context": {"session_id": "123"}
}
// Server返回的响应
{
  "result": {
    "city": "Beijing",
    "temperature": "25°C",
    "condition": "Sunny"
  },
  "status": "success"
}
```
---
### **模块三：常见应用场景代码**
#### 3.1 数据库查询集成（SQLite示例）
```python
import sqlite3
class DatabaseTool:
    def query(self, sql):
        conn = sqlite3.connect("example.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result
# 在MCP Server中注册
server.tools["database"] = DatabaseTool()
# Client调用示例
client.query_tool("database", {"sql": "SELECT * FROM users LIMIT 1"})
```
#### 3.2 文件读写集成
```python
class FileTool:
    def read_file(self, file_path):
        with open(file_path, "r") as f:
            return f.read()
    def write_file(self, file_path, content):
        with open(file_path, "w") as f:
            f.write(content)
# 在MCP Server中注册
server.tools["file"] = FileTool()
# Client调用示例
client.query_tool("file", {"action": "read", "path": "/data/report.txt"})
```
---
### **模块四：MCP发现机制（自动注册）**
```python
# Server端注册工具描述（用于Client发现）
TOOLS_DESC = {
    "weather": {
        "description": "查询城市天气",
        "params": {"city": "str"}
    },
    "database": {
        "description": "执行SQL查询",
        "params": {"sql": "str"}
    }
}
# Client发现可用工具
def discover_tools(server_url):
    response = requests.get(f"{server_url}/mcp/tools")
    return response.json()
print(discover_tools("http://localhost:8000"))
# 输出: {"weather": {...}, "database": {...}}
```
---
### **教学提示**
1. **环境准备**：需安装`fastapi`, `requests`等库，并运行FastAPI服务。
2. **扩展性**：实际项目中可结合`mcp-python`库（如`pip install mcp`）简化开发。
3. **安全性**：生产环境需添加认证（如API密钥）和输入验证。
  通过以上代码示例，学生可以直观理解MCP协议的核心交互流程，并快速上手实战集成。建议结合实际部署（如Docker容器化Server）进行教学演示。