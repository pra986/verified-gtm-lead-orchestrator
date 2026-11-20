from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .models import (
    ApprovalStatus,
    CRMUpsertReceipt,
    ICPProfile,
    OutreachApprovalItem,
    ScrapedLeadEvidence,
)

INJECTION_PATTERNS: List[Tuple[str, str]] = [
    ("ignore_instructions", r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    ("system_prompt", r"(?i)(reveal|dump|print|show)\s+(the\s+)?system\s+prompt"),
    ("override_directive", r"(?i)(system\s+override|developer\s+mode|jailbreak)"),
    ("exfiltrate_secrets", r"(?i)(exfiltrate|leak|send)\s+(api\s+keys?|secrets?|tokens?)"),
    ("script_tag", r"(?is)<script.*?>.*?</script>"),
    ("tool_injection", r"(?i)(execute|call)\s+tool\s+without\s+approval"),
]


class VerifiedGTMOrchestrator:
    """GTM lead orchestrator with prompt-injection sanitization, domain deduplication, and approval gates."""

    def __init__(self, icp: Optional[ICPProfile] = None) -> None:
        self.icp = icp or ICPProfile(industry="FinTech", target_regions=["US", "EU", "IN"])
        self.crm_records: Dict[str, CRMUpsertReceipt] = {}
        self.approval_queue: Dict[str, OutreachApprovalItem] = {}
        self.manual_review_queue: List[OutreachApprovalItem] = []

    @staticmethod
    def canonicalize_domain(url_or_domain: str) -> str:
        raw = (url_or_domain or "").strip().lower()
        if not raw:
            return ""
        candidate = raw if "://" in raw else f"https://{raw}"
        parsed = urlparse(candidate)
        host = (parsed.netloc or parsed.path).split(":")[0].strip(".")
        if host.startswith("www."):
            host = host[4:]
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    @staticmethod
    def sanitize_scraped_text(raw_text: str) -> Tuple[str, bool, List[str]]:
        sanitized = raw_text or ""
        matched: List[str] = []
        for label, pattern in INJECTION_PATTERNS:
            if re.search(pattern, sanitized):
                matched.append(label)
                sanitized = re.sub(pattern, "[REDACTED_UNTRUSTED_DIRECTIVE]", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized, bool(matched), matched

    def process_lead(
        self,
        evidence: ScrapedLeadEvidence,
        proposed_slot: str = "2026-11-24T15:00:00Z",
    ) -> Tuple[CRMUpsertReceipt, OutreachApprovalItem]:
        sanitized, detected, patterns = self.sanitize_scraped_text(evidence.raw_text)
        evidence.sanitized_text = sanitized
        evidence.injection_detected = detected
        evidence.neutralized_patterns = patterns

        canonical = self.canonicalize_domain(evidence.canonical_domain or evidence.source_url)
        evidence.canonical_domain = canonical

        now_iso = datetime.now(timezone.utc).isoformat()
        existing = self.crm_records.get(canonical)
        if existing:
            receipt = CRMUpsertReceipt(
                record_id=existing.record_id,
                canonical_domain=canonical,
                company_name=evidence.company_name,
                action="updated",
                contact_email=evidence.contact_email or existing.contact_email,
                sanitized_summary=sanitized[:240],
                updated_at=now_iso,
            )
        else:
            receipt = CRMUpsertReceipt(
                record_id=f"crm_{uuid.uuid4().hex[:8]}",
                canonical_domain=canonical,
                company_name=evidence.company_name,
                action="created",
                contact_email=evidence.contact_email,
                sanitized_summary=sanitized[:240],
                updated_at=now_iso,
            )
        self.crm_records[canonical] = receipt

        item_id = f"apr_{uuid.uuid4().hex[:8]}"
        has_valid_email = bool(evidence.contact_email and "@" in evidence.contact_email)
        if not has_valid_email:
            approval_item = OutreachApprovalItem(
                item_id=item_id,
                record_id=receipt.record_id,
                canonical_domain=canonical,
                contact_email=None,
                subject=f"Manual review required for {evidence.company_name}",
                body="Missing contact email; automated outreach and calendar booking blocked.",
                proposed_slot=proposed_slot,
                status=ApprovalStatus.MANUAL_REVIEW,
                reason="Missing contact email; routed to manual review queue.",
                calendar_booked=False,
                outreach_sent=False,
            )
            self.manual_review_queue.append(approval_item)
        else:
            approval_item = OutreachApprovalItem(
                item_id=item_id,
                record_id=receipt.record_id,
                canonical_domain=canonical,
                contact_email=evidence.contact_email,
                subject=f"Intro: {evidence.company_name} x GTM Automation",
                body=f"Hi {evidence.contact_name or 'there'}, noted {evidence.company_name}: {sanitized[:120]}",
                proposed_slot=proposed_slot,
                status=ApprovalStatus.PENDING_APPROVAL,
                reason="Awaiting human approval before external outreach or calendar booking.",
                calendar_booked=False,
                outreach_sent=False,
            )
        self.approval_queue[item_id] = approval_item
        return receipt, approval_item

    def approve_item(self, item_id: str) -> OutreachApprovalItem:
        item = self.approval_queue[item_id]
        if item.status == ApprovalStatus.MANUAL_REVIEW or not item.contact_email:
            raise ValueError("Cannot approve item in MANUAL_REVIEW without contact email.")
        item.status = ApprovalStatus.APPROVED
        item.calendar_booked = True
        item.outreach_sent = True
        item.reason = "Approved by human reviewer."
        return item

    def reject_item(self, item_id: str, reason: str = "Calendar slot rejected") -> OutreachApprovalItem:
        item = self.approval_queue[item_id]
        item.status = ApprovalStatus.REJECTED
        item.calendar_booked = False
        item.outreach_sent = False
        item.reason = reason
        return item
