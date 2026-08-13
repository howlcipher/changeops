#!/bin/bash
set -e

# Setup temp repo to avoid test state leakage
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
git add main.go go.mod .gitignore
git commit -m "add go mock profile"

cd - > /dev/null
PROJECT_DIR=$PWD
export PATH="$PROJECT_DIR:$PATH"
export CHANGEOPS_BASE="$TEMP_REPO/.changeops"
mkdir -p config
cat <<CONFIG_EOF > config/changeops-config.json
{
  "repos": {
    "testrepo": {
      "path": "$TEMP_REPO",
      "allowed_branches": ["main"],
      "validation_profile": "go",
      "allowed_actions": [
        "create_release_candidate"
      ]
    }
  }
}
CONFIG_EOF

# Build
cd adapter && go build -o ../changeops
cd ..
~/.local/bin/howlframe build src/changeops.howl

# Ensure repo is validated so evidence is fresh
./changeops validate testrepo

echo "=== Adversarial Tests ==="
FAILURES=0

run_adv() {
  local name=$1
  local proposal=$2
  local expected_outcome=$3
  echo "Testing: $name"
  echo "$proposal" > tests/adv_prop.json
  local out=$(./changeops evaluate tests/adv_prop.json 2>&1)
  
  if [ "$expected_outcome" == "UNKNOWN_REPOSITORY" ]; then
    if echo "$out" | grep -q "UNKNOWN_REPOSITORY"; then
      echo "  PASS: Stopped securely (Unknown repo)"
      return
    fi
  elif [ "$expected_outcome" == "DENY" ]; then
    if echo "$out" | grep -q "Decision: DENY"; then
      echo "  PASS: Stopped securely (Decision: DENY)"
      return
    fi
  elif [ "$expected_outcome" == "REQUIRE_APPROVAL" ]; then
    if echo "$out" | grep -q "Decision: REQUIRE_APPROVAL"; then
      echo "  PASS: Stopped securely (Decision: REQUIRE_APPROVAL)"
      return
    fi
  fi
  
  echo "  FAIL: Did not see expected secure outcome '$expected_outcome'. Output was:"
  echo "$out"
  FAILURES=$((FAILURES+1))
}

run_adv "Unknown repo" '{"action":"create_release_candidate","repo":"unknown","reason":"..."}' "UNKNOWN_REPOSITORY"

run_adv "Path traversal repo" '{"action":"create_release_candidate","repo":"../../etc/shadow","reason":"..."}' "UNKNOWN_REPOSITORY"

run_adv "Absolute path repo" '{"action":"create_release_candidate","repo":"/etc/passwd","reason":"..."}' "UNKNOWN_REPOSITORY"

run_adv "Unknown action" '{"action":"delete_database","repo":"testrepo","reason":"..."}' "DENY"

run_adv "Command injection reason" '{"action":"create_release_candidate","repo":"testrepo","reason":"\"; rm -rf /;\""}' "REQUIRE_APPROVAL"

run_adv "Missing fields" '{"confidence":0.9}' "UNKNOWN_REPOSITORY"

echo "Testing: Unknown action execution does not mutate"
DECISION_ID="decision-unknown"
mkdir -p .changeops/decisions

PAYLOAD="delete_database|testrepo|fake|ALLOW"
DIGEST=$(echo -n "$PAYLOAD" | sha256sum | awk '{print $1}')
cat <<DEC_EOF > ".changeops/decisions/$DECISION_ID.json"
{
  "decision_id": "$DECISION_ID",
  "proposal": {
    "action": "delete_database",
    "repo": "testrepo",
    "reason": "adversarial"
  },
  "evidence": {
    "repo": "testrepo",
    "branch": "main",
    "revision": "fake",
    "current_revision": "fake",
    "working_tree": "clean",
    "tests": "PASS",
    "build": "PASS",
    "approved": "true",
    "candidate_exists": "false"
  },
  "result": "ALLOW",
  "reason": "fake",
  "digest": "$DIGEST"
}
DEC_EOF

OUT=$(./changeops execute $DECISION_ID 2>&1 || true)
if echo "$OUT" | grep -q "Execution DENIED: DENY"; then
  echo "  PASS: Stopped securely during execution (Execution DENIED) with no mutation"
else
  echo "  FAIL: Unknown action execution did not stop securely. Output was:"
  echo "$OUT"
  FAILURES=$((FAILURES+1))
fi
rm -f .changeops/decisions/$DECISION_ID.json

rm -f tests/adv_prop.json

if [ $FAILURES -eq 0 ]; then
  echo "ALL ADVERSARIAL TESTS PASSED"
else
  echo "$FAILURES ADVERSARIAL TESTS FAILED"
  exit 1
fi
