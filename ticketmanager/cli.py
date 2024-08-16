import typer
from rich.table import Table
from rich.console import Console
from typing import Optional, List
from ticketmanager.infra.repository.tickets_repository import (
    add_ticket_to_database,
    get_tickets_from_database,
)
from ticketmanager.infra.entities.models import Ticket

main = typer.Typer(help="Ticket Manager Aplication")
console = Console()


@main.command("add")
def add(bar_code: int, suplyer: str, type: str = typer.Option(...)):
    """Add a new ticket to database."""
    if add_ticket_to_database(bar_code, suplyer, type):
        print("New ticket add on database!")
    else:
        print("Failed! :()")


@main.command("list")
def list_tickets(type: Optional[str] = None) -> List[Ticket]:
    """Lists tickets in database."""
    tickets = get_tickets_from_database()
    table = Table(title="Tickets")
    headers = ["bar_code", "suplyer", "type", "due_date", "payday", "is_paid_out"]
    for header in headers:
        table.add_column(header, style="magenta")
    for ticket in tickets:
        values = [str(getattr(ticket, header)) for header in headers]
        table.add_row(*values)
    console.print(table)
