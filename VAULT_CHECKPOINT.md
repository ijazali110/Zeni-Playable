## Export artifact vault checkpoint
- `saas/vault.py`: binary HTML/ZIP submission to isolated private storage (mode 0600) after structural checks and atomic quota reservation. SHA-256 integrity and ownership checks. No public delivery route.
- `saas/test_vault.py`: invalid submission, quota limits, owner isolation, and quarantined artifact checks.
- Vault remains a staging library; it is NOT integrated with an authenticated file-upload endpoint, real conversion processing, ad-network runtime certification, signed downloads, payment, or developer AI repair.
- IMPORTANT: Quarantined bytes do not represent a successful export. Reservation expiry and cleanup must be coordinated with artifact records before production. Never settle payment/quotas based only on this upload.
