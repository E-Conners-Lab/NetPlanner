# Security Policy

NetPlanner is built to a strict secure-by-default standard (authentication,
ownership scoping, CSRF, rate limiting, prompt-injection boundaries, and a
hardened CI gate). We take security reports seriously and appreciate
responsible disclosure.

## Supported versions

NetPlanner is pre-1.0 and ships from `main`. Security fixes land on `main`;
there is no separate LTS branch yet.

| Version | Supported |
|---------|-----------|
| `main`  | ✅        |
| older tags | ❌ (upgrade to `main`) |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through GitHub's **"Report a vulnerability"** button under the
repository's **Security** tab (GitHub Private Vulnerability Reporting). This
opens a private advisory visible only to the maintainers.

Please include:

- A description of the issue and the impact you believe it has.
- Steps to reproduce (a minimal proof-of-concept is ideal).
- Affected component(s) — e.g. `backend/app/auth.py`, the Advisor agent, the
  PDF renderer — and any relevant configuration.
- Your assessment of severity, if you have one.

### What to expect

- **Acknowledgement:** within 3 business days.
- **Triage & initial assessment:** within 7 business days.
- **Fix timeline:** communicated after triage; critical issues are
  prioritized. We will keep you updated and credit you in the advisory once a
  fix ships, unless you prefer to remain anonymous.

## Scope

In scope:

- Authentication / session handling, CSRF, and authorization (cross-user
  access) in the backend API.
- Prompt-injection and tool-capability boundaries in the AI agents
  (`backend/app/agents/`).
- PDF generation / file handling (`backend/app/services/pdf.py`,
  `report.py`).
- Secret handling and dependency vulnerabilities.

Out of scope:

- Findings that require a compromised host, a malicious local operator, or
  physical access.
- Denial of service from unrealistic request volumes against a single-tenant
  local deployment.
- Issues in third-party dependencies that are already publicly known and
  tracked upstream (please still let us know if we are shipping a vulnerable
  pin).

## A note on intended use

NetPlanner is **advisory software**: every output — TCO models, vendor
comparisons, pricing — is a recommendation for human review, not an automated
financial or procurement action. Treat its output accordingly.
