"""Complete tool integration for agent-sandbox.

This module provides all available sandbox tools as LangChain tools.
"""

import os
import base64
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain_core.tools import tool
from agent_sandbox import Sandbox

load_dotenv()


class SandboxTools:
    """All sandbox tools wrapper class."""
    
    def __init__(self):
        self.sandbox_url = os.getenv("SANDBOX_BASE_URL", "http://localhost:8080")
        self._sandbox = None
    
    @property
    def sandbox(self) -> Sandbox:
        if self._sandbox is None:
            self._sandbox = Sandbox(base_url=self.sandbox_url)
        return self._sandbox


sandbox_tools = SandboxTools()


def format_output(outputs: List[Any]) -> str:
    """Format code execution outputs."""
    if not outputs:
        return "Code executed successfully (no output)"
    
    output_texts = []
    for output in outputs:
        if hasattr(output, 'text') and output.text:
            output_texts.append(output.text)
        elif hasattr(output, 'error') and output.error:
            output_texts.append(f"Error: {output.error}")
        elif hasattr(output, 'result') and output.result:
            output_texts.append(str(output.result))
    
    return "\n".join(output_texts) if output_texts else "Code executed successfully"


@tool
def execute_python_code(code: str) -> str:
    """Execute Python code in the sandbox environment.
    
    Args:
        code: Python code to execute
    
    Returns:
        Execution output or error message
    """
    result = sandbox_tools.sandbox.jupyter.execute_code(code=code)
    return format_output(result.data.outputs if result.data else [])


@tool
def execute_javascript_code(code: str) -> str:
    """Execute JavaScript/Node.js code in the sandbox environment.
    
    Args:
        code: JavaScript code to execute
    
    Returns:
        Execution output or error message
    """
    result = sandbox_tools.sandbox.nodejs.execute_code(code=code)
    return format_output(result.data.outputs if result.data else [])


@tool
def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read the contents of a file from the sandbox.
    
    Args:
        file_path: Absolute file path to read
        start_line: Optional start line (0-based)
        end_line: Optional end line (not inclusive)
    
    Returns:
        File contents or error message
    """
    result = sandbox_tools.sandbox.file.read_file(
        file=file_path,
        start_line=start_line,
        end_line=end_line
    )
    
    if hasattr(result, 'data') and result.data:
        return result.data.content
    
    return "File not found or empty"


@tool
def write_file(file_path: str, content: str, append: bool = False) -> str:
    """Write content to a file in the sandbox.
    
    Args:
        file_path: Absolute file path to write
        content: Content to write
        append: Whether to append to existing file
    
    Returns:
        Success or error message
    """
    result = sandbox_tools.sandbox.file.write_file(
        file=file_path,
        content=content,
        append=append
    )
    
    return f"Successfully wrote to {file_path}"


@tool
def replace_in_file(file_path: str, old_str: str, new_str: str) -> str:
    """Replace a string in a file.
    
    Args:
        file_path: Absolute file path
        old_str: String to replace
        new_str: Replacement string
    
    Returns:
        Success or error message
    """
    result = sandbox_tools.sandbox.file.replace_in_file(
        file=file_path,
        old_str=old_str,
        new_str=new_str
    )
    
    return f"Successfully replaced text in {file_path}"


@tool
def search_in_file(file_path: str, regex: str) -> str:
    """Search for a pattern in file content using regular expressions.
    
    Args:
        file_path: Absolute file path
        regex: Regular expression pattern
    
    Returns:
        Search results or "Pattern not found"
    """
    result = sandbox_tools.sandbox.file.search_in_file(
        file=file_path,
        regex=regex
    )
    
    if hasattr(result, 'data') and result.data:
        matches = result.data.content
        if matches:
            return matches
    
    return "Pattern not found"


@tool
def find_files(path: str = "/tmp", pattern: str = "*") -> str:
    """Find files by name pattern in a directory.
    
    Args:
        path: Directory path to search
        pattern: Glob pattern (e.g., "*.py", "**/*.txt")
    
    Returns:
        List of matching files or "No files found"
    """
    result = sandbox_tools.sandbox.file.find_files(
        path=path,
        glob=pattern
    )
    
    if hasattr(result, 'data') and result.data:
        files = result.data.files
        if files:
            file_list = [f"{f.name} ({f.type})" for f in files]
            return "\n".join(file_list)
    
    return "No files found matching the pattern"


@tool
def list_directory(
    path: str = "/tmp",
    recursive: bool = False,
    show_hidden: bool = False,
    file_types: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    include_size: bool = False
) -> str:
    """List directory contents with various options.
    
    Args:
        path: Directory path to list
        recursive: Whether to list recursively
        show_hidden: Whether to show hidden files
        file_types: Filter by file extensions (e.g., ['.py', '.txt'])
        max_depth: Maximum depth for recursive listing
        include_size: Whether to include file size
    
    Returns:
        Directory listing or "Directory not found"
    """
    result = sandbox_tools.sandbox.file.list_path(
        path=path,
        recursive=recursive,
        show_hidden=show_hidden,
        file_types=file_types,
        max_depth=max_depth,
        include_size=include_size
    )
    
    if hasattr(result, 'data') and result.data:
        files = result.data.files
        if files:
            file_list = []
            for f in files:
                size_info = f" ({f.size} bytes)" if f.size else ""
                file_list.append(f"{f.name}{size_info}")
            return "\n".join(file_list)
    
    return "Directory not found or empty"


@tool
def upload_file(file_path: str, local_file_path: str) -> str:
    """Upload a file to the sandbox.
    
    Args:
        file_path: Target path in sandbox
        local_file_path: Path to local file to upload
    
    Returns:
        Success or error message
    """
    with open(local_file_path, 'rb') as f:
        file_content = f.read()
    
    encoded_content = base64.b64encode(file_content).decode('utf-8')
    
    result = sandbox_tools.sandbox.file.upload_file(
        file=(local_file_path.split('/')[-1], encoded_content),
        path=file_path
    )
    
    return f"Successfully uploaded {local_file_path} to {file_path}"


@tool
def download_file(file_path: str, local_path: str) -> str:
    """Download a file from the sandbox.
    
    Args:
        file_path: Path in sandbox to download
        local_path: Local path to save
    
    Returns:
        Success or error message
    """
    chunks = []
    for chunk in sandbox_tools.sandbox.file.download_file(path=file_path):
        chunks.append(chunk)
    
    if chunks:
        with open(local_path, 'wb') as f:
            for chunk in chunks:
                f.write(chunk)
        return f"Successfully downloaded {file_path} to {local_path}"
    
    return "File not found or download failed"


@tool
def execute_shell_command(
    command: str,
    timeout: Optional[float] = 30.0,
    exec_dir: Optional[str] = None
) -> str:
    """Execute a shell command in the sandbox.
    
    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds
        exec_dir: Working directory
    
    Returns:
        Command output (stdout/stderr)
    """
    result = sandbox_tools.sandbox.shell.exec_command(
        command=command,
        timeout=timeout,
        exec_dir=exec_dir
    )
    
    if hasattr(result, 'data') and result.data:
        outputs = []
        if result.data.stdout:
            outputs.append(result.data.stdout)
        if result.data.stderr:
            outputs.append(f"STDERR: {result.data.stderr}")
        return "\n".join(outputs) if outputs else "Command executed (no output)"
    
    return "Command failed or timed out"


@tool
def create_shell_session(exec_dir: Optional[str] = None) -> str:
    """Create a new shell session.
    
    Args:
        exec_dir: Working directory for the session
    
    Returns:
        Session ID or error message
    """
    result = sandbox_tools.sandbox.shell.create_session(exec_dir=exec_dir)
    
    if hasattr(result, 'data') and result.data:
        return f"Session created: {result.data.id}"
    
    return "Failed to create session"


@tool
def list_shell_sessions() -> str:
    """List all active shell sessions.
    
    Returns:
        List of active sessions or "No active sessions"
    """
    result = sandbox_tools.sandbox.shell.list_sessions()
    
    if hasattr(result, 'data') and result.data:
        sessions = result.data.sessions
        if sessions:
            session_list = []
            for s in sessions:
                session_list.append(f"ID: {s.id}, State: {s.state}")
            return "\n".join(session_list)
    
    return "No active sessions"


@tool
def cleanup_all_sessions() -> str:
    """Clean up all active shell sessions.
    
    Returns:
        Success message
    """
    sandbox_tools.sandbox.shell.cleanup_all_sessions()
    return "All sessions cleaned up"


@tool
def get_browser_info() -> str:
    """Get information about the browser environment.
    
    Returns:
        Browser information or error message
    """
    result = sandbox_tools.sandbox.browser.get_info()
    
    if hasattr(result, 'data') and result.data:
        info = []
        info.append(f"CDP URL: {result.data.cdp_url}")
        info.append(f"Viewport: {result.data.viewport.width}x{result.data.viewport.height}")
        return "\n".join(info)
    
    return "Browser not available"


@tool
def take_screenshot() -> str:
    """Take a screenshot of the current browser display.
    
    Returns:
        Screenshot taken message
    """
    chunks = []
    for chunk in sandbox_tools.sandbox.browser.screenshot():
        chunks.append(chunk)
    
    if chunks:
        return f"Screenshot captured: {len(chunks)} bytes"
    return "Screenshot failed"


@tool
def browser_navigate(url: str) -> str:
    """Navigate browser to a URL.
    
    Args:
        url: URL to navigate to
    
    Returns:
        Success or error message
    """
    from agent_sandbox.browser import Action_Navigate
    result = sandbox_tools.sandbox.browser.execute_action(
        request=Action_Navigate(url=url)
    )
    
    return f"Navigated to {url}"


@tool
def browser_click(selector: str) -> str:
    """Click on an element by selector.
    
    Args:
        selector: CSS selector of element
    
    Returns:
        Success or error message
    """
    from agent_sandbox.browser import Action_Click, Selector
    
    result = sandbox_tools.sandbox.browser.execute_action(
        request=Action_Click(selector=Selector(css_selector=selector))
    )
    
    return f"Clicked on {selector}"


@tool
def browser_type(selector: str, text: str) -> str:
    """Type text into an element.
    
    Args:
        selector: CSS selector of element
        text: Text to type
    
    Returns:
        Success or error message
    """
    from agent_sandbox.browser import Action_Type, Selector
    
    result = sandbox_tools.sandbox.browser.execute_action(
        request=Action_Type(
            text=text,
            selector=Selector(css_selector=selector)
        )
    )
    
    return f"Typed text into {selector}"


@tool
def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """Scroll the browser page.
    
    Args:
        direction: Scroll direction (up/down)
        amount: Scroll amount in pixels
    
    Returns:
        Success or error message
    """
    from agent_sandbox.browser import Action_Scroll
    
    x, y = 0, amount if direction == "down" else -amount
    
    result = sandbox_tools.sandbox.browser.execute_action(
        request=Action_Scroll(x=x, y=y)
    )
    
    return f"Scrolled {direction}"


@tool
def set_browser_resolution(width: int = 1920, height: int = 1080) -> str:
    """Set browser resolution.
    
    Args:
        width: Screen width
        height: Screen height
    
    Returns:
        Success or error message
    """
    from agent_sandbox.browser import Resolution
    
    result = sandbox_tools.sandbox.browser.set_config(
        resolution=Resolution(width=width, height=height)
    )
    
    return f"Browser resolution set to {width}x{height}"


@tool
def convert_to_markdown(url: str) -> str:
    """Convert a webpage URL to markdown.
    
    Args:
        url: URL to convert
    
    Returns:
        Markdown content or error message
    """
    result = sandbox_tools.sandbox.util.convert_to_markdown(url=url)
    
    if hasattr(result, 'data') and result.data:
        return result.data.content
    
    return "Failed to convert URL to markdown"


def get_all_tools():
    """Return all available tools as a list."""
    return [
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
    ]
