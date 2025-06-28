# nl2sql_project/cli.py
import requests
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

# --- 配置 ---
MCP_SERVER_URL = "http://localhost:8080"
PAGE_SIZE = 10

# --- 初始化 ---
console = Console()

def query_mcp_server(prompt, offset=0):
    """向 MCP 服务器发送查询请求"""
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/query",
            json={"prompt": prompt, "page_size": PAGE_SIZE, "offset": offset},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"连接 MCP 服务器失败: {e}"}

def display_results(result):
    """以表格形式美观地展示查询结果"""
    if not result or not result.get("data"):
        console.print("[yellow]查询成功，但没有返回任何数据。[/yellow]")
        return

    data = result["data"]
    table = Table(title="查询结果", show_header=True, header_style="bold magenta")
    
    # 添加列
    headers = data[0].keys()
    for header in headers:
        table.add_column(header, style="dim")

    # 添加行
    for row in data:
        table.add_row(*[str(item) for item in row.values()])
        
    console.print(table)
    console.print(f"[green]成功返回 {len(data)} 条记录。[/green]")

def main():
    """CLI 主循环"""
    console.print("[bold cyan]欢迎使用自然语言数据库查询 CLI[/bold cyan]")
    console.print(f"后端服务器: [link={MCP_SERVER_URL}]{MCP_SERVER_URL}[/link]")
    
    last_prompt = ""
    current_offset = 0

    while True:
        if not last_prompt:
            prompt = console.input("[bold]请输入你的问题 (输入 'exit' 退出): [/bold]")
        else:
            prompt = console.input(f"[bold]输入 'next' 获取下一页, 'exit' 退出, 或输入新问题: [/bold]")

        if prompt.lower() == 'exit':
            break
            
        if prompt.lower() == 'next':
            if not last_prompt:
                console.print("[yellow]没有可用于翻页的查询，请输入一个新问题。[/yellow]")
                continue
            prompt_to_send = last_prompt
        else:
            # 是一个新问题，重置状态
            current_offset = 0
            last_prompt = prompt
            prompt_to_send = prompt

        with console.status("[bold green]正在查询...[/bold green]"):
            result = query_mcp_server(prompt_to_send, current_offset)

        if "error" in result:
            console.print(f"[bold red]错误: {result['error']}[/bold red]")
            if result.get("generated_sql"):
                console.print("生成的 (错误的) SQL:")
                syntax = Syntax(result["generated_sql"], "sql", theme="default", line_numbers=True)
                console.print(syntax)
            last_prompt = "" # 出错了，重置
            continue

        console.print("\n[bold blue]LLM 生成的 SQL:[/bold blue]")
        sql_syntax = Syntax(result.get('generated_sql', ''), "sql", theme="default", line_numbers=True)
        console.print(sql_syntax)
        
        display_results(result)

        if result.get("next_offset"):
            current_offset = result["next_offset"]
            console.print("[cyan]提示: 查询结果有多页，输入 'next' 查看下一页。[/cyan]\n")
        else:
            console.print("[cyan]已是最后一页。[/cyan]\n")
            last_prompt = "" # 最后一页，重置
            current_offset = 0


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]用户中断，程序退出。[/bold yellow]")
        sys.exit(0)