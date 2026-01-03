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
    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox

    def on_tool_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        print(f"🔧 开始执行工具: {serialized.get('name', 'unknown')}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        print(f"✅ 工具执行完成")


@tool
def execute_python_code(code: str) -> str:
    """Execute Python code in the sandbox environment."""
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    
    result = sandbox.jupyter.execute_code(code=code)
    
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
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    
    result = sandbox.nodejs.execute_code(code=code)
    
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
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    
    result = sandbox.file.read_file(path=file_path)
    
    if hasattr(result, 'data') and result.data:
        return result.data.content
    
    return "File not found or empty"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file in the sandbox."""
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    
    result = sandbox.file.write_file(path=file_path, content=content)
    
    if hasattr(result, 'data') and result.data:
        return f"Successfully wrote to {file_path}"
    
    return "Failed to write file"


@tool
def list_files(directory: str = "/tmp") -> str:
    """List files in a directory of the sandbox."""
    sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
    sandbox = Sandbox(base_url=sandbox_url)
    
    result = sandbox.file.list_path(path=directory)
    
    if hasattr(result, 'data') and result.data:
        files = result.data.files
        if files:
            file_list = [f"{f.name} ({f.type})" for f in files]
            return "\n".join(file_list)
    
    return "Directory not found or empty"


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
    """Create a LangChain ReAct agent with sandbox tools."""
    tools = [
        execute_python_code,
        execute_javascript_code,
        read_file,
        write_file,
        list_files,
    ]
    
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
        max_iterations=10,
    )
    
    return agent_executor


async def run_agent_query(query: str):
    """Run a query through the LangChain agent."""
    agent = create_langchain_agent()
    
    result = await agent.ainvoke({"input": query})
    
    return result


def main():
    """Main entry point for the LangChain agent."""
    print("🚀 启动 LangChain Agent...")
    print("=" * 50)
    
    agent = create_langchain_agent()
    
    print("\n💬 Agent 已就绪，请输入您的问题:")
    print("   (示例: 计算 1+1, 列出 /tmp 目录的文件, 等)")
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
            
            print("\n🤖 思考中...")
            result = agent.invoke({"input": user_input})
            
            print("\n✅ 结果:")
            print("-" * 50)
            print(result.get("output", "No output"))
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("请重试...")


if __name__ == "__main__":
    main()
