"""
LangChain Agent with complete agent-sandbox integration.

This agent uses LangChain's ReAct pattern and integrates all sandbox tools
including file operations, code execution, shell commands, and browser automation.
"""

import os
import json
from typing import List, Dict, Any, Union
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.agents import AgentStep
from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain.callbacks.base import BaseCallbackHandler
from agent_sandbox import Sandbox

load_dotenv()


class SandboxCallbackHandler(BaseCallbackHandler):
    """Callback handler for sandbox operations."""
    
    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox

    def on_tool_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        print(f"🔧 开始执行工具: {serialized.get('name', 'unknown')}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        print(f"✅ 工具执行完成")


# Import all tools from our comprehensive tools module
import sys
sys.path.insert(0, os.path.dirname(__file__))
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


def create_llm():
    """Create LLM instance using Volcengine API."""
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")
    model = os.getenv("CODE_LLM_MODEL", "deepseek-v3-2-251201")
    
    if not api_key or not base_url:
        raise ValueError("Missing required environment variables: COZE_WORKLOAD_IDENTITY_API_KEY or COZE_INTEGRATION_MODEL_BASE_URL")
    
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
    )


def create_langchain_agent():
    """Create a LangChain ReAct agent with all sandbox tools."""
    tools = all_tools
    
    llm = create_llm()
    
    prompt = hub.pull("hwchase17/react")
    
    agent = create_react_agent(llm, tools, prompt)
    
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    callback_handler = SandboxCallbackHandler(sandbox)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        callbacks=[callback_handler],
        handle_parsing_errors=True,
        max_iterations=20,
    )
    
    return agent_executor


async def run_agent_query(query: str):
    """Run a query through the LangChain agent."""
    agent = create_langchain_agent()
    
    result = await agent.ainvoke({"input": query})
    
    return result


def main():
    """Main entry point for the LangChain agent."""
    print("🚀 启动 LangChain Agent (完整工具集成版)...")
    print("=" * 60)
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
    
    agent = create_langchain_agent()
    
    print("\n💬 Agent 已就绪，请输入您的问题:")
    print("   (示例: 计算 1+1, 列出 /tmp 目录的文件, 执行 shell 命令, 等)")
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
            
            print("\n🤖 思考中...")
            result = agent.invoke({"input": user_input})
            
            print("\n✅ 结果:")
            print("-" * 60)
            print(result.get("output", "No output"))
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            print("请重试...")


if __name__ == "__main__":
    main()
