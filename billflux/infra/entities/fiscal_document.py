"""Module for model FiscalDocument (notas fiscais emitidas pelo PDV)"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Field


class FiscalDocument(SQLModel, table=True):
    """Uma NFC-e por venda do PDV (modelo 65)."""

    __tablename__ = "fiscal_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(
        foreign_key="orders.id", nullable=False, unique=True, index=True
    )
    provider: str = Field(default="brasilnfe", nullable=False, max_length=40)
    model: int = Field(default=65, nullable=False)
    environment: str = Field(default="homologacao", nullable=False, max_length=20)
    status: str = Field(default="pendente", nullable=False, max_length=30, index=True)
    series: Optional[int] = Field(default=None, nullable=True)
    number: Optional[int] = Field(default=None, nullable=True)
    access_key: Optional[str] = Field(
        default=None, nullable=True, max_length=44, index=True
    )
    protocol: Optional[str] = Field(default=None, nullable=True, max_length=60)
    xml: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    danfe: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    qr_code_url: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    error_code: Optional[str] = Field(default=None, nullable=True, max_length=20)
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    retry_count: int = Field(default=0, nullable=False)
    next_retry_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    authorized_at: Optional[datetime] = Field(default=None, nullable=True)
    cancelled_at: Optional[datetime] = Field(default=None, nullable=True)
    cancel_reason: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
