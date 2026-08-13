# ChangeOps Authority Boundary Report

## What does Go own?
The Go host adapter owns the mechanics: reading the trusted local JSON configuration, mapping logical repository IDs to absolute trusted paths, invoking Git commands to gather evidence, durable local persistence of decision JSON files, timestamping, user-facing CLI orchestration, and dispatching the final bounded physical action (e.g. creating a Git tag).

## What does HowlFrame own?
HowlFrame strictly owns the authorization policy: it determines whether an action is permitted for the given branch and repository (checking `allowed_branches` and `allowed_actions`), verifies whether all required evidence states are met (e.g. working tree clean, tests/build PASS), checks for approval, identifies stale-evidence states, and ultimately returns the exact state transition (`ALLOW`, `DENY`, or `REQUIRE_APPROVAL`).

## Why is Go trusted?
Go is trusted because it operates at the boundary between the host OS and the HowlFrame VM. It possesses the capability to modify the filesystem, read configurations, and invoke processes. The architecture assumes the host itself is uncompromised; if the trusted host is malicious or its source code modified, it can bypass its own execution contracts. 

## Is HowlFrame the authorization policy engine?
Yes. Following the hardening audit, all policy enforcement—including branch allowances, action catalogs, and evidence checks—has been strictly relocated to the `.howl` policy, ensuring deterministic and testable evaluation.

## Is HowlFrame the complete security boundary?
No. HowlFrame is an authorization engine, not an OS sandbox. The architecture does not make a compromised Go host safe. The complete security boundary requires trust in the host execution environment, the integrity of the Go binary, and the integrity of the filesystem where the policy and configuration reside.

## Can Go execute a mutating action without HowlFrame ALLOW through normal ChangeOps control flow?
No. The `execute` command enforces that `ALLOW` must be explicitly returned by the HowlFrame evaluation of the current state, and the decision file's normalized digest must match the evaluated context, ensuring that the executed action strictly follows policy approval.

## How many mutation paths exist?
There are two mutating action definitions implemented in the host adapter: `create_release_candidate` and `record_release_ready`.

## How many require HowlFrame ALLOW?
All of them (2/2).

## Are allowed branches enforced?
Yes. The Go adapter passes `allowed_branches` from the trusted configuration to HowlFrame as evidence parameters. HowlFrame ensures that any mutating operation's branch must be a member of the allowed branches list.

## Are allowed actions enforced?
Yes. Similar to branches, `allowed_actions` is provided by the trusted config. HowlFrame denies any proposal requesting an action not listed in this set.

## Are approvals bound to exact evaluated context?
Yes. The evaluated context (including action, repo, and revision) is hashed into a canonical application-level `digest` stored on the decision record. This creates an integrity binding that prevents transferring approval between different contexts.

## Can persisted decisions be altered after approval?
No. If the decision file is modified post-evaluation (e.g. changing the action or repository), the `digest` validation will fail during the execution phase, immediately denying the action.

## Does stale evidence fail closed?
Yes. The execution phase gathers current evidence (`current_revision`) and provides it alongside the originally evaluated evidence (`revision`). HowlFrame compares these and fails closed with a `STALE_EVIDENCE` `DENY` decision if they differ.

## Does HowlFrame failure fail closed?
Yes. If HowlFrame cannot run, crashes, or produces invalid output, the Go adapter captures the error and terminates without executing any mutating actions. There is no permissive fallback.

## Are capability grants proposal-controlled?
No. The proposal only contains `action`, `repo`, `reason`, and `confidence`. These are strictly consumed as strings by HowlFrame. The Go adapter independently supplies the HowlFrame capability flags (e.g., `-allow-caps filesystem`) based on its trusted code.

## Can proposal data become arbitrary commands?
No. The execution command uses a hardcoded switch statement against known string literals (e.g. `"create_release_candidate"`). Arguments to OS commands (like `git tag`) are constructed predictably without opening a shell process, eliminating shell-injection risks.

## Are host adapter mechanics appropriately separated from policy?
Yes. The Go adapter passes gathered evidence and trusted configuration facts to HowlFrame. It does not conditionally block or allow workflows based on its own branch or action logic; it merely respects the deterministic `ALLOW`/`DENY` emitted by the policy.

## How much Go remains?
The Go host adapter consists of roughly 400 lines of code.

## Why is that amount of Go acceptable or unacceptable?
It is highly acceptable. The Go code correctly delegates all security decision-making to the policy while retaining responsibility for mechanics such as JSON serialization, Git interfacing, and configuration loading. Attempting to rewrite these mechanical operations in HowlFrame would complicate the policy layer without improving the authorization boundary.

## Did ChangeOps expose a HowlFrame platform gap?
No. The HowlFrame CLI interface and bytecode logic primitives were fully sufficient to construct a complete, context-aware authorization system, including digesting configuration facts and executing conditional assertions. No modifications to HowlFrame core were required.
