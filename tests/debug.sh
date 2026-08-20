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
git add main.go go.mod
git commit -m "add go mock profile"

PROJECT_DIR=/run/media/system/tallgeese/dev/howlchangeops
export HOWLCHANGEOPS_BASE="$TEMP_REPO/.howlchangeops"
export HOWLCHANGEOPS_APPROVAL_KEY_FILE="$TEMP_REPO/approval_key.bin"
dd if=/dev/urandom of="$HOWLCHANGEOPS_APPROVAL_KEY_FILE" bs=32 count=1 2>/dev/null
chmod 600 "$HOWLCHANGEOPS_APPROVAL_KEY_FILE"

mkdir -p "$TEMP_REPO/config"
cat <<EOF > "$TEMP_REPO/config/howlchangeops-config.json"
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
ln -s "$PROJECT_DIR/howlchangeops" howlchangeops
ln -s "$PROJECT_DIR/howlchangeops.hfbc" howlchangeops.hfbc
ln -s howlchangeops changeops
ln -s howlchangeops.hfbc changeops.hfbc

cat <<EOF > proposal_1.json
{
  "action": "create_release_candidate",
  "repo": "testrepo",
  "reason": "Test dirty repo",
  "confidence": 0.9
}
EOF

./howlchangeops validate testrepo
echo "=== evaluate ==="
./howlchangeops evaluate proposal_1.json
