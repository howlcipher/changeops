# HowlFrame Dogfooding Report

## Is ChangeOps a real application?
Yes. ChangeOps acts as a real-world release controller, demonstrating actual external impacts (creating release candidate tags in a Git repository) guided by a deterministic security boundary powered by HowlFrame.

## Can the owner actually use it?
Yes, it can be executed from a local machine on any local Git repository specified within `changeops-config.json` by invoking the bounded Go adapter commands (`inspect`, `validate`, `evaluate`, `approve`, `execute`).

## Can it operate against arbitrary configured personal repositories?
Yes. A developer can specify any repository path locally, along with allowed validation profiles and branches. The adapter validates against that specific repo.

## What real external effect does it perform?
It creates an annotated Git tag locally, representing a Release Candidate, bound tightly to the specific Git commit revision that was validated.

## Is HowlFrame actually the authority layer?
Yes. The Go adapter strictly delegates policy evaluation to `changeops.hfbc`, a bytecode artifact compiled from `.howl`. The execution command only proceeds if HowlFrame produces an `ALLOW` decision.

## Can proposal data become arbitrary execution?
No. The proposal JSON allows expressing intent, reasoning, and parameters, but it cannot override the underlying policy logic or force the host adapter into executing an unmapped command or an arbitrary shell script.

## Can AI self-approve?
No. An adversarial test with `{"approved": true, "admin": true, "override": true}` was correctly caught by the HowlFrame policy which demanded independent approval bindings outside the proposal data payload.

## Can AI widen capabilities?
No. Capabilities are granted explicitly by the runner (`-allow-caps filesystem`), isolating execution capabilities from AI output.

## Are repo paths trusted?
Yes, via `changeops-config.json`. The AI only provides a logical ID (e.g. `"howlframe"`). Absolute paths mapping to those IDs are managed securely in the configuration file, preventing directory traversal or untrusted local access.

## Are commands trusted?
Yes. The commands executed by the Go adapter are hardcoded shell commands with verified deterministic arguments, rejecting arbitrary command execution. 

## Are approvals bound to decisions?
Yes. Approvals are tied specifically to the unique `decision_id` hashed against the action and the revision, guaranteeing that approvals apply exclusively to the exact context that was evaluated.

## Is evidence bound to a Git revision?
Yes. Revisions are verified during `evaluate` and are then stored in the decision payload.

## Does stale evidence fail safely?
Yes. By comparing `ev_revision` with `ev_current_revision`, execution is forcefully denied (`STALE_EVIDENCE`) if the repository has been mutated post-approval.

## Does state persist adequately?
Yes. Decisions, including pending approvals and a chronological audit log (`history.jsonl`), are managed effectively using local file persistence (`.changeops/decisions/`).

## How usable was HowlFrame outside its own repository?
Very usable. The toolchain successfully functioned completely disconnected from the source code, leveraging the pinned release tag of v0.1.0 downloaded via standard release artifacts.

## Which HowlFrame features worked naturally?
- The compiler toolchain (`howlframe build` and `howlframe check`).
- Basic structural statements, conditionals (`if`, `do`), variable assignments (`set`), parsing JSON strings, and mapping dictionaries (`map_get`).
- Zero-trust default execution (requiring explicit `--allow-caps`).

## Which were awkward?
- Parsing CLI arguments via `=` (`repo=howlframe`) and splitting manually is verbose; there is no native key-value argument flag parser yet.
- The `--allow-caps` flag position requires strict formatting preceding the artifact which can be tricky to uncover (documented mismatch between help string and parsing reality).

## Which blocked development?
No absolute blockers.

## How many HowlFrame core changes were required?
0. ChangeOps successfully built purely off the released v0.1.0 boundary.

## What should HowlFrame improve next based ONLY on this evidence?
1. Enhanced standard library components for CLI argument parsing.
2. Align `howlframe` help text CLI syntax representation regarding capability flags.
