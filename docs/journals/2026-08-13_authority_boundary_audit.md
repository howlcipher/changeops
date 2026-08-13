# Goal

Make the trust boundary explicit, minimal, testable, and difficult to bypass. We must be able to state: "No mutating ChangeOps effect can occur unless the exact operation, repository, revision, trusted policy configuration, evidence, and approval state have received a valid HowlFrame ALLOW decision."

# Starting SHA

cfae238366e2df3d4f3fe82ea98746df75f1b02c

# Current architecture

UNTRUSTED PROPOSAL
        ↓
TRUSTED EVIDENCE COLLECTION
        ↓
HOWLFRAME POLICY
        ↓
ALLOW / DENY / REQUIRE_APPROVAL
        ↓
BOUNDED HOST EFFECT

# Trust assumptions

Go host is trusted code for OS/Git mechanics, reading local config, filesystem mechanics, etc. HowlFrame is the authorization policy engine.

# Known concerns

The Go host adapter (adapter/main.go) might contain policy evaluation, such as checking `AllowedBranches` and `AllowedActions`, instead of correctly providing this information to HowlFrame so HowlFrame can make the decision.

# Hypotheses

- Go adapter currently implements business policy checks independently.
- Validation caching or execution state might not be securely bound to the evaluated decision context.
- Modifying the persisted decision file might bypass authority.

# Non-goals

- Eliminate Go completely.
- Make HowlFrame implement Git, persistence, timestamps, or OS mechanics.

## What I inspected

`adapter/main.go`, `src/changeops.howl`, `config/changeops-config.example.json`, and `tests/`.

## Authority owner

Currently, `AllowedBranches` and `AllowedActions` are defined in the Go host's configuration struct `ConfigRepo`. However, they are NEVER passed to HowlFrame in `invokeHowlFrame`. Furthermore, the Go execution engine (`execute` command) only checks if the action string matches hardcoded values (`create_release_candidate` or `record_release_ready`).

## Potential bypass

1. **Allowed Branch Bypass**: `changeops.howl` does not evaluate branches, and the host adapter does not check it either. A proposal on a forbidden branch gets evaluated identically to an allowed branch and returns `REQUIRE_APPROVAL` or `ALLOW` if evidence matches.
2. **Allowed Action Bypass**: A repository configured to only allow `record_release_ready` can successfully request `create_release_candidate` and get `REQUIRE_APPROVAL` because `changeops.howl` does not verify the action against a trusted list of allowed actions.
3. **Decision Mutation**: Decisions are saved as JSON files in `.changeops/decisions/`. The ID is a hash of `action-revision-time`, but the file content can be mutated (e.g. changing the `repo` or evidence fields). If an attacker changes `repo` and the corresponding `revision` to match another repo, they can effectively transfer an approval to execute an action on a different repository.

## Test performed

Wrote `tests/authority_bypass_test.sh` containing 3 bypass tests.
1. Branch bypass: requested RC on `feature-branch` where config allowed only `main`.
2. Action bypass: requested RC where config allowed only `record_release_ready`.
3. Decision mutation bypass: modified a decision file to transfer the target repo to another repo.

## Result

- The Branch bypass test FAILED (allowed branch was not enforced; proposal returned `REQUIRE_APPROVAL`).
- The Action bypass test FAILED (allowed action was not enforced; proposal returned `REQUIRE_APPROVAL`).
- The Decision mutation bypassed was somewhat mitigated by `STALE_EVIDENCE` checks, but can be fully bypassed if the attacker also mutates the `evidence.revision` in the JSON to match the target repository.

## Next step

Commit the test script characterizing the current behavior. Then fix the policy by passing trusted branch and action config to HowlFrame and updating `changeops.howl` to enforce them.
