# ChangeOps

A local AI-assisted Git change and release controller built on HowlFrame.

Website: https://howlcipher.github.io/changeops/

## What problem does it solve?
ChangeOps bridges the gap between AI proposals and production reality using bounded execution. AI agents are excellent at reasoning about when a release candidate should be created, but they cannot be given unconstrained authority to mutate your repository. ChangeOps proves that **intent is not authority**. It allows an AI (or a user) to propose actions, strictly validates intent via deterministic `HowlFrame` capability checks, requires trusted approval for state mutations, and executes bounded operations securely.

## Five-minute demo
1. **Initialize Repositories**: Configure local Git repos securely in `config/changeops-config.json`. Set `CHANGEOPS_APPROVAL_KEY_FILE` to point to a secure key.
2. **Inspect**: `changeops inspect my_repo` retrieves verifiable Git states.
3. **Validate**: `changeops validate my_repo` runs tests and stores status safely in a cryptographically bound Evidence Envelope.
4. **Evaluate**: Submit a JSON intent (e.g. `{"action": "create_release_candidate", "repo": "my_repo"}`). ChangeOps evaluates against a compiled `.hfbc` bytecode logic policy via the HowlFrame VM, safely outputting an evaluation decision (e.g. `REQUIRE_APPROVAL`).
5. **Approve**: A human validates and signs off on the exact deterministic decision snapshot via `changeops approve <decision_id>`, which generates an HMAC-SHA256 signature using the trusted key.
6. **Execute**: `changeops execute <decision_id>` performs a bounded action (like creating a local Git tag) *only* if the repo's evidence is not stale (`STALE_EVIDENCE`) and the approval hasn't already been consumed.

## Architecture
ChangeOps consists of two core boundaries:
1. **The Policy Authority (HowlFrame)**: `changeops.howl` compiles into `changeops.hfbc`. It parses inputs, consumes evidence, checks conditions, and enforces transitions resulting in `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`. 
2. **The Host Adapter (Go)**: The Go application handles Git inspection, executes bounded commands securely, and invokes the HowlFrame runtime under strict sandbox capabilities. 

## Intent is not authority
Proposals dictating actions, logic overrides, or fake approval metrics (like passing `"approved": true`) within the JSON payload are categorically rejected. AI dictates the proposition; HowlFrame owns the authorization machinery.

## Installation
Build the ChangeOps adapter:
```bash
cd adapter
go build -o ../changeops
```

Compile the authoritative policy layer:
```bash
howlframe check src/changeops.howl
howlframe build src/changeops.howl
```

## HowlFrame dependency
ChangeOps consumes **HowlFrame v0.1.0** entirely via its public CLI interface. It is independent of HowlFrame's source code, serving as real-world dogfooding for the platform's release candidates. See the dogfooding report in `docs/howlframe_dogfooding_report.md` for findings.

## Configuration
Configure repositories securely via `config/changeops-config.json`. Refer to the `.example.json` file for mapping logical repo IDs to physical absolute paths and their bounded actions.

## Inspect
```bash
changeops inspect <repo_id>
```
Gathers current evidence, git branch, tag state, and working tree clean/dirty status.

## Validate
```bash
changeops validate <repo_id>
```
Executes the predefined validation profile bounded by configuration limits (e.g. `go test ./...` and `go build ./...`) and caches the state.

## Evaluate
```bash
changeops evaluate proposal.json
```
Evaluates an intent payload. Outputs a decision and binds a `decision_id` for approval gating.

## Approval
```bash
changeops approve <decision_id>
```
Provides trusted authorization context binding directly to a decision state without relying on input intent parameters.

## Execution
```bash
changeops execute <decision_id>
```
Gathers current state evidence, verifies no TOCTOU drift has occurred (safely denying with `STALE_EVIDENCE` if so), and executes the strictly bounded physical change (e.g., git tagging).

## History
```bash
changeops history
```
Outputs the JSON lines audit trail of evaluation and execution logic.

## Trust boundary
- **AI Proposal:** Can dictate the logical repo ID, action to pursue, and descriptive reasons.
- **ChangeOps Adapter:** Maps logical IDs to true absolute paths, handles true process invocations securely.
- **HowlFrame Policy:** Retains exclusive ownership over capabilities, validation requirements, and approvals.

## Security limitations
This V0.2 architecture bounds logical actions within a local operational domain utilizing the Host Go Adapter wrapper and HowlFrame's execution capabilities. It establishes a strong local trusted evidence foundation with HMAC-SHA256 approvals and strict replay prevention. It is not yet integrated with remote GitHub API ingestion (slated for v0.3).

## Dogfooding findings
ChangeOps was designed as the first independent external application to evaluate HowlFrame v0.1's usability. It found significant success building policy boundaries directly atop HowlFrame's CLI and bytecode primitives. Read `docs/howlframe_dogfooding_report.md` for complete results.

## Business mapping
The local ChangeOps implementation mirrors enterprise DevOps CI/CD integration models: AI acts as the proposer, a deterministic authority layer strictly handles permissions, and a trusted executor pushes the physical bounds only within predetermined logic loops.
