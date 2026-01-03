import os
import json
from typing import List, Dict, Any, TypedDict, Annotated, Union, Optional
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from agent_sandbox import Sandbox

load_dotenv()


class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_step: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_answer: str
    iterations: int


class AgentStep(Enum):
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    ANSWER = "answer"


class SandboxClient:
    def __init__(self):
        self.sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
        self._sandbox = None
    
    @property
    def sandbox(self) -> Sandbox:
        if self._sandbox is None:
            self._sandbox = Sandbox(base_url=self.sandbox_url)
        return self._sandbox


sandbox_client = SandboxClient()


@tool
def execute_python_code(code: str) -> str:
    """Execute Python code in the sandbox environment."""
    result = sandbox_client.sandbox.jupyter.execute_code(code=code)
    
    if hasattr(result, 'data') and result.data:
        outputs = result.data.outputs
        if outputs:
            output_texts = []
            for output in outputs:
                if hasattr(output, 'text') and output.text:
                    output_texts.append(output.text)
                elif hasattr(output, 'error') and output.error:
                    output_texts.append(f"Error: {output.error}")
            return "\n".join(output_texts) if output_texts else "Code executed successfully (no output)"
    
    return "Code executed successfully"


@tool
def execute_javascript_code(code: str) -> str:
    """Execute JavaScript/Node.js code in the sandbox environment."""
    result = sandbox_client.sandbox.nodejs.execute_code(code=code)
    
    if hasattr(result, 'data') and result.data:
        outputs = result.data.outputs
        if outputs:
            output_texts = []
            for output in outputs:
                if hasattr(output, 'text') and output.text:
                    output_texts.append(output.text)
                elif hasattr(output, 'error') and output.error:
                    output_texts.append(f"Error: {output.error}")
            return "\n".join(output_texts) if output_texts else "Code executed successfully (no output)"
    
    return "Code executed successfully"


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file from the sandbox."""
    result = sandbox_client.sandbox.file.read_file(path=file_path)
    
    if hasattr(result, 'data') and result.data:
        return result.data.content
    
    return "File not found or empty"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file in the sandbox."""
    result = sandbox_client.sandbox.file.write_file(path=file_path, content=content)
    
    if hasattr(result, 'data') and result.data:
        return f"Successfully wrote to {file_path}"
    
    return "Failed to write file"


@tool
def list_files(directory: str = "/tmp") -> str:
    """List files in a directory of the sandbox."""
    result = sandbox_client.sandbox.file.list_path(path=directory)
    
    if hasattr(result, 'data') and result.data:
        files = result.data.files
        if files:
            file_list = [f"{f.name} ({f.type})" for f in files]
            return "\n".join(file_list)
    
    return "Directory not found or empty"


@tool
def search_files(pattern: str, path: str = "/tmp") -> str:
    """Search for files matching a pattern in the sandbox."""
    result = sandbox_client.sandbox.file.find_files(path=path, pattern=pattern)
    
    if hasattr(result, 'data') and result.data:
        files = result.data.files
        if files:
            file_list = [f"{f.name} ({f.type})" for f in files]
            return "\n".join(file_list)
    
    return "No files found matching the pattern"


tools = [
    execute_python_code,
    execute_javascript_code,
    read_file,
    write_file,
    list_files,
    search_files,
]

tool_node = ToolNode(tools)


def create_llm():
    """Create LLM instance using Volcengine API."""
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")
    model = os.getenv("CODE_LLM_MODEL", "deepseek-v3-2-251201")
    
    if not api_key or not base_url:
        raise ValueError("Missing required environment variables: COZE_WORKLOAD_IDENTITY_API_KEY or COZE_INTEGRATION_MODEL_BASE_URL")
    
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
    )


def should_continue(state: AgentState) -> str:
    """判断是否继续执行或结束"""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    
    if last_message and isinstance(last_message, AIMessage):
        if last_message.content.strip().endswith("FINAL_ANSWER:"):
            return "end"
        elif any(isinstance(msg, ToolMessage) for msg in messages):
            return "continue"
    
    return "continue"


def understand_node(state: AgentState) -> AgentState:
    """理解用户输入的节点"""
    llm = create_llm()
    messages = state["messages"]
    
    system_prompt = """你是一个智能助手。你需要理解用户的问题，并决定是否需要使用工具。

请分析用户的问题：
1. 问题是什么？
2. 需要执行什么操作？
3. 需要使用哪些工具？

请用简洁的语言回答。"""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages
    ])
    
    return {
        "messages": state["messages"] + [response],
        "current_step": AgentStep.PLAN.value,
        "tool_calls": state.get("tool_calls", []),
        "tool_results": state.get("tool_results", []),
        "final_answer": "",
        "iterations": state.get("iterations", 0) + 1
    }


def plan_node(state: AgentState) -> AgentState:
    """规划执行步骤的节点"""
    llm = create_llm()
    messages = state["messages"]
    
    system_prompt = """你是一个智能助手。基于当前的问题和已有的信息，规划下一步需要做什么。

请按照以下格式回答：
PLANNED_ACTION: <下一步应该做什么>
USE_TOOL: <是否需要使用工具 (yes/no)>
TOOL_NAME: <如果需要使用工具，工具名称>
TOOL_ARGS: <工具参数，JSON格式>

如果问题已经解决，请回答：
FINAL_ANSWER: <最终答案>"""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages
    ])
    
    return {
        "messages": state["messages"] + [response],
        "current_step": AgentStep.EXECUTE.value,
        "tool_calls": state.get("tool_calls", []),
        "tool_results": state.get("tool_results", []),
        "final_answer": "",
        "iterations": state.get("iterations", 0)
    }


def execute_node(state: AgentState) -> AgentState:
    """执行工具调用的节点"""
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    
    if last_message and isinstance(last_message, AIMessage):
        if "FINAL_ANSWER:" in last_message.content:
            answer = last_message.content.replace("FINAL_ANSWER:", "").strip()
            return {
                "messages": state["messages"],
                "current_step": AgentStep.ANSWER.value,
                "tool_calls": state.get("tool_calls", []),
                "tool_results": state.get("tool_results", []),
                "final_answer": answer,
                "iterations": state.get("iterations", 0)
            }
    
    return state


def review_node(state: AgentState) -> AgentState:
    """审查结果的节点"""
    llm = create_llm()
    messages = state["messages"]
    tool_results = state.get("tool_results", [])
    
    system_prompt = """你是一个智能助手。请审查工具执行的结果，判断是否完成了任务。

如果任务完成，请回答：
FINAL_ANSWER: <最终答案>

如果任务未完成，请继续规划下一步操作。"""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages,
        SystemMessage(content=f"\n工具执行结果: {tool_results}")
    ])
    
    return {
        "messages": state["messages"] + [response],
        "current_step": AgentStep.PLAN.value,
        "tool_calls": state.get("tool_calls", []),
        "tool_results": state.get("tool_results", []),
        "final_answer": "",
        "iterations": state.get("iterations", 0)
    }


def create_agent_graph() -> StateGraph:
    """创建 LangGraph 状态图"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("understand", understand_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("review", review_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("understand")
    
    workflow.add_edge("understand", "plan")
    workflow.add_edge("plan", "execute")
    
    workflow.add_conditional_edges(
        "execute",
        lambda state: should_continue(state),
        {
            "continue": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "review")
    workflow.add_edge("review", "plan")
    
    return workflow


def run_graph(query: str) -> Dict[str, Any]:
    """运行图推理"""
    app = create_agent_graph().compile()
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "current_step": AgentStep.UNDERSTAND.value,
        "tool_calls": [],
        "tool_results": [],
        "final_answer": "",
        "iterations": 0
    }
    
    config = {"configurable": {"thread_id": "1"}}
    
    final_state = None
    for state in app.stream(initial_state, config=config):
        final_state = state
        print(f"\n📍 状态更新: {list(state.keys())}")
    
    return final_state


def main():
    """主入口"""
    print("🚀 启动 LangGraph Agent...")
    print("=" * 50)
    print("💡 基于工作流的智能代理")
    print("=" * 50)
    
    print("\n💬 Agent 已就绪，请输入您的问题:")
    print("   (示例: 计算 1+1, 列出 /tmp 目录, 等)")
    print("   输入 'quit' 或 'exit' 退出")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 执行中...")
            result = run_graph(user_input)
            
            print("\n✅ 最终结果:")
            print("-" * 50)
            if result and "final_answer" in result:
                print(result["final_answer"])
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
