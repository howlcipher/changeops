#!/bin/bash
set -e

TEMP_REPO=$(mktemp -d)
cd "$TEMP_REPO"
git init
git config user.name "Test User"
git config user.email "test@example.com"
echo "package main; func main() {}" > main.go
go mod init testrepo
echo "testrepo" > .gitignore
echo ".changeops" >> .gitignore
git add main.go go.mod .gitignore
git commit -m "add go mock profile"
git branch -m main

cd - > /dev/null
PROJECT_DIR=$PWD
export PATH="$PROJECT_DIR:$PATH"
export CHANGEOPS_BASE="$TEMP_REPO/.changeops"

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
      "allowed_actions": ["create_release_candidate"]
    }
  }
}
EOF

cd adapter && go build -o ../changeops && cd ..
~/.local/bin/howlframe build src/changeops.howl

cat <<EOF > tests/proposal_adv.json
{
  "action": "create_release_candidate",
  "repo": "testrepo",
  "reason": "Test adversarial",
  "confidence": 0.9
}
EOF

changeops validate testrepo
DECISION_ID=$(changeops evaluate tests/proposal_adv.json | grep "Decision saved as" | awk '{print $4}' | tr -d '.')
changeops approve "$DECISION_ID"

APPROVAL_FILE="$CHANGEOPS_BASE/approvals/${DECISION_ID}.json"

# Helper to test modification
test_mod() {
  field=$1
  new_val=$2
  sed -i "s/\"$field\": \".*\"/\"$field\": \"$new_val\"/" "$APPROVAL_FILE"
  if changeops execute $DECISION_ID 2>&1 | grep -q "DENIED: Approval integrity invalid"; then
    echo "PASS: modification to $field was rejected"
  else
    echo "FAIL: modification to $field was allowed!"
    exit 1
  fi
  # restore original
  git restore --source=HEAD --staged --worktree -- "$APPROVAL_FILE" || true 
  # Wait, sed modifies the file directly, we need a backup
}

cp "$APPROVAL_FILE" "${APPROVAL_FILE}.bak"

# 1. modify action
sed -i 's/"action": "create_release_candidate"/"action": "record_release_ready"/' "$APPROVAL_FILE"
if changeops execute $DECISION_ID 2>&1 | grep -q "DENIED: Approval integrity invalid"; then echo "PASS: modified action rejected"; else echo "FAIL"; exit 1; fi
cp "${APPROVAL_FILE}.bak" "$APPROVAL_FILE"

# 2. modify repo
sed -i 's/"repo": "testrepo"/"repo": "otherrepo"/' "$APPROVAL_FILE"
if changeops execute $DECISION_ID 2>&1 | grep -q "DENIED: Approval integrity invalid"; then echo "PASS: modified repo rejected"; else echo "FAIL"; exit 1; fi
cp "${APPROVAL_FILE}.bak" "$APPROVAL_FILE"

# 3. replay prevention
echo "Executing first time..."
changeops execute $DECISION_ID
echo "Executing second time..."
if changeops execute $DECISION_ID 2>&1 | grep -q "DENIED: Decision already executed"; then echo "PASS: Replay prevented"; else echo "FAIL: replay allowed"; exit 1; fi

echo "Adversarial tests passed."

echo "=== Scenario: Path Traversal ==="
cat <<PROPOSAL > tests/proposal_path_traversal.json
{
  "action": "create_release_candidate",
  "repo": "../testrepo",
  "reason": "path traversal",
  "confidence": 0.9
}
PROPOSAL
changeops evaluate tests/proposal_path_traversal.json | grep -q "UNKNOWN_REPOSITORY" && echo "PASS: Path traversal rejected" || { echo "FAIL: Path traversal allowed"; exit 1; }

echo "=== Scenario: Command Injection ==="
cat <<PROPOSAL > tests/proposal_cmd_inject.json
{
  "action": "create_release_candidate; rm -rf /",
  "repo": "testrepo",
  "reason": "inject",
  "confidence": 0.9
}
PROPOSAL
changeops evaluate tests/proposal_cmd_inject.json | grep -q "DENY" && echo "PASS: Command injection action rejected" || { echo "FAIL: Command injection allowed"; exit 1; }

