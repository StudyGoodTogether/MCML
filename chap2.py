# 【例2-1】
# 模拟MCP Slot结构定义与输出，展示语义角色分离机制

class Slot:
    def __init__(self, role, content, name=None):
        self.role = role        # 语义角色，如 user、system、tool 等
        self.content = content  # Slot文本内容
        self.name = name        # 可选名称标识

    def __repr__(self):
        tag = f"{self.role.upper()}" + (f" - {self.name}" if self.name else "")
        return f"[{tag}]\n{self.content}\n"

# 构建多个语义角色的Slot
slots = [
    Slot("user", "请检查以下代码是否存在性能问题：for i in range(1000000): pass", name="CodeReview"),
    Slot("system", "你是性能优化专家，请基于代码给出逐步分析建议。"),
    Slot("tool", "静态分析结果：未使用的循环体可能导致资源浪费", name="AnalyzerFeedback")
]

# 输出分段结构，模拟注入前语义对齐状态
for slot in slots:
    print(slot)



# 【例2-2】
import json

# 定义Slot结构并转换为字典形式
class Slot:
    def __init__(self, role, content, name=None):
        self.role = role
        self.content = content
        self.name = name

    def to_dict(self):
        slot = {"role": self.role, "content": self.content}
        if self.name:
            slot["name"] = self.name
        return slot

# 构造多个上下文Slot
slots = [
    Slot("user", "请将这段英文内容翻译为中文：MCP standardizes context injection."),
    Slot("system", "你是一个严谨的翻译助手，保留术语原文。", name="TranslateInstruction")
]

# 构造MCP JSON-RPC传输结构
mcp_request = {
    "jsonrpc": "2.0",
    "id": 2024,
    "method": "mcp/invoke",
    "params": {
        "slots": [s.to_dict() for s in slots],
        "options": {"max_tokens": 256}
    }
}

# 打印传输结构，模拟数据封装后发送前的状态
print(json.dumps(mcp_request, indent=2, ensure_ascii=False))



# 【例2-3】
import json

# 定义结构化Slot对象
class Slot:
    def __init__(self, role, content, options=None):
        self.role = role
        self.content = content
        self.options = options or {}

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "options": self.options
        }

# 定义生命周期属性：memory为持久化，tool结果为一次性
slots = [
    Slot("memory", "用户上次查询：AI绘画工具使用说明。", options={"persistent": True}),
    Slot("tool", "调用结果：已检索到3条绘画插件推荐。", options={"ephemeral": True}),
    Slot("user", "继续推荐更多AI图像生成方案。")
]

# 组装MCP请求结构
mcp_payload = {
    "jsonrpc": "2.0",
    "id": 888,
    "method": "mcp/invoke",
    "params": {
        "slots": [s.to_dict() for s in slots]
    }
}

# 打印封装后的消息内容
print(json.dumps(mcp_payload, indent=2, ensure_ascii=False))



# 【例2-4】
import asyncio
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("example-server")

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="example://resource",
            name="示例资源"
        )
    ]

async def main():
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main)



# 【例2-5】
import os
import json
import time
import random
import openai

# 设置OpenAI API密钥
openai.api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")

# 定义Slot类，代表MCP中的一个上下文单元
class Slot:
    def __init__(self, role, content, name=None, options=None):
        self.role = role        # 语义角色，如 "user", "system", "tool", "memory"
        self.content = content  # 上下文文本内容
        self.name = name        # 可选：标识名称
        self.options = options or {}  # 可选：其他控制属性

    def to_dict(self):
        # 将Slot转换为字典格式，符合MCP协议要求
        slot_dict = {
            "role": self.role,
            "content": self.content
        }
        if self.name:
            slot_dict["name"] = self.name
        if self.options:
            slot_dict["options"] = self.options
        return slot_dict

# 定义MCPClient类，负责构造上下文消息并调用GPT-4-Turbo API
class MCPClient:
    def __init__(self, model="gpt-4-turbo", max_tokens=512, temperature=0.7):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        # 初始化请求ID
        self.request_id = random.randint(1000, 9999)

    def build_request(self, slots, tools=None, options=None):
        """
        构造MCP协议格式请求消息
        :param slots: Slot对象列表
        :param tools: 可选，工具调用信息列表
        :param options: 可选，全局参数设置
        :return: JSON格式的请求字典
        """
        # 构造slots数组
        slots_list = [slot.to_dict() for slot in slots]
        # 构造请求消息体
        request_message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "mcp/invoke",
            "params": {
                "slots": slots_list,
                "options": options or {"max_tokens": self.max_tokens, "temperature": self.temperature}
            }
        }
        if tools:
            request_message["params"]["tools"] = tools
        return request_message

    def call_model(self, request_message):
        """
        发送请求到GPT-4-Turbo，并获取响应
        :param request_message: MCP格式请求消息
        :return: 模型返回的响应文本
        """
        # 将MCP消息中的Slot拼接成最终Prompt
        prompt = self.compose_prompt(request_message["params"]["slots"])
        # 构造OpenAI API调用参数
        messages = [
            {"role": "system", "content": "You are an AI assistant integrating MCP protocol."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            # 返回生成的文本
            return response.choices[0].message["content"]
        except Exception as e:
            return f"Error calling model: {e}"

    def compose_prompt(self, slots_list):
        """
        根据slots列表构造最终发送给模型的Prompt文本
        :param slots_list: 包含各Slot字典的列表
        :return: 拼接后的Prompt文本
        """
        prompt_parts = []
        for slot in slots_list:
            role = slot.get("role", "")
            name = slot.get("name", "")
            content = slot.get("content", "")
            # 根据角色构造提示，格式：[Role - Name]: Content
            if name:
                prompt_parts.append(f"[{role} - {name}]: {content}")
            else:
                prompt_parts.append(f"[{role}]: {content}")
        # 将各部分用换行分隔
        prompt = "\n".join(prompt_parts)
        return prompt

# 示例：构造多个Slot，整合用户输入、系统指令、工具返回值以及知识库信息
def example_usage():
    # 模拟用户输入Slot
    user_slot = Slot(role="user", content="请解释一下MCP协议如何提高大模型应用的灵活性。")
    # 模拟系统指令Slot
    system_slot = Slot(role="system", content="提供详细的技术说明，并结合实际案例。", name="Instruction")
    # 模拟工具调用返回Slot
    tool_slot = Slot(role="tool", content="已从企业知识库中检索到相关技术文档摘要。", name="KnowledgeDB")
    # 模拟额外知识库信息Slot
    memory_slot = Slot(role="memory", content="MCP协议在上下文管理和语义注入方面具有创新意义。", name="MemoryNote")

    # 将所有Slot汇总到一个列表中
    slots = [system_slot, user_slot, tool_slot, memory_slot]

    # 可选：定义工具调用信息（示例中暂不实际调用工具）
    tools = [{"name": "KnowledgeRetriever", "parameters": {"query": "MCP protocol innovation"}}]

    # 全局选项参数（例如最大Token数和温度）
    options = {"max_tokens": 512, "temperature": 0.6}

    # 初始化MCP客户端，指定使用GPT-4-Turbo模型
    mcp_client = MCPClient(model="gpt-4-turbo", max_tokens=512, temperature=0.6)

    # 构造MCP协议请求消息
    request_message = mcp_client.build_request(slots, tools, options)
    
    # 打印构造的请求消息（用于调试和验证格式）
    print("=== Constructed MCP Request Message ===")
    print(json.dumps(request_message, indent=2, ensure_ascii=False))
    print("\n")

    # 调用模型并获取响应结果
    response_text = mcp_client.call_model(request_message)
    
    # 打印模型响应结果
    print("=== Model Response ===")
    print(response_text)
    
# 主程序入口
if __name__ == "__main__":
    print("Running MCP integration example with GPT-4-Turbo...\n")
    # 为模拟网络延时添加休眠
    time.sleep(1)
    example_usage()
    print("\nIntegration example completed.")