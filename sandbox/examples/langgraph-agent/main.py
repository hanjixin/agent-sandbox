"""
LangGraph Agent with complete agent-sandbox integration.

This agent uses LangGraph's workflow-based architecture and integrates all sandbox tools
including file operations, code execution, shell commands, and browser automation.
"""

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
    """State for the LangGraph agent."""
    messages: List[BaseMessage]
    current_step: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_answer: str
    iterations: int


class AgentStep(Enum):
    """Steps in the agent workflow."""
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    ANSWER = "answer"


# Import all tools from our comprehensive tools module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import (
    execute_python_code,
    execute_javascript_code,
    read_file,
    write_file,
    replace_in_file,
    search_in_file,
    find_files,
    list_directory,
    upload_file,
    download_file,
    execute_shell_command,
    create_shell_session,
    list_shell_sessions,
    cleanup_all_sessions,
    get_browser_info,
    take_screenshot,
    browser_navigate,
    browser_click,
    browser_type,
    browser_scroll,
    set_browser_resolution,
    convert_to_markdown,
)


# Define all available tools for the agent
all_tools = [
    # Code Execution
    execute_python_code,
    execute_javascript_code,
    
    # File Operations
    read_file,
    write_file,
    replace_in_file,
    search_in_file,
    find_files,
    list_directory,
    upload_file,
    download_file,
    
    # Shell Operations
    execute_shell_command,
    create_shell_session,
    list_shell_sessions,
    cleanup_all_sessions,
    
    # Browser Operations
    get_browser_info,
    take_screenshot,
    browser_navigate,
    browser_click,
    browser_type,
    browser_scroll,
    set_browser_resolution,
    
    # Utility
    convert_to_markdown,
]


tool_node = ToolNode(all_tools)


class SandboxClient:
    """Sandbox client wrapper."""
    
    def __init__(self):
        self.sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
        self._sandbox = None
    
    @property
    def sandbox(self) -> Sandbox:
        if self._sandbox is None:
            self._sandbox = Sandbox(base_url=self.sandbox_url)
        return self._sandbox


sandbox_client = SandboxClient()


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


def print_tools_info():
    """Print all available tools."""
    print("📦 可用工具列表:")
    print("-" * 60)
    
    tool_categories = {
        "🐍 代码执行": ["execute_python_code", "execute_javascript_code"],
        "📁 文件操作": ["read_file", "write_file", "replace_in_file", "search_in_file", "find_files", "list_directory", "upload_file", "download_file"],
        "💻 Shell命令": ["execute_shell_command", "create_shell_session", "list_shell_sessions", "cleanup_all_sessions"],
        "🌐 浏览器": ["get_browser_info", "take_screenshot", "browser_navigate", "browser_click", "browser_type", "browser_scroll", "set_browser_resolution"],
        "🔧 工具": ["convert_to_markdown"],
    }
    
    for category, tool_names in tool_categories.items():
        print(f"\n{category}:")
        for tool_name in tool_names:
            print(f"  • {tool_name}")
    
    print("\n" + "=" * 60)


def main():
    """主入口"""
    print("🚀 启动 LangGraph Agent (完整工具集成版)...")
    print("=" * 60)
    
    print_tools_info()
    
    print("\n💬 Agent 已就绪，请输入您的问题:")
    print("   (示例: 计算 1+1, 列出 /tmp 目录, 执行 shell 命令, 等)")
    print("   输入 'quit' 或 'exit' 退出")
    print("-" * 60)
    
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
            print("-" * 60)
            if result and "final_answer" in result:
                print(result["final_answer"])
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
