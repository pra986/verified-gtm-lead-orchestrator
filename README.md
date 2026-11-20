# Verified GTM Lead Orchestrator

**Project 11 (B3: AI Builder - Go-to-Market Agent System)**

A production-hardened Go-To-Market (GTM) lead research and Pipedrive CRM orchestration agent featuring untrusted Firecrawl scraped-text prompt-injection sanitization, canonical root-domain CRM deduplication, missing-contact manual review routing, and human-in-the-loop approval gates before external outreach or calendar booking.

---

## Architecture Overview

```
ICPProfile
   |
   v
[1. Discovery & Firecrawl Scrape] ---> Untrusted Web Text
   |
   v
[2. Prompt-Injection Sanitizer]   ---> Strips adversarial directives & hidden instructions
   |
   v
[3. Canonical Domain Normalizer]  ---> Extracts root domain (e.g. app.acme.io -> acme.io)
   |
   v
[4. Pipedrive CRM Upsert Gate]    ---> Deduplicates by root domain; updates existing or creates new
   |
   +--> (Missing contact email) --> Manual Review Queue
   |
   v
[5. Outreach & Calendar Staging]  ---> Generates OutreachApprovalItem (pending human approval)
   |
   v
[6. Human Approval Gate]          ---> Approved -> Dispatch / Book | Rejected -> Preserve CRM state
```

## 6-Stage Workflow

1. **ICP Targeting (`ICPProfile`)**: Validates target industry, company size, geography, and disqualifiers.
2. **Evidence Collection (`ScrapedLeadEvidence`)**: Ingests scraped company pages and contact signals from Firecrawl / n8n webhooks.
3. **Prompt-Injection Sanitization**: Neutralizes untrusted web payloads (e.g., `ignore previous instructions`, `system:`, tool-call spoofing, base64/HTML comment directives) before any downstream reasoning or CRM write.
4. **Canonical Root-Domain Deduplication (`CRMUpsertReceipt`)**: Normalizes URLs/subdomains to canonical root domains so repeated runs upsert existing Pipedrive organization/deal records instead of creating duplicates.
5. **Missing-Contact Routing**: Leads lacking a verified contact email are automatically routed to `manual_review_queue` rather than entering automated outreach.
6. **Human Approval Gate (`OutreachApprovalItem`)**: External emails and calendar slot bookings remain gated in `PENDING_APPROVAL`. Rejected calendar slots or outreach items preserve the underlying CRM lead state without side effects.

## Data Contract

- `ICPProfile`: Ideal Customer Profile criteria (industry, min/max employees, regions, excluded domains).
- `ScrapedLeadEvidence`: Raw scraped text, source URL, extracted domain, optional contact email, and sanitization metadata.
- `CRMUpsertReceipt`: Canonical root domain, Pipedrive record ID, action (`CREATED` | `UPDATED`), and timestamp.
- `OutreachApprovalItem`: Proposed subject, body, calendar slot, approval status (`PENDING_APPROVAL` | `APPROVED` | `REJECTED` | `MANUAL_REVIEW`), and audit trail.

## Production Controls

- **Untrusted Input Isolation**: All Firecrawl markdown/text is sanitized and flagged (`injection_detected`, `neutralized_patterns`) prior to CRM or outreach staging.
- **Idempotent CRM Writes**: Canonical root-domain keying prevents duplicate Pipedrive records across retries and multi-URL scrapes.
- **Fail-Safe Contact Validation**: Missing or invalid contact emails never trigger outbound messaging.
- **Zero Unapproved Side Effects**: No email or calendar invite is dispatched without explicit human approval; rejections leave lead state intact.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run CLI demo
python -m gtm_orchestrator.cli

# Run test suite
pytest -v
```

## Attribution

Built as **Project 11 (B3)** inspired by **Ed Donner's AI Builder** course, extending the n8n + Firecrawl + Pipedrive GTM agent pattern with deterministic verification, prompt-injection neutralization, and approval gates.

## License

MIT
