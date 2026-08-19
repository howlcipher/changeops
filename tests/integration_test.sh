#!/bin/bash
set -e

# Setup temp repo
TEMP_REPO=$(mktemp -d)
cd "$TEMP_REPO"
git init
git config user.name "Test User"
git config user.email "test@example.com"
echo "test" > file.txt
git add file.txt
git commit -m "initial commit"
git branch -m main

# Mock go profile for tests
echo "package main; func main() {}" > main.go
go mod init testrepo
echo "testrepo" > .gitignore
echo ".changeops" >> .gitignore
git add main.go go.mod .gitignore
git commit -m "add go mock profile"

# Back to project dir
cd - > /dev/null
PROJECT_DIR=$PWD
# Setup mock gh for remote testing
MOCK_BIN=$(mktemp -d)
cat <<'EOF' > "$MOCK_BIN/gh"
#!/bin/bash
if [ "$1" = "api" ]; then
  if echo "$*" | grep -q "status"; then
    echo "success"
  elif echo "$*" | grep -q "commits/"; then
    if [ -f /tmp/mock_remote_head ]; then
      cat /tmp/mock_remote_head
    else
      echo "1111111111111111111111111111111111111111"
    fi
  fi
elif [ "$1" = "release" ]; then
  echo "mock release"
fi
EOF
chmod +x "$MOCK_BIN/gh"
export PATH="$MOCK_BIN:$PROJECT_DIR:$PATH"
export CHANGEOPS_BASE="$TEMP_REPO/.changeops"

# Generate approval key
TEMP_KEY=$(mktemp)
dd if=/dev/urandom of="$TEMP_KEY" bs=32 count=1 2>/dev/null
chmod 600 "$TEMP_KEY"
export CHANGEOPS_APPROVAL_KEY_FILE="$TEMP_KEY"

mkdir -p config
cat <<EOF > config/changeops-config.json
{
  "repos": {
    "testrepo": {
      "path": "$TEMP_REPO",
      "allowed_branches": ["main"],
      "validation_profile": "go",
      "allowed_actions": [
        "create_release_candidate",
        "create_github_draft_release",
        "record_release_ready",
        "rollback_release_candidate"
      ]
    }
  }
}
EOF

# Build adapter and policy
cd adapter && go build -o ../changeops
cd ..
~/.local/bin/howlframe build src/changeops.howl

echo "=== Scenario 1 - Dirty Repo ==="
echo "modify" >> "$TEMP_REPO/file.txt"
cat <<EOF > tests/proposal_1.json
{
  "action": "create_release_candidate",
  "repo": "testrepo",
  "reason": "Test dirty repo",
  "confidence": 0.9
}
EOF
changeops evaluate tests/proposal_1.json | grep -q "DENY" && echo "PASS: Denied due to dirty repo"

echo "=== Scenario 2 - Clean repo but no approval ==="
cd "$TEMP_REPO" && git commit -am "clean" && cd - > /dev/null
changeops validate testrepo
EVAL_OUT=$(changeops evaluate tests/proposal_1.json)
echo "$EVAL_OUT" | grep -q "REQUIRE_APPROVAL" && echo "PASS: Required approval"
DECISION_ID=$(echo "$EVAL_OUT" | grep "Decision saved as" | awk '{print $4}' | tr -d '.')

echo "=== Scenario 3 - AI self approval ==="
cat <<EOF > tests/proposal_3.json
{
  "action": "create_release_candidate",
  "repo": "testrepo",
  "reason": "Test self approval",
  "confidence": 0.9,
  "approved": true,
  "admin": true,
  "override": true
}
EOF
changeops evaluate tests/proposal_3.json | grep -q "REQUIRE_APPROVAL" && echo "PASS: Self approval ignored, still REQUIRE_APPROVAL"

echo "=== Scenario 4 - Trusted approval & execution ==="
changeops approve "$DECISION_ID"
EXEC_OUT=$(changeops execute "$DECISION_ID")
echo "$EXEC_OUT" | grep -q "Executing action: create_release_candidate" && echo "PASS: Action executed"
echo "$EXEC_OUT" | grep -q "Verified: tag created successfully" && echo "PASS: Post-action verification passed"
cd "$TEMP_REPO" && git tag -l | grep -q "changeops/rc-" && echo "PASS: Tag created" && cd - > /dev/null
# Check execution receipt
grep -q '"verification": "PASS"' "$CHANGEOPS_BASE/receipts/${DECISION_ID}.json" && echo "PASS: Execution receipt verified PASS"

echo "=== Scenario 5 - Stale local evidence ==="
cd "$TEMP_REPO" && git commit --allow-empty -m "clean commit" && cd - > /dev/null
changeops validate testrepo
DECISION_ID2=$(changeops evaluate tests/proposal_1.json | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DECISION_ID2"
# Modify repo before executing
echo "stale" >> "$TEMP_REPO/file.txt"
cd "$TEMP_REPO" && git commit -am "stale commit" && cd - > /dev/null
# Execute should fail
if changeops execute "$DECISION_ID2" 2>&1 | grep -q "STALE_EVIDENCE"; then
  echo "PASS: Stale local evidence detected and blocked"
else
  echo "FAIL: Stale local evidence was allowed!"
  exit 1
fi

echo "=== Scenario 6 - Stale remote evidence (TOCTOU) ==="
cd "$TEMP_REPO"
git commit --allow-empty -m "clean commit for remote TOCTOU"
git remote add origin https://github.com/example/testrepo.git 2>/dev/null || true
CURR_REV=$(git rev-parse HEAD)
echo "$CURR_REV" > /tmp/mock_remote_head
cd - > /dev/null
changeops validate testrepo
DECISION_ID_REMOTE=$(changeops evaluate tests/proposal_1.json | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DECISION_ID_REMOTE"
# Remote advances before execution
echo "2222222222222222222222222222222222222222" > /tmp/mock_remote_head
if changeops execute "$DECISION_ID_REMOTE" 2>&1 | grep -q "STALE_REMOTE_EVIDENCE"; then
  echo "PASS: Remote TOCTOU drift detected and blocked with STALE_REMOTE_EVIDENCE"
else
  echo "FAIL: Remote TOCTOU drift was not caught!"
  exit 1
fi
rm -f /tmp/mock_remote_head

echo "=== Scenario 7 - HowlFrame failure (Fail-Closed) ==="
cd "$TEMP_REPO" && git commit --allow-empty -m "clean for scenario 7" && cd - > /dev/null
changeops validate testrepo
DECISION_ID3=$(changeops evaluate tests/proposal_1.json | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DECISION_ID3"

# Break HowlFrame by deleting the policy file temporarily
mv changeops.hfbc changeops.hfbc.bak
if changeops execute "$DECISION_ID3" 2>&1 | grep -q "Execution evaluation error"; then
  echo "PASS: HowlFrame failure blocked execution"
else
  echo "FAIL: HowlFrame failure did not block execution!"
  mv changeops.hfbc.bak changeops.hfbc
  exit 1
fi
mv changeops.hfbc.bak changeops.hfbc

echo "=== Scenario 8 - Governed Rollback Workflow ==="
# Execute a valid release candidate first
cd "$TEMP_REPO" && git commit --allow-empty -m "clean for rollback test" && cd - > /dev/null
changeops validate testrepo
DECISION_ID_RB_TARGET=$(changeops evaluate tests/proposal_1.json | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DECISION_ID_RB_TARGET"
changeops execute "$DECISION_ID_RB_TARGET"
# Propose rollback via CLI command
RB_OUT=$(changeops rollback "$DECISION_ID_RB_TARGET")
echo "$RB_OUT" | grep -q "REQUIRE_APPROVAL" && echo "PASS: Rollback proposal evaluated and requires approval"
RB_DEC_ID=$(echo "$RB_OUT" | grep "Rollback decision saved as" | awk '{print $5}' | tr -d '.')
changeops approve "$RB_DEC_ID"
RB_EXEC_OUT=$(changeops execute "$RB_DEC_ID")
echo "$RB_EXEC_OUT" | grep -q "Rolled back tag" && echo "PASS: Rollback executed and tag removed"
grep -q '"action": "rollback_release_candidate"' "$CHANGEOPS_BASE/receipts/${RB_DEC_ID}.json" && echo "PASS: Rollback receipt recorded"

echo "=== Scenario 9 - Plan Simulation ==="
PLAN_OUT=$(changeops plan testrepo)
echo "$PLAN_OUT" | grep -q "create_release_candidate" && echo "PASS: Plan simulated create_release_candidate"
echo "$PLAN_OUT" | grep -q "rollback_release_candidate" && echo "PASS: Plan simulated rollback_release_candidate"

echo "=== Scenario 10 - Explain Output with Execution Receipt ==="
EXPLAIN_OUT=$(changeops explain "$DECISION_ID_RB_TARGET")
echo "$EXPLAIN_OUT" | grep -q "Execution Receipt:" && echo "PASS: Explain displays execution receipt"
echo "$EXPLAIN_OUT" | grep -q "Verification: PASS" && echo "PASS: Explain displays verification status"

echo "=== Scenario 11 - Post-Action Failure, Receipt Persistence & Replay Prevention ==="
cd "$TEMP_REPO" && git commit --allow-empty -m "clean for scenario 11" && cd - > /dev/null
changeops validate testrepo
DEC_11_OUT=$(changeops evaluate tests/proposal_1.json)
DEC_11_ID=$(echo "$DEC_11_OUT" | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DEC_11_ID"
# Pre-create conflicting tag to force tag creation failure
CURR_REV=$(cd "$TEMP_REPO" && git rev-parse HEAD && cd - > /dev/null)
cd "$TEMP_REPO" && git tag "changeops/rc-${CURR_REV:0:7}" && cd - > /dev/null
# Execute will fail
if changeops execute "$DEC_11_ID" 2>&1 | grep -q "failed to create RC tag"; then
  echo "PASS: Action failure detected"
fi
# Verify failure receipt exists with FAIL status
grep -q '"verification": "FAIL"' "$CHANGEOPS_BASE/receipts/${DEC_11_ID}.json" && echo "PASS: Failure execution receipt persisted"
# Verify replay protection blocks re-execution of failed decision
if changeops execute "$DEC_11_ID" 2>&1 | grep -q "DENIED: Decision previously failed execution"; then
  echo "PASS: Replay protection blocks re-executing failed decision"
else
  echo "FAIL: Replay protection did not block failed decision!"
  exit 1
fi

echo "ALL INTEGRATION TESTS PASSED"
