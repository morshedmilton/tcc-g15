# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.8.x   | :white_check_mark: |
| < 1.8.0 | :x:                |

## Reporting a Vulnerability

Because this software controls thermal and fan behavior through ACPI firmware interfaces, safety vulnerabilities (such as bypasses of the fail-safe temperature threshold, infinite fan stops, or privilege escalations) are treated with critical priority.

If you discover a security or hardware safety issue:
1. Please do **NOT** open a public issue.
2. Email the maintainer directly at morshed2004milton@gmail.com with:
   - Laptop model and BIOS version
   - Reproduction steps and PoC
   - Description of the safety or security impact
3. We will acknowledge receipt within 48 hours and work with you on a responsible disclosure and patch.
