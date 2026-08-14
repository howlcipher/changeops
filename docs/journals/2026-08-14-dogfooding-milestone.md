# Dogfooding Milestone - August 14, 2026

## Self-Dogfooding Implementation
Today we achieved full self-dogfooding for ChangeOps. We successfully mapped the root repository into the trusted configuration boundaries and built a first-class `changeops dogfood` command. This effectively simulates an AI agent proposing a release candidate specifically against the ChangeOps repository itself.

The boundary holds strong: When `dogfood` runs, it correctly identifies the root directory, executes the local validation profile (now supported via a root-level `go.mod`), constructs the Evidence Envelope, and passes it into HowlFrame for evaluation. The determinism works perfectly: it refuses to silently self-approve, consistently outputting `REQUIRE_APPROVAL` when the working tree is clean and the validation passes.

## GitHub Remote Evidence
We introduced a significant new capability: gathering trusted remote evidence from GitHub using the `gh` CLI. By doing this in the Go host adapter during `gatherEvidence`, we prevented the AI proposal from owning any tokens or authorization capabilities.

The evidence includes:
- Remote HEAD SHA
- CI Check Status
- Whether local and remote SHAs agree
- Existing Release presence

This is now plumbed completely through to HowlFrame. To provide true Time-Of-Check to Time-Of-Use (TOCTOU) protection, we check `STALE_REMOTE_EVIDENCE` inside `changeops.howl`. If the remote repository has advanced past the revision authorized during `evaluate`, the `execute` phase forcefully denies the operation.

## Bounded GitHub Side-Effects
We added a single bounded remote effect: `create_github_draft_release`. Instead of giving the AI an arbitrary "run gh release" string, it is strictly mapped. HowlFrame evaluates if the local tag exists, if the revisions match, and if the remote head is stable. Only then does it allow execution. The verification phase then re-queries GitHub to prove the release actually exists before creating the audit receipt.

## Findings on HowlFrame
The integration process confirmed that HowlFrame can effectively handle reasonably complex multi-variable state evaluations.

**What worked naturally**:
The determinism. Being able to rely completely on the HowlFrame `.hfbc` artifact to reject stale evidence without rewriting the logic in Go is very powerful. It successfully bounded the new `create_github_draft_release` action natively.

**What was awkward**:
Nesting `let` statements in Lisp-like `.howl`. With the addition of remote variables, our `changeops.howl` now has around 33 nested `let` statements! Managing the closing parentheses `))))))))))...` manually is very fragile and prone to compiler errors like `Expected ')'`.

**Missing primitives discovered**:
HowlFrame needs a flatter variable assignment system (like an `assign` keyword or implicit block scope) so we do not have to deeply nest every single bound variable. 

**Changes required**:
No changes to HowlFrame itself were required to support this! However, managing `.howl` in ChangeOps required extensive careful bracket management. 

## Conclusion
ChangeOps can now securely dogfood itself and interact safely with remote GitHub state without widening the capabilities available to untrusted AI proposals.
