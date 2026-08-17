from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from billflux.domain.models.bills import Bill
from billflux.infra.config.database import create_db
from billflux.infra.repository.bill_repository import BillRepository

main = typer.Typer(help="BillFlux - Gerenciador de Contas a Pagar")
console = Console()


@main.callback()
def init_database():
    """Garante que as tabelas existam no banco de dados."""
    create_db()


@main.command("add")
def add(bar_code: int, suplyer: str, bill_type: str = typer.Option(...)):
    """Add a new bill to database."""
    repository = BillRepository()
    if repository.insert_bill(bar_code=bar_code, suplyer=suplyer, bill_type=bill_type):
        print("New bill added to database!")
    else:
        print("Failed!")


@main.command("list")
def list_bills(bill_type: Optional[str] = None) -> List[Bill]:
    """Lists bills in database."""
    repository = BillRepository()
    bills = repository.get_bills()
    table = Table(title="Bills")
    headers = [
        "bar_code",
        "suplyer",
        "bill_type",
        "due_date",
        "value",
        "payday",
        "status",
    ]
    for header in headers:
        table.add_column(header, style="magenta")
    for bill in bills:
        values = [str(getattr(bill, header)) for header in headers]
        table.add_row(*values)
    console.print(table)
