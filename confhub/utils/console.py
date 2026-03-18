"""ConfHub CLI - rich 출력 헬퍼 모듈"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def print_success(message: str):
    """성공 메시지 출력"""
    console.print(f"✅ {message}", style="green")


def print_error(message: str):
    """에러 메시지 출력 (stderr)"""
    error_console.print(f"❌ {message}", style="red")


def print_warning(message: str):
    """경고 메시지 출력"""
    console.print(f"⚠️  {message}", style="yellow")


def print_info(message: str):
    """정보 메시지 출력"""
    console.print(f"ℹ️  {message}", style="blue")


def print_panel(title: str, content: str, style: str = "blue"):
    """패널 형태로 메시지 출력"""
    console.print(Panel(content, title=title, style=style))


def make_table(title: str, columns: list[str]) -> Table:
    """헤더가 있는 rich Table 생성"""
    table = Table(title=title, show_header=True, header_style="bold blue")
    for col in columns:
        table.add_column(col)
    return table
