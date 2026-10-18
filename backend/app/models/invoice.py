from sqlalchemy import String, DateTime, Numeric, Date, ForeignKey, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("company_demo.id"), nullable=False)
    beneficiary_id: Mapped[str] = mapped_column(ForeignKey("beneficiary.id"), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(asdecimal=False), nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    issue_date: Mapped[str] = mapped_column(Date, nullable=True)
    due_date: Mapped[str] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=True)
    file_hash: Mapped[str] = mapped_column(String, nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    company = relationship("CompanyDemo", back_populates="invoices")
    beneficiary = relationship("Beneficiary", back_populates="invoices")
    decisions = relationship("DecisionRecord", back_populates="invoice", cascade="all, delete-orphan")
    human_reviews = relationship("HumanReview", back_populates="invoice", cascade="all, delete-orphan")
    budget_reservations = relationship("BudgetReservation", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def last_policy_version(self) -> int | None:
        latest = max(
            self.decisions,
            key=lambda decision: (
                decision.created_at.isoformat() if decision.created_at else "",
                decision.id,
            ),
            default=None,
        )
        return latest.policy_version if latest else None
