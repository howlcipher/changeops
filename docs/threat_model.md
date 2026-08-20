# HowlChangeOps Threat Model

## Trusted Components

*   **HowlChangeOps Binary:** Must be compiled from untampered source code and run in a trusted local environment.
*   **Local Host:** Assumes a secure operating system where unauthorized users cannot intercept execution, replace binaries, or extract keys from memory.
*   **Trusted Repository Configuration:** The `config/howlchangeops-config.json` (or fallback `config/changeops-config.json`) is assumed to be controlled by administrators and resistant to unauthorized tampering.
*   **Approval Key / Signing Authority:** The HMAC-SHA256 secret key located outside the repository (via `HOWLCHANGEOPS_APPROVAL_KEY_FILE` or `CHANGEOPS_APPROVAL_KEY_FILE`) is considered secure.
*   **HowlFrame Runtime and Policy Artifact:** The `howlchangeops.hfbc` compiled policy file is assumed to reflect genuine administrator intent and cannot be tampered with by untrusted actors.

## Untrusted Components

*   **Proposal JSON:** Input proposals from AI or users are strictly untrusted intent.
*   **AI Output:** Any claims made by the AI (e.g. `approved: true`, overrides) are entirely ignored for authorization purposes.
*   **Arbitrary Repository Contents:** Source code modifications are considered untrusted until validated by a trusted profile and approved.
*   **AI Attempts to Claim Approval:** Any forgery attempts such as trying to manually create a signed approval artifact.

## Protected Against

*   **Approval Forgery:** Modifying action, repo, revision, expiry, decision digest, or evidence digest in an approval JSON invalidates it (detected via HMAC-SHA256).
*   **Replay Attacks:** Approvals cannot be executed multiple times. An execution receipt invalidates subsequent attempts.
*   **Evidence Staleness / Cache Poisoning:** Validation cache is strictly bound to repository, revision, validation profile, and configuration digest. Changes to source or trusted config invalidate prior validation.
*   **Cross-context Transfer:** Approvals cannot be moved between different repositories, revisions, or decisions due to strict binding.
*   **Proposal Escalation:** Proposals containing fake override flags or alternative logic are inherently impotent because HowlFrame ignores them.
*   **Time-of-Check to Time-of-Use (TOCTOU) Drift:** Local and remote commit drift detection fail closed (`STALE_EVIDENCE`, `STALE_REMOTE_EVIDENCE`).

## Not Protected Against

*   **Compromised Host / Root Access:** If an attacker has root on the host machine, they can extract the signing key, replace the HowlChangeOps binary, or directly bypass HowlChangeOps to interact with Git.
*   **Malicious Administrator Configuration:** If a trusted administrator configures a dangerous validation profile or alters HowlFrame policy to be overly permissive, the system will execute it.
*   **Stolen HMAC Key:** If the key configured via `HOWLCHANGEOPS_APPROVAL_KEY_FILE` is compromised, an attacker can mint valid approvals for any decision.
