# 【例9-1】
import os
import time
import json
import asyncio
from typing import List, Dict, Any

import numpy as np
import faiss
import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

############################
# Mock: Embedding function
############################
def mock_text_to_vector(text: str, dim: int = 64) -> np.ndarray:
    """
    模拟文本到向量的转换, 仅用随机数表示,
    真实场景可调用Sentence-BERT或OpenAI等Embedding模型
    """
    rng = np.random.RandomState(abs(hash(text)) % (10**6))
    return rng.rand(dim).astype('float32')

############################
# Construct FAISS index offline
############################
TEXT_DB = [
    "Quantum physics deals with subatomic particles",
    "Machine learning relies on data-driven approaches",
    "Neural networks are biologically inspired computing systems",
    "Climate change impacts global temperature and weather patterns",
    "FAISS is a popular library for vector similarity search",
    "Milvus supports large scale vector data management in a distributed environment",
    "RAG is retrieval augmented generation to combine external knowledge with LLMs",
    "MCP provides a standardized context protocol for LLM-based solutions"
]

EMB_DIM = 64
# build vectors
VECTORS = []
for doc in TEXT_DB:
    vec = mock_text_to_vector(doc, EMB_DIM)
    VECTORS.append(vec)

VECTORS = np.vstack(VECTORS)
faiss_index = faiss.IndexFlatL2(EMB_DIM)
faiss_index.add(VECTORS)

ID_TO_TEXT = {i: TEXT_DB[i] for i in range(len(TEXT_DB))}

############################
# MCP server definition
############################
app = FastMCP("faiss-vector-search")

@app.tool()
def tool_vector_search(query_text: str, top_k: int = 3) -> Dict[str, Any]:
    """
    MCP工具函数: 将query_text转为embedding,
    在FAISS索引中检索最相近top_k条记录并返回

    Args:
        query_text: 用户查询文本
        top_k: 返回前k条检索结果

    Returns:
        {
          "query_embedding": ...,
          "hits": [
            {"doc_id": int, "score": float, "text": str}, ...
          ]
        }
    """
    # convert query to vector
    query_vec = mock_text_to_vector(query_text, EMB_DIM).reshape(1, -1)
    # search
    distances, indices = faiss_index.search(query_vec, top_k)
    hits = []
    for i in range(top_k):
        idx = indices[0][i]
        dist = distances[0][i]
        if idx < 0:
            continue
        hits.append({
            "doc_id": int(idx),
            "score": float(dist),
            "text": ID_TO_TEXT[int(idx)]
        })
    return {
        "query_embedding": "omitted_for_demo",  # 不实际显示向量
        "hits": hits
    }

@app.tool()
def tool_list_db_content() -> Dict[str, Any]:
    """
    查看TEXT_DB中所有文本内容, 仅作演示用
    """
    return {"db_size": len(TEXT_DB), "docs": TEXT_DB}

############################
# Server & Client
############################
async def run_server():
    print("=== MCP服务器(faiss-vector-search) 启动... ===")
    app.run(transport="stdio")

async def run_client():
    print("=== 客户端等待5秒后启动... ===")
    await asyncio.sleep(5)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath(__file__)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[Client] 初始化完成, 开始向量检索演示")
            await session.initialize()

            # Step1: 查看DB内容
            list_res = await session.call_tool("tool_list_db_content", {})
            print("[Client] 查看DB内容:", list_res)

            # Step2: 向量检索查询1
            query1 = "machine intelligence approach"
            search_res1 = await session.call_tool("tool_vector_search", {
                "query_text": query1,
                "top_k": 3
            })
            print("[Client] 向量检索结果1:", search_res1)

            # Step3: 向量检索查询2
            query2 = "global warming and environment"
            search_res2 = await session.call_tool("tool_vector_search", {
                "query_text": query2,
                "top_k": 4
            })
            print("[Client] 向量检索结果2:", search_res2)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例9-2】
import os
import time
import random
import json
import asyncio
from typing import List, Dict, Any

import mcp
from mcp.server import FastMCP
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

##############################
# Mock: Industry knowledge database
##############################
DOCS = [
    "Industry 4.0 emphasizes automation and data exchange in manufacturing technologies",
    "Cloud computing enables scalable resources over the internet for dynamic workloads",
    "An intelligent system can leverage big data for predictive maintenance in factories",
    "Natural language processing helps machines understand human text or speech inputs",
    "Regulatory compliance in pharmaceutical sector requires strict documentation",
    "MCP provides a standard protocol for model-based context communication",
    "Data privacy is a major concern when collecting user analytics data"
]

##############################
# Mock: Generate vector for doc
##############################
def mock_vector_for_doc(doc: str, dim: int = 32) -> List[float]:
    """
    仅做随机数生成, 不与之前示例重复
    """
    seed = abs(hash(doc)) % (10**6)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]

def mock_vector_for_query(query: str, dim: int = 32) -> List[float]:
    """
    同理, 用于生成查询向量
    """
    seed = abs(hash(query)) % (10**6)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]

##############################
# Mock: Simple vector DB
##############################
VEC_DIM = 32
class SimpleVectorDB:
    def __init__(self):
        self.index = []  # list of (doc_id, vector)
        self.doc_map = {} # doc_id -> text

    def build_index(self, docs: List[str]):
        for i, d in enumerate(docs):
            vec = mock_vector_for_doc(d, VEC_DIM)
            self.index.append((i, vec))
            self.doc_map[i] = d

    def search(self, query_vec: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        # 计算欧氏距离, 只做演示
        result = []
        for doc_id, vec in self.index:
            dist = sum((q - v)**2 for q,v in zip(query_vec, vec))**0.5
            result.append({"doc_id": doc_id, "dist": dist})
        # 排序取top_k
        result.sort(key=lambda x: x["dist"])
        return result[:top_k]

    def get_doc_text(self, doc_id: int) -> str:
        return self.doc_map[doc_id]

# 建立全局vector db
VEC_DB = SimpleVectorDB()
VEC_DB.build_index(DOCS)

##############################
# Mock: LLM for final generation
##############################
def mock_model_infer(context_docs: List[str], user_query: str) -> str:
    """
    模拟调用语言模型, 将片段拼接后给出简短回答.
    不做实际NLP, 仅演示流程
    """
    # 只展示doc列表
    doc_titles = ", ".join([c[:25] for c in context_docs])
    return f"Answer for '{user_query}', based on docs: {doc_titles}..."

##############################
# MCP server definition
##############################
app = FastMCP("rag-demo-server")

@app.tool()
def tool_search_vector(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    RAG阶段1: vector search
    """
    qv = mock_vector_for_query(query, VEC_DIM)
    hits = VEC_DB.search(qv, top_k)
    # fetch text
    results = []
    for h in hits:
        doc_text = VEC_DB.get_doc_text(h["doc_id"])
        results.append({"doc_id": h["doc_id"], "distance": h["dist"], "text": doc_text})
    return {"hits": results}

@app.tool()
def tool_select_snippets(hits: List[Dict[str, Any]], limit_tokens: int = 50) -> Dict[str, Any]:
    """
    RAG阶段2: snippet selection
    limit_tokens: 模拟基于长度限制进行片段截断
    """
    # 简单策略: 按distance从小到大, 取前n篇
    # doc的最长长度限制limit_tokens, 仅为演示
    chosen = []
    used = 0
    for h in hits:
        txt = h["text"]
        # mock text length
        length = len(txt.split())
        if used + length <= limit_tokens:
            chosen.append(txt)
            used += length
        else:
            break
    return {"selected_snippets": chosen, "used_tokens": used}

@app.tool()
def tool_generate_answer(user_query: str, context_snippets: List[str]) -> Dict[str, Any]:
    """
    RAG阶段3: LLM answer generation
    """
    # mock a final answer
    final_answer = mock_model_infer(context_snippets, user_query)
    return {"answer": final_answer}

##############################
# demonstration: server & client
##############################
async def run_server():
    print("=== MCP服务器(rag-demo-server) 启动... ===")
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
            print("[Client] RAG chain: 检索→选择→生成")
            await session.initialize()

            # 1. 用户查询
            user_query = "explain big data use in predictive maintenance"

            # 2. 向量检索
            search_res = await session.call_tool("tool_search_vector", {
                "query": user_query,
                "top_k": 5
            })
            print("[Client] 向量检索结果:", search_res)

            # 3. 片段筛选
            hits = search_res.get("hits", [])
            select_res = await session.call_tool("tool_select_snippets", {
                "hits": hits,
                "limit_tokens": 30
            })
            print("[Client] 片段筛选结果:", select_res)

            # 4. 最终生成回答
            sel_snips = select_res.get("selected_snippets", [])
            gen_res = await session.call_tool("tool_generate_answer", {
                "user_query": user_query,
                "context_snippets": sel_snips
            })
            print("[Client] 最终回答:", gen_res)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例9-3】
import os
import time
import json
import random
import asyncio
from typing import Dict, Any, List

import mcp
from mcp.server import FastMCP
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters

#####################
# Mock data & vector
#####################
DOCS_DB = [
    "Cloud computing uses virtualized resources for dynamic scaling",
    "A knowledge base can contain structured or unstructured data",
    "MCP standardizes context passing between model and external tools",
    "Vector search helps find semantically similar documents in large corpora",
    "RAG stands for retrieval-augmented generation in language modeling",
    "Slot mechanism in MCP organizes context in a structured manner",
    "Distributed training improves model performance with parallel computation"
]

def mock_text_to_vector(txt: str, dim: int = 16) -> List[float]:
    seed = abs(hash(txt)) % (10**6)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]

def mock_model_infer(context: List[str], query: str) -> str:
    """
    模拟生成, 把context信息拼合并返回简单回答
    """
    preview_context = [c[:25] for c in context]
    return f"[MockAnswer] Query='{query}' with context={preview_context}"

#####################
# Simple vector DB
#####################
class SimpleVectorDB:
    def __init__(self):
        self.index = []
        self.docs = {}

    def build_index(self):
        for i, doc in enumerate(DOCS_DB):
            vec = mock_text_to_vector(doc)
            self.index.append((i, vec))
            self.docs[i] = doc

    def search(self, query_vec: List[float], top_k: int) -> List[Dict[str, Any]]:
        results = []
        for idx, vec in self.index:
            dist = sum((q - v)**2 for q,v in zip(query_vec, vec))**0.5
            results.append({"idx": idx, "dist": dist})
        results.sort(key=lambda x: x["dist"])
        return results[:top_k]

    def get_doc(self, idx: int) -> str:
        return self.docs[idx]

VDB = SimpleVectorDB()
VDB.build_index()

#####################
# Global slot store
#####################
# retrieval_slot: store search result list
# selected_snippets_slot: store selected text
# We store them in a dictionary keyed by session_id or user_id for demonstration
RAG_SLOT_STORE: Dict[str, Dict[str, Any]] = {}

def init_user_slot_store(user_id: str):
    if user_id not in RAG_SLOT_STORE:
        RAG_SLOT_STORE[user_id] = {
            "retrieval_slot": [],
            "selected_snippets_slot": []
        }

#####################
# MCP server
#####################
app = FastMCP("rag-slot-demo")

@app.tool()
def tool_vector_search(user_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    执行向量检索, 将结果写入user的retrieval_slot
    """
    init_user_slot_store(user_id)
    qv = mock_text_to_vector(query)
    hits = VDB.search(qv, top_k)
    results = []
    for h in hits:
        doc_text = VDB.get_doc(h["idx"])
        results.append({"doc_text": doc_text, "dist": h["dist"]})
    RAG_SLOT_STORE[user_id]["retrieval_slot"] = results
    return {"message": "retrieval done", "retrieved_count": len(results), "hits": results}

@app.tool()
def tool_select_snippets(user_id: str, limit_len: int = 50) -> Dict[str, Any]:
    """
    从retrieval_slot中选出若干片段, 并写入selected_snippets_slot
    limit_len模拟针对上下文长度限制做片段裁剪
    """
    if user_id not in RAG_SLOT_STORE:
        return {"error": "no retrieval_slot found"}
    ret = RAG_SLOT_STORE[user_id]["retrieval_slot"]
    chosen = []
    used = 0
    for r in ret:
        text = r["doc_text"]
        token_count = len(text.split())
        if used + token_count <= limit_len:
            chosen.append(text)
            used += token_count
        else:
            break
    RAG_SLOT_STORE[user_id]["selected_snippets_slot"] = chosen
    return {"chosen_count": len(chosen), "chosen_texts": chosen}

@app.tool()
def tool_generate_answer(user_id: str, query: str) -> Dict[str, Any]:
    """
    根据selected_snippets_slot生成回答
    """
    if user_id not in RAG_SLOT_STORE:
        return {"error": "no selected_snippets_slot found"}
    context_snips = RAG_SLOT_STORE[user_id]["selected_snippets_slot"]
    if not context_snips:
        return {"error": "no context selected"}
    answer = mock_model_infer(context_snips, query)
    return {"final_answer": answer}

@app.tool()
def tool_show_slots(user_id: str) -> Dict[str, Any]:
    """
    查看当前user_id对应的RAG slot内容
    """
    if user_id not in RAG_SLOT_STORE:
        return {"error": "no slot store for given user"}
    return RAG_SLOT_STORE[user_id]

#####################
# demonstration
#####################
async def run_server():
    print("=== RAG上下文Slot演示服务器启动... ===")
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
            print("[Client] RAG slot demonstration starts")
            await session.initialize()

            user_id = "user_abc"
            # 1. 向量检索
            query_text = "transformer approach in data usage"
            res1 = await session.call_tool("tool_vector_search", {
                "user_id": user_id,
                "query": query_text,
                "top_k": 5
            })
            print("[Client] 向量检索结果:", res1)

            # 2. 选择片段, limit_len=20做裁剪
            res2 = await session.call_tool("tool_select_snippets", {
                "user_id": user_id,
                "limit_len": 20
            })
            print("[Client] 片段选择:", res2)

            # 3. 生成回答
            res3 = await session.call_tool("tool_generate_answer", {
                "user_id": user_id,
                "query": query_text
            })
            print("[Client] 最终回答:", res3)

            # 4. 查看slot详情
            slot_view = await session.call_tool("tool_show_slots", {"user_id": user_id})
            print("[Client] slot内容:", slot_view)

async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())



# 【例9-4】
import os
import time
import random
import json
import asyncio
from typing import Dict, Any, List

import mcp
from mcp.server import FastMCP
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters

DOC_DB = [
    "Document A: Cloud computing resources can be scaled up or down automatically.",
    "Document B: Large Language Models often require specialized GPU clusters for training.",
    "Document C: RAG combines vector search with generative capabilities, enabling knowledge infusion.",
    "Document D: MCP provides a unified context protocol for various AI tools and services.",
    "Document E: Data ingestion pipelines frequently rely on Kafka or RabbitMQ for streaming."
]

################ Mock embedding function ################
def mock_embed(text: str, dim: int = 16) -> List[float]:
    seed = abs(hash(text)) % (10**6)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]

def mock_model_infer(prompt_context: List[str], query: str) -> str:
    """
    将prompt_context与query简单拼合, 返回伪回答
    """
    joined_context = "\n".join(prompt_context)
    return f"Query: {query}\nContext:\n{joined_context}\n[MockAnswer] Summarized."

################ Simple vector DB with doc_id and rank ################
class MiniVectorDB:
    def __init__(self):
        self.index = []
        self.map_id = {}

    def build(self, docs: List[str]):
        for i, d in enumerate(docs):
            emb = mock_embed(d)
            self.index.append((i, emb, d))
            self.map_id[i] = d

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        qv = mock_embed(query)
        results = []
        for (did, emb, text) in self.index:
            dist = sum((e1 - e2)**2 for e1, e2 in zip(emb, qv))**0.5
            results.append({"doc_id": did, "distance": dist, "text": text})
        results.sort(key=lambda x: x["distance"])
        top_hits = results[:top_k]
        # 生成段落rank信息
        final = []
        for rank, hit in enumerate(top_hits):
            final.append({
                "doc_id": hit["doc_id"],
                "rank": rank+1,
                "score": round(hit["distance"], 4),
                "text": hit["text"]
            })
        return final

VDB = MiniVectorDB()
VDB.build(DOC_DB)

# 全局slot store, keyed by user_id
SLOT_STORE: Dict[str, Dict[str, Any]] = {}

def ensure_slot_store(user_id: str):
    if user_id not in SLOT_STORE:
        SLOT_STORE[user_id] = {
            "structured_retrieval_slot": None,
            "final_inject_slot": None
        }

app = FastMCP("structured-rag-demo")

@app.tool()
def tool_search_docs(user_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Step1: 搜索多个片段, 记录doc_id, rank, score, text等结构信息, 并暂存在structured_retrieval_slot
    """
    ensure_slot_store(user_id)
    hits = VDB.search(query, top_k)
    # hits: list of {doc_id, rank, score, text}
    SLOT_STORE[user_id]["structured_retrieval_slot"] = hits
    return {"status": "ok", "hits": hits}

@app.tool()
def tool_structure_snippets(user_id: str, token_limit: int = 40) -> Dict[str, Any]:
    """
    Step2: 将structured_retrieval_slot中各snippet组织为可注入Prompt的列表,
    并根据token限制裁剪或合并
    """
    if user_id not in SLOT_STORE:
        return {"error": "user not found"}
    if not SLOT_STORE[user_id]["structured_retrieval_slot"]:
        return {"error": "no retrieval data found"}
    hits = SLOT_STORE[user_id]["structured_retrieval_slot"]
    chosen_snips = []
    used = 0
    for h in hits:
        txt = h["text"]
        tokens = len(txt.split())
        if used + tokens <= token_limit:
            chosen_snips.append(f"Rank{h['rank']} Score{h['score']}: {txt}")
            used += tokens
        else:
            break
    # 记录到 final_inject_slot
    SLOT_STORE[user_id]["final_inject_slot"] = chosen_snips
    return {"status": "ok", "snippets_count": len(chosen_snips), "chosen_snippets": chosen_snips}

@app.tool()
def tool_generate_final_answer(user_id: str, query: str) -> Dict[str, Any]:
    """
    Step3: 用final_inject_slot做Prompt上下文, 调用mock_model_infer
    """
    if user_id not in SLOT_STORE:
        return {"error": "user not found"}
    context_data = SLOT_STORE[user_id]["final_inject_slot"]
    if not context_data:
        return {"error": "no snippet to inject"}
    final_answer = mock_model_infer(context_data, query)
    return {"final_answer": final_answer}

@app.tool()
def tool_show_slot(user_id: str) -> Dict[str, Any]:
    """
    查看Slot内容
    """
    if user_id not in SLOT_STORE:
        return {"error": "user slot not found"}
    return SLOT_STORE[user_id]

################# server & client demo #################
async def run_server():
    print("=== MCP服务器(structured-rag-demo) 启动... ===")
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
            print("[Client] Multi-segment RAG injection demonstration")
            await session.initialize()

            user_id = "user_999"
            query_text = "how does rag integrate knowledge with models"

            # Step1: 检索
            res1 = await session.call_tool("tool_search_docs", {
                "user_id": user_id,
                "query": query_text,
                "top_k": 4
            })
            print("[Client] step1 search result:", res1)

            # Step2: 结构化snippet, token_limit=30模拟裁剪
            res2 = await session.call_tool("tool_structure_snippets", {
                "user_id": user_id,
                "token_limit": 30
            })
            print("[Client] step2 structure snippet:", res2)

            # Step3: 生成回答
            res3 = await session.call_tool("tool_generate_final_answer", {
                "user_id": user_id,
                "query": query_text
            })
            print("[Client] step3 final answer:", res3)

            # 查看Slot
            slot_info = await session.call_tool("tool_show_slot", {"user_id": user_id})
            print("[Client] slot info:", slot_info)


async def main():
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(run_client())
    await asyncio.gather(server_task, client_task)

if __name__ == "__main__":
    asyncio.run(main())