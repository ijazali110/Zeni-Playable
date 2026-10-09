# Zeni PlayAd — Staging Implementation Notes

This branch is **not deployed**. Production remains the original Playable Cave Pro.

## Approved entitlements
- Free: Unity Ads, TikTok, Pangle, Meta. Three *lifetime* successful exports. Converter forbidden.
- Pro: the same four network families. Thirty successful exports per verified subscription billing period. Converter allowed.
- Business: all supported networks, all existing tool features, no monthly export quota.
- Admin/developer: separate server-side role, never inferred from plan.
- Failed export does not consume quota. Reserved jobs prevent parallel quota bypass.
- A generated file must only be made available after server-side export validation and quota reservation. Browser-only enforcement is insecure.

## Status
- `staging/index.html`: branding-only fork of the active HTML. Not yet a completed rebrand; old logo/legacy labels may remain.
- `saas/entitlements.py`: atomic SQLite export reservation / completion and converter feature gating. Internal staging library; NOT integrated with HTML UI or authenticated HTTP API.
- `saas/smoke_test.py`: initial smoke checks.
- Existing live converter must not be overwritten during rollout.

## Next integration gates
1. Authenticated user accounts, email verification, admin RBAC, device-session management, verified subscription billing webhooks.
2. HTTP endpoint providing server-enforced export reservation, validated artifact delivery and completion; ensure cannot bypass via old browser direct export/download functions. Do not ship paywall by hiding buttons alone.
3. Usage reservations need stale-job expiration/reconciliation and an atomic billing-period switch; payment cancellation/refund handling.
4. Anti-abuse: rate limits per account/IP/device; disposable email reputation; CAPTCHA/challenges, appeal/allowlist and audit logs. Hash/truncate IP and avoid permanent fingerprint claims.
5. Developer-only OpenAI key: encrypted at rest using a server-owned encryption key; no API key in public JS/HTML or logs. Safe structured repair proposals with sandbox diff, validation, rollback, strict budget, no unrestricted shell execution.
6. Regression fixtures for Unity Ads, AppLovin, Mintegral, Meta, TikTok/Pangle and edge cases. Network validation cannot guarantee partner approval.
7. Staging deployment and end-to-end QA before controlled production cutover.

## Business decisions pending
Plan prices, payment provider, subscription period source, account verification sender/provider, and exact AI repair billing/credit treatment.

## Major update staging checkpoint
- `saas/server.py`: localhost-only staging API with hashed expiring bearer tokens, plan introspection, developer-only AI status, and quota reservation. Tokens are currently provisioned by trusted code; there is no public signup/payment integration.
- `saas/abuse.py`: privacy-aware IP-prefix/device-hint velocity signals. This provides challenge/review recommendations, not automatic bans. Requires protected signup flow and CAPTCHA provider integration.
- `saas/test_api.py`: API permission and quota regression tests.
- IMPORTANT: export reservation API does NOT generate or deliver a verified playable artifact yet. The live browser converter is not gated. Never expose this API publicly or treat it as billing-ready.
- AI status endpoint does not call OpenAI. Developer key configuration and safe repair pipeline remain pending.
