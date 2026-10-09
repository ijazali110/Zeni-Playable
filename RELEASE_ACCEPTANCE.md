# Zeni PlayAd — Unified Release Acceptance Matrix

Release branch: feature/zeni-playad-saas. Production remains unchanged.

| Area | Required acceptance criterion | Current state |
| --- | --- | --- |
| Branding | No legacy names in final navigation, logo, favicon, footer, exports | Partial staging text replacement |
| Accounts | Verified sign-up/login/reset/session/revocation, email sending, CSRF/CORS, rate limits | Identity & verification primitives only |
| Free | 3 lifetime successful exports, Unity/TikTok/Pangle/Meta only; no converter | Quota library tested; web bypass unresolved |
| Pro | 30 per verified billing cycle, same 4 networks, converter enabled | Quota library tested; billing missing |
| Business | All supported networks and existing tool features | Permission module tested |
| Fraud | Disposable domains, IP/device signals, challenge flow, admin review, appeals | Velocity signals only |
| Payment | Gateway webhooks, signature verification, subscription renewals/cancel/refunds | Not configured |
| Export | Server-controlled submission, generation and signed artifact retrieval | NOT implemented |
| Conversion | Runtime-tested adapters and original gameplay preservation | Existing browser logic only |
| Developer AI | Encrypted key, budget, safe structured proposals, sandbox retests/rollback | Developer status endpoint only |
| Admin | Account moderation, usage ledger, billing reconciliation, access audit | Not integrated |
| Testing | Representative Unity/Meta/Pangle/AppLovin/Mintegral fixture matrix | Structural / API unit tests only |
| Deployment | Staging domain, secrets, monitoring, backups, rollback, production smoke | Not deployed |

## Hard release gates
1. Never publish browser-only premium restrictions; keep all proprietary transformations gated through authenticated server-side export pipeline.
2. Don't accept client-provided "success" or "plan" fields as entitlement evidence.
3. Preserve existing gameplay and converter code until fixture-based regression proves compatibility.
4. OpenAI is advisory/patch proposal only, without arbitrary code execution or direct production mutating authority.
5. Make no live Nginx changes or replace production `index.html` until account, billing, subscription enforcement, end-to-end export, and rollback test gates pass.
6. All payment and provider integrations require valid credentials and real webhook verification.
7. Live use must not be represented as safe or ready just because unit tests pass.

## Run staging unit suite
`cd saas && python3 -m unittest test_accounts test_api test_artifacts -v && python3 smoke_test.py`

## Source integrity
Current production source snapshot is in repository root `index.html`, while branding work is isolated in `staging/index.html`.
