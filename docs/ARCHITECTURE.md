# Verified GTM Lead Orchestrator Architecture

## Overview
`verified-gtm-lead-orchestrator` is a deterministic, security-hardened Go-To-Market (GTM) lead ingestion, CRM deduplication, and human-in-the-loop outreach orchestration pipeline.

## Pipeline Stages

1. **ICP Definition & Filtering (`ICPProfile`)**
   - Validates incoming lead evidence against target industry, employee headcount bounds (`min_employees` to `max_employees`), target regions, and `excluded_domains`.

2. **Untrusted Scraped-Text Sanitization**
   - Treats all scraped web copy (`raw_text`) as untrusted input.
   - Detects and neutralizes prompt-injection payloads (e.g., `ignore previous instructions`, `system prompt`, `tool call`, `<script>`, `jailbreak`, override directives) before any downstream summarization or drafting.
   - Records `injection_detected` and `neutralized_patterns` on `ScrapedLeadEvidence`.

3. **Canonical Root-Domain Normalization & CRM Upsert**
   - Extracts and normalizes `canonical_domain` from `source_url` or domain fields (stripping protocol, `www.`, subdomains/paths, and lowercasing).
   - Performs idempotent Pipedrive CRM upsert keyed on `canonical_domain` so repeated scrapes of the same organization update the existing `CRMUpsertReceipt` (`action="updated"`) instead of creating duplicate records.

4. **Missing-Contact Routing (`MANUAL_REVIEW`)**
   - If `contact_email` is missing or invalid, the orchestrator routes the lead to `ApprovalStatus.MANUAL_REVIEW` rather than attempting automated outreach or calendar booking.

5. **Human Approval Gating (`PENDING_APPROVAL` -> `APPROVED` / `REJECTED`)**
   - Valid leads with verified contact details enter `ApprovalStatus.PENDING_APPROVAL` as an `OutreachApprovalItem`.
   - External email outreach (`outreach_sent`) and calendar slot booking (`calendar_booked`) are strictly blocked until explicit human approval is recorded.
   - If a proposed calendar slot or outreach item is rejected (`ApprovalStatus.REJECTED`), `calendar_booked` and `outreach_sent` remain `False` and the lead state is preserved.

## Data Contracts (`gtm_orchestrator/models.py`)
- `ApprovalStatus`: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `MANUAL_REVIEW`
- `ICPProfile`: Target ICP constraints and domain exclusions
- `ScrapedLeadEvidence`: Raw and sanitized lead evidence with injection telemetry
- `CRMUpsertReceipt`: Idempotent CRM write receipt keyed by `canonical_domain`
- `OutreachApprovalItem`: Gated outreach draft and proposed calendar slot
