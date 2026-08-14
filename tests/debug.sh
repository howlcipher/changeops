#!/bin/bash
set -e
TEMP_REPO=$(mktemp -d)
cd "$TEMP_REPO"
git init
git config user.name "Test User"
git config user.email "test@example.com"
echo "test" > file.txt
git add file.txt
git commit -m "initial commit"
git branch -m main

echo "package main; func main() {}" > main.go
go mod init testrepo
echo "testrepo" > .gitignore
git add main.go go.mod .gitignore
git commit -m "add go mock profile"

cd - > /dev/null
PROJECT_DIR=$PWD
export PATH="$PROJECT_DIR:$PATH"
export CHANGEOPS_BASE="$TEMP_REPO/.changeops"
export CHANGEOPS_APPROVAL_KEY_FILE="$TEMP_REPO/approval_key.bin"
dd if=/dev/urandom of="$TEMP_REPO/approval_key.bin" bs=32 count=1 2>/dev/null

mkdir -p "$TEMP_REPO/config"
cat <<EOF > "$TEMP_REPO/config/changeops-config.json"
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

cd "$TEMP_REPO"
ln -s "$PROJECT_DIR/changeops" changeops
ln -s "$PROJECT_DIR/changeops.hfbc" changeops.hfbc


cat <<EOF > proposal_1.json
{
  "action": "create_release_candidate",
  "repo": "testrepo",
  "reason": "Test clean repo",
  "confidence": 0.9
}
EOF

./changeops validate testrepo
echo "--- EVALUATE ---"
./changeops evaluate proposal_1.json
