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
