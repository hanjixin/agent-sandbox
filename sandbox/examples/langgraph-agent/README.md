# LangGraph Agent with agent-sandbox

本项目展示如何使用 LangGraph 创建一个基于工作流的 Agent，集成 agent-sandbox 进行代码执行和文件操作。

## 功能特点

- 🔄 **工作流驱动**: 使用 LangGraph 状态机管理代理行为
- 🧠 **多步骤推理**: 支持理解、规划、执行、审查的完整推理流程
- 🐍 **Python 代码执行**: 在沙箱中安全执行 Python 代码
- 📦 **JavaScript 代码执行**: 在沙箱中安全执行 Node.js 代码
- 📁 **完整文件操作**: 读取、写入、替换、搜索、查找、列出、上传、下载
- 💻 **Shell 命令执行**: 执行任意 shell 命令
- 🌐 **浏览器自动化**: 导航、点击、输入、滚动、截图、分辨率设置
- 🔗 **URL 转 Markdown**: 将网页转换为 Markdown 格式
- 🔥 **火山云集成**: 使用 Volcengine API 提供的 DeepSeek 模型

## 前置条件

- Python 3.12+
- uv 包管理器
- 运行中的 agent-sandbox 实例 (默认: http://localhost:8080)
- 火山云 API 访问凭证

## 快速开始

### 1. 安装依赖

```bash
cd langgraph-agent
uv venv
uv pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的配置：

```env
# Volcengine API Configuration
COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key_here
COZE_INTEGRATION_MODEL_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
CODE_LLM_MODEL=deepseek-v3-2-251201

# Sandbox URL (default: http://localhost:8080)
SANDBOX_BASE_URL=http://localhost:8080
```

### 3. 运行 Agent

```bash
uv run main.py
```

## 使用示例

```
🚀 启动 LangGraph Agent...
==================================================
💡 基于工作流的智能代理
==================================================

💬 Agent 已就绪，请输入您的问题:
   (示例: 计算 1+1, 列出 /tmp 目录, 等)
   输入 'quit' 或 'exit' 退出
--------------------------------------------------

👤 您: 计算 1+1

🤖 执行中...

📍 状态更新: ['understand']

📍 状态更新: ['plan']

📍 状态更新: ['tools']

📍 状态更新: ['review']

📍 状态更新: ['plan']

✅ 最终结果:
--------------------------------------------------
2
--------------------------------------------------
```

## 工作流说明

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  1. UNDERSTAND - 理解问题                            │
│     • 分析用户意图                                   │
│     • 识别需要的信息                                 │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  2. PLAN - 规划执行步骤                              │
│     • 确定是否需要工具                               │
│     • 规划工具调用                                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  3. EXECUTE - 执行计划                               │
│     • 解析 LLM 响应                                  │
│     • 确定下一步操作                                 │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
       END             继续
        │                 │
        ▼                 ▼
┌─────────────────┐   ┌─────────────────────────────────────┐
│  5. ANSWER      │   │  4. TOOLS - 执行工具调用            │
│     返回结果    │   │     • 调用沙箱工具                  │
└─────────────────┘   │     • 收集执行结果                  │
                      └────────────────┬────────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────────┐
                      │  5. REVIEW - 审查结果               │
                      │     • 评估是否完成任务               │
                      │     • 决定是否继续                   │
                      └────────────────┬────────────────────┘
                                       │
                                       └──────────────────► 返回 PLAN
```

## 可用工具

1. **execute_python_code**: 执行 Python 代码
2. **execute_javascript_code**: 执行 JavaScript/Node.js 代码
3. **read_file**: 读取文件内容
4. **write_file**: 写入文件
5. **replace_in_file**: 替换文件中的字符串
6. **search_in_file**: 在文件中搜索正则表达式
7. **find_files**: 使用 glob 模式查找文件
8. **list_directory**: 列出目录内容
9. **upload_file**: 上传文件到沙箱
10. **download_file**: 从沙箱下载文件
11. **execute_shell_command**: 执行 shell 命令
12. **create_shell_session**: 创建 shell 会话
13. **list_shell_sessions**: 列出活跃的 shell 会话
14. **cleanup_all_sessions**: 清理所有会话
15. **get_browser_info**: 获取浏览器信息
16. **take_screenshot**: 截图
17. **browser_navigate**: 导航到 URL
18. **browser_click**: 点击元素
19. **browser_type**: 输入文本
20. **browser_scroll**: 滚动页面
21. **set_browser_resolution**: 设置浏览器分辨率
22. **convert_to_markdown**: 将 URL 转换为 Markdown

## 程序化使用

```python
from main import run_graph

result = run_graph("请计算 1+1")
print(result)
```

## 架构说明

```
┌─────────────────────────────────────────────────────┐
│              LangGraph Workflow                      │
├─────────────────────────────────────────────────────┤
│  • State: AgentState                                 │
│  • Nodes: Understand → Plan → Execute → Review       │
│  • Conditional Edges: 智能路由                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              LangChain Core                          │
├─────────────────────────────────────────────────────┤
│  • LLM: DeepSeek-V3 (Volcengine)                    │
│  • Messages: 状态消息传递                            │
│  • Tools: 沙箱工具集成                               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              agent-sandbox SDK                       │
├─────────────────────────────────────────────────────┤
│  • Code Execution (Jupyter/Node.js)                 │
│  • File Operations                                  │
│  • MCP Protocol Support                             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              Docker Sandbox (本地)                   │
└─────────────────────────────────────────────────────┘
```

## 与 LangChain Agent 的对比

| 特性 | LangChain Agent | LangGraph Agent |
|------|----------------|-----------------|
| **架构** | ReAct 单轮推理 | 工作流状态机 |
| **流程控制** | 隐式循环 | 显式状态转换 |
| **可扩展性** | 中等 | 高 |
| **复杂度** | 低 | 中等 |
| **适用场景** | 简单任务 | 复杂多步骤任务 |

## 常见问题

### Q: 如何连接到远程沙箱？
A: 修改 `SANDBOX_BASE_URL` 环境变量指向远程沙箱地址。

### Q: 支持其他模型吗？
A: 是的，修改 `CODE_LLM_MODEL` 环境变量即可使用其他模型。

### Q: 如何调试工作流？
A: 查看控制台输出，每个节点的状态都会显示。

## 许可证

MIT License
