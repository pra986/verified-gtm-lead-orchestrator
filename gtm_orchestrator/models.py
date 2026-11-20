from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ICPProfile(BaseModel):
    """Ideal Customer Profile criteria for GTM lead qualification."""

    industry: str
    min_employees: int = 10
    max_employees: int = 5000
    target_regions: List[str] = Field(default_factory=lambda: ["US", "EU", "UK", "IN"])
    excluded_domains: List[str] = Field(default_factory=list)


class ScrapedLeadEvidence(BaseModel):
    """Untrusted lead evidence ingested from Firecrawl / web scraping."""

    source_url: str
    company_name: str
    raw_text: str
    sanitized_text: str = ""
    canonical_domain: str = ""
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    employee_count: Optional[int] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    injection_detected: bool = False
    neutralized_patterns: List[str] = Field(default_factory=list)


class CRMUpsertReceipt(BaseModel):
    """Idempotent Pipedrive CRM upsert receipt keyed by canonical root domain."""

    record_id: str
    canonical_domain: str
    company_name: str
    action: str  # "CREATED" or "UPDATED"
    contact_email: Optional[str] = None
    sanitized_summary: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutreachApprovalItem(BaseModel):
    """Human-in-the-loop approval gate item for outreach and calendar booking."""

    item_id: str
    record_id: str
    canonical_domain: str
    contact_email: Optional[str] = None
    subject: str
    body: str
    proposed_slot: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING_APPROVAL
    reason: Optional[str] = None
    calendar_booked: bool = False
    outreach_sent: bool = False
