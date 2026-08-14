import os

content = """package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type ConfigRepo struct {
	Path              string   `json:"path"`
	AllowedBranches   []string `json:"allowed_branches"`
	ValidationProfile string   `json:"validation_profile"`
	AllowedActions    []string `json:"allowed_actions"`
}

type Config struct {
	Repos map[string]ConfigRepo `json:"repos"`
}

type Proposal struct {
	Action     string  `json:"action"`
	Repo       string  `json:"repo"`
	Reason     string  `json:"reason"`
	Confidence float64 `json:"confidence"`
}

type ValidationResult struct {
	Name         string `json:"name"`
	Status       string `json:"status"`
	StartedAt    string `json:"started_at"`
	FinishedAt   string `json:"finished_at"`
	ExitCode     int    `json:"exit_code"`
	Profile      string `json:"profile"`
	Revision     string `json:"revision"`
	OutputDigest string `json:"output_digest"`
}

type RiskEvidence struct {
	ChangedFileCount          int  `json:"changed_file_count"`
	ContainsInfrastructure    bool `json:"contains_infrastructure_changes"`
	ContainsDependency        bool `json:"contains_dependency_changes"`
	ContainsCI                bool `json:"contains_ci_changes"`
	ContainsSecuritySensitive bool `json:"contains_security_sensitive_paths"`
}

type EvidenceEnvelope struct {
	Schema                   string                      `json:"schema"`
	Repo                     string                      `json:"repo"`
	Revision                 string                      `json:"revision"`
	Branch                   string                      `json:"branch"`
	WorkingTree              string                      `json:"working_tree"`
	ValidationProfile        string                      `json:"validation_profile"`
	ValidationProfileVersion string                      `json:"validation_profile_version"`
	ConfigDigest             string                      `json:"config_digest"`
	GeneratedAt              string                      `json:"generated_at"`
	Checks                   map[string]ValidationResult `json:"checks"`
	Risk                     RiskEvidence                `json:"risk"`
}

type RuntimeEvidence struct {
	CurrentRevision string `json:"current_revision"`
	WorkingTree     string `json:"working_tree"`
	Approved        string `json:"approved"`
	CandidateExists string `json:"candidate_exists"`
	EvidenceDigest  string `json:"evidence_digest"`
	EvidenceAge     string `json:"evidence_age"`
}

type Gate struct {
	Name   string `json:"name"`
	Status string `json:"status"`
}

type Decision struct {
	ID              string           `json:"decision_id"`
	Proposal        Proposal         `json:"proposal"`
	Evidence        EvidenceEnvelope `json:"evidence"`
	RuntimeEvidence RuntimeEvidence  `json:"runtime_evidence"`
	Gates           []Gate           `json:"gates"`
	Result          string           `json:"result"`
	Reason          string           `json:"reason"`
	Digest          string           `json:"digest"`
}

type Approval struct {
	Schema         string `json:"schema"`
	ApprovalID     string `json:"approval_id"`
	DecisionID     string `json:"decision_id"`
	DecisionDigest string `json:"decision_digest"`
	EvidenceDigest string `json:"evidence_digest"`
	Repo           string `json:"repo"`
	Action         string `json:"action"`
	Revision       string `json:"revision"`
	Approver       string `json:"approver"`
	IssuedAt       string `json:"issued_at"`
	ExpiresAt      string `json:"expires_at"`
	Nonce          string `json:"nonce"`
	Signature      string `json:"signature"`
}

type ExecutionReceipt struct {
	Schema       string `json:"schema"`
	DecisionID   string `json:"decision_id"`
	ApprovalID   string `json:"approval_id"`
	Action       string `json:"action"`
	Repo         string `json:"repo"`
	Revision     string `json:"revision"`
	ExecutedAt   string `json:"executed_at"`
	Verification string `json:"verification"`
}

var (
	baseDir      = ".changeops"
	decisionsDir = filepath.Join(baseDir, "decisions")
	approvalsDir = filepath.Join(baseDir, "approvals")
	receiptsDir  = filepath.Join(baseDir, "receipts")
	historyFile  = filepath.Join(baseDir, "history.jsonl")
)

func initDirs() {
	os.MkdirAll(decisionsDir, 0755)
	os.MkdirAll(approvalsDir, 0755)
	os.MkdirAll(receiptsDir, 0755)
}

func loadConfig() (*Config, string, error) {
	data, err := os.ReadFile("config/changeops-config.json")
	if err != nil {
		return nil, "", err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, "", err
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(data))
	return &cfg, digest, nil
}

func getApprovalKey() []byte {
	keyFile := os.Getenv("CHANGEOPS_APPROVAL_KEY_FILE")
	if keyFile == "" {
		return nil
	}
	key, err := os.ReadFile(keyFile)
	if err != nil {
		return nil
	}
	return key
}

func canonicalApprovalString(a Approval) string {
	return fmt.Sprintf("schema:%s|approval_id:%s|decision_id:%s|decision_digest:%s|evidence_digest:%s|repo:%s|action:%s|revision:%s|approver:%s|issued_at:%s|expires_at:%s|nonce:%s",
		a.Schema, a.ApprovalID, a.DecisionID, a.DecisionDigest, a.EvidenceDigest, a.Repo, a.Action, a.Revision, a.Approver, a.IssuedAt, a.ExpiresAt, a.Nonce)
}

func signApproval(a Approval, key []byte) string {
	payload := canonicalApprovalString(a)
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(payload))
	return fmt.Sprintf("%x", mac.Sum(nil))
}

func computeEvidenceDigest(e EvidenceEnvelope) string {
	data, _ := json.Marshal(e)
	return fmt.Sprintf("%x", sha256.Sum256(data))
}

func computeDecisionDigest(d Decision) string {
	payload := fmt.Sprintf("%s|%s|%s|%s|%s", d.Proposal.Action, d.Proposal.Repo, d.Evidence.Revision, d.Result, computeEvidenceDigest(d.Evidence))
	return fmt.Sprintf("%x", sha256.Sum256([]byte(payload)))
}

func gitCommand(repoPath string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = repoPath
	out, err := cmd.Output()
	return strings.TrimSpace(string(out)), err
}

func computeRisk(repoPath string, rev string) RiskEvidence {
	out, err := gitCommand(repoPath, "diff-tree", "--no-commit-id", "--name-only", "-r", rev)
	if err != nil {
		return RiskEvidence{}
	}
	files := strings.Split(out, "\\n")
	risk := RiskEvidence{
		ChangedFileCount: len(files),
	}
	for _, f := range files {
		if f == "" {
			continue
		}
		if strings.HasPrefix(f, "infra/") || strings.HasPrefix(f, "terraform/") || f == "Dockerfile" {
			risk.ContainsInfrastructure = true
		}
		if f == "go.mod" || f == "requirements.txt" || f == "package-lock.json" {
			risk.ContainsDependency = true
		}
		if strings.HasPrefix(f, ".github/workflows/") {
			risk.ContainsCI = true
		}
		if strings.Contains(f, "security") || strings.Contains(f, "auth") {
			risk.ContainsSecuritySensitive = true
		}
	}
	return risk
}

func gatherEvidence(repoID string, repoPath string, repoCfg ConfigRepo, configDigest string) (EvidenceEnvelope, RuntimeEvidence) {
	branch, _ := gitCommand(repoPath, "branch", "--show-current")
	rev, _ := gitCommand(repoPath, "rev-parse", "HEAD")
	status, _ := gitCommand(repoPath, "status", "--porcelain")
	workingTree := "dirty"
	if status == "" {
		workingTree = "clean"
	}

	ev := EvidenceEnvelope{
		Schema: "changeops.evidence/v1",
		Repo: repoID,
		Revision: rev,
		Branch: branch,
		WorkingTree: workingTree,
		ValidationProfile: repoCfg.ValidationProfile,
		ValidationProfileVersion: "1.0",
		ConfigDigest: configDigest,
		Checks: make(map[string]ValidationResult),
		Risk: computeRisk(repoPath, rev),
	}

	cacheKey := fmt.Sprintf("%x", sha256.Sum256([]byte(fmt.Sprintf("%s|%s|%s|%s", repoID, rev, repoCfg.ValidationProfile, configDigest))))
	cacheFile := filepath.Join(baseDir, fmt.Sprintf("evidence_%s.json", cacheKey))
	if cacheData, err := os.ReadFile(cacheFile); err == nil {
		var cachedEv EvidenceEnvelope
		if json.Unmarshal(cacheData, &cachedEv) == nil {
			if cachedEv.Revision == rev && cachedEv.ConfigDigest == configDigest && cachedEv.ValidationProfile == repoCfg.ValidationProfile {
				ev = cachedEv
				ev.WorkingTree = workingTree // Update working tree
			}
		}
	}

	candidateExists := "false"
	tags, _ := gitCommand(repoPath, "tag", "-l", fmt.Sprintf("changeops/rc-%s", rev[:7]))
	if tags != "" {
		candidateExists = "true"
	}

	rtEv := RuntimeEvidence{
		CurrentRevision: rev,
		WorkingTree: workingTree,
		CandidateExists: candidateExists,
		Approved: "false",
		EvidenceDigest: computeEvidenceDigest(ev),
	}
	if ev.GeneratedAt != "" {
		genTime, err := time.Parse(time.RFC3339, ev.GeneratedAt)
		if err == nil {
			rtEv.EvidenceAge = time.Since(genTime).Round(time.Second).String()
		}
	}

	return ev, rtEv
}

func runValidationCommand(name string, repoPath string, cmdName string, args ...string) ValidationResult {
	start := time.Now().UTC()
	cmd := exec.Command(cmdName, args...)
	cmd.Dir = repoPath
	out, err := cmd.CombinedOutput()
	
	status := "PASS"
	exitCode := 0
	if err != nil {
		status = "FAIL"
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.ExitCode()
		} else {
			exitCode = -1
		}
	}
	
	return ValidationResult{
		Name: name,
		Status: status,
		StartedAt: start.Format(time.RFC3339),
		FinishedAt: time.Now().UTC().Format(time.RFC3339),
		ExitCode: exitCode,
		Profile: "local",
		Revision: "HEAD",
		OutputDigest: fmt.Sprintf("%x", sha256.Sum256(out)),
	}
}

func validate(repoID string, repoPath string, repoCfg ConfigRepo, configDigest string) {
	ev, _ := gatherEvidence(repoID, repoPath, repoCfg, configDigest)
	ev.GeneratedAt = time.Now().UTC().Format(time.RFC3339)
	ev.Checks = make(map[string]ValidationResult)

	if repoCfg.ValidationProfile == "go" {
		fmt.Println("Running go test ./...")
		ev.Checks["test"] = runValidationCommand("go_test", repoPath, "go", "test", "./...")
		
		fmt.Println("Running go build ./...")
		ev.Checks["build"] = runValidationCommand("go_build", repoPath, "go", "build", "./...")
	} else {
		fmt.Printf("Unknown profile: %s\\n", repoCfg.ValidationProfile)
	}
	
	wtStatus := "FAIL"
	if ev.WorkingTree == "clean" {
		wtStatus = "PASS"
	}
	ev.Checks["working_tree"] = ValidationResult{
		Name: "working_tree",
		Status: wtStatus,
		StartedAt: time.Now().UTC().Format(time.RFC3339),
		FinishedAt: time.Now().UTC().Format(time.RFC3339),
		ExitCode: 0,
	}

	os.MkdirAll(baseDir, 0755)
	cacheKey := fmt.Sprintf("%x", sha256.Sum256([]byte(fmt.Sprintf("%s|%s|%s|%s", repoID, ev.Revision, repoCfg.ValidationProfile, configDigest))))
	cacheFile := filepath.Join(baseDir, fmt.Sprintf("evidence_%s.json", cacheKey))
	cacheData, _ := json.MarshalIndent(ev, "", "  ")
	os.WriteFile(cacheFile, cacheData, 0644)
	fmt.Printf("Validation complete. evidence_digest=%s\\n", computeEvidenceDigest(ev))
}

func invokeHowlFrame(proposalFile string, ev EvidenceEnvelope, rtEv RuntimeEvidence, repoCfg ConfigRepo) (map[string]interface{}, error) {
	args := []string{"run", "-allow-caps", "filesystem", "changeops.hfbc", proposalFile}
	args = append(args, fmt.Sprintf("repo=%s", ev.Repo))
	args = append(args, fmt.Sprintf("branch=%s", ev.Branch))
	args = append(args, fmt.Sprintf("revision=%s", ev.Revision))
	args = append(args, fmt.Sprintf("current_revision=%s", rtEv.CurrentRevision))
	args = append(args, fmt.Sprintf("working_tree=%s", rtEv.WorkingTree))
	
	testStatus := "UNKNOWN"
	if c, ok := ev.Checks["test"]; ok {
		testStatus = c.Status
	}
	buildStatus := "UNKNOWN"
	if c, ok := ev.Checks["build"]; ok {
		buildStatus = c.Status
	}
	
	args = append(args, fmt.Sprintf("tests=%s", testStatus))
	args = append(args, fmt.Sprintf("build=%s", buildStatus))
	args = append(args, fmt.Sprintf("approved=%s", rtEv.Approved))
	args = append(args, fmt.Sprintf("candidate_exists=%s", rtEv.CandidateExists))
	args = append(args, fmt.Sprintf("allowed_branches=%s", strings.Join(repoCfg.AllowedBranches, ",")))
	args = append(args, fmt.Sprintf("allowed_actions=%s", strings.Join(repoCfg.AllowedActions, ",")))
	
	// Risk parameters
	args = append(args, fmt.Sprintf("risk_infra=%t", ev.Risk.ContainsInfrastructure))
	args = append(args, fmt.Sprintf("risk_deps=%t", ev.Risk.ContainsDependency))
	args = append(args, fmt.Sprintf("risk_ci=%t", ev.Risk.ContainsCI))

	cmd := exec.Command("howlframe", args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("howlframe error: %v, out: %s", err, string(out))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(out, &result); err != nil {
		return nil, fmt.Errorf("howlframe output invalid JSON: %v (out: %s)", err, string(out))
	}
	return result, nil
}

func appendAudit(entry map[string]interface{}) {
	entry["timestamp"] = time.Now().UTC().Format(time.RFC3339)
	data, _ := json.Marshal(entry)
	f, _ := os.OpenFile(historyFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	defer f.Close()
	f.Write(data)
	f.WriteString("\\n")
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: changeops <command> [args...]")
		os.Exit(1)
	}

	initDirs()
	cfg, configDigest, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\\n", err)
		os.Exit(1)
	}

	cmd := os.Args[1]

	switch cmd {
	case "inspect":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops inspect <repo_id>")
			os.Exit(1)
		}
		repoID := os.Args[2]
		repoCfg, ok := cfg.Repos[repoID]
		if !ok {
			fmt.Printf("UNKNOWN_REPOSITORY: %s\\n", repoID)
			os.Exit(1)
		}
		ev, rtEv := gatherEvidence(repoID, repoCfg.Path, repoCfg, configDigest)
		fmt.Println("Evidence Envelope:")
		evData, _ := json.MarshalIndent(ev, "", "  ")
		fmt.Println(string(evData))
		fmt.Println("\\nRuntime Evidence:")
		rtData, _ := json.MarshalIndent(rtEv, "", "  ")
		fmt.Println(string(rtData))

	case "validate":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops validate <repo_id>")
			os.Exit(1)
		}
		repoID := os.Args[2]
		repoCfg, ok := cfg.Repos[repoID]
		if !ok {
			fmt.Printf("UNKNOWN_REPOSITORY: %s\\n", repoID)
			os.Exit(1)
		}
		validate(repoID, repoCfg.Path, repoCfg, configDigest)

	case "plan":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops plan <repo_id>")
			os.Exit(1)
		}
		repoID := os.Args[2]
		repoCfg, ok := cfg.Repos[repoID]
		if !ok {
			fmt.Printf("UNKNOWN_REPOSITORY: %s\\n", repoID)
			os.Exit(1)
		}
		ev, rtEv := gatherEvidence(repoID, repoCfg.Path, repoCfg, configDigest)
		
		actions := []string{
			"create_release_candidate",
			"record_release_ready",
			"rollback_release_candidate",
			"promote_staging",
			"promote_production",
		}
		
		tmpProp := filepath.Join(baseDir, "tmp_plan.json")
		defer os.Remove(tmpProp)
		
		fmt.Printf("Plan for repository: %s (revision: %s)\\n", repoID, ev.Revision[:7])
		fmt.Printf("Evidence Identity: %s\\n", rtEv.EvidenceDigest[:16])
		if rtEv.EvidenceAge != "" {
			fmt.Printf("Evidence Age: %s\\n", rtEv.EvidenceAge)
		}
		fmt.Println()
		
		for _, act := range actions {
			prop := Proposal{Action: act, Repo: repoID, Reason: "plan simulation"}
			propData, _ := json.Marshal(prop)
			os.WriteFile(tmpProp, propData, 0644)
			
			res, err := invokeHowlFrame(tmpProp, ev, rtEv, repoCfg)
			if err != nil {
				fmt.Printf("%-30s ERROR — %v\\n", act, err)
				continue
			}
			decision := res["decision"].(string)
			reason := res["reason"].(string)
			if decision == "ALLOW" || decision == "REQUIRE_APPROVAL" {
				fmt.Printf("%-30s %s\\n", act, decision)
			} else {
				fmt.Printf("%-30s %s — %s\\n", act, decision, reason)
			}
		}

	case "evaluate":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops evaluate <proposal.json>")
			os.Exit(1)
		}
		proposalFile := os.Args[2]
		propData, err := os.ReadFile(proposalFile)
		if err != nil {
			fmt.Printf("Error reading proposal: %v\\n", err)
			os.Exit(1)
		}
		var prop Proposal
		if err := json.Unmarshal(propData, &prop); err != nil {
			fmt.Printf("Error parsing proposal: %v\\n", err)
			os.Exit(1)
		}

		repoCfg, ok := cfg.Repos[prop.Repo]
		if !ok {
			fmt.Printf("UNKNOWN_REPOSITORY: %s\\n", prop.Repo)
			os.Exit(1)
		}

		ev, rtEv := gatherEvidence(prop.Repo, repoCfg.Path, repoCfg, configDigest)
		res, err := invokeHowlFrame(proposalFile, ev, rtEv, repoCfg)
		if err != nil {
			fmt.Printf("Evaluation error: %v\\n", err)
			os.Exit(1)
		}

		decisionID := fmt.Sprintf("decision-%x", sha256.Sum256([]byte(fmt.Sprintf("%s-%s-%d", prop.Action, ev.Revision, time.Now().UnixNano()))))[:16]

		var gates []Gate
		if g, ok := res["gates"].([]interface{}); ok {
			for _, item := range g {
				if m, ok := item.(map[string]interface{}); ok {
					gates = append(gates, Gate{
						Name:   m["name"].(string),
						Status: m["status"].(string),
					})
				}
			}
		}

		dec := Decision{
			ID:              decisionID,
			Proposal:        prop,
			Evidence:        ev,
			RuntimeEvidence: rtEv,
			Gates:           gates,
			Result:          res["decision"].(string),
			Reason:          res["reason"].(string),
		}
		dec.Digest = computeDecisionDigest(dec)

		fmt.Printf("Decision: %s\\nReason: %s\\n", dec.Result, dec.Reason)

		if dec.Result == "REQUIRE_APPROVAL" {
			decData, _ := json.MarshalIndent(dec, "", "  ")
			os.WriteFile(filepath.Join(decisionsDir, dec.ID+".json"), decData, 0644)
			fmt.Printf("Decision saved as %s. Use 'changeops approve %s' to approve.\\n", dec.ID, dec.ID)
		}

		appendAudit(map[string]interface{}{
			"event":    "evaluate",
			"decision": dec,
		})

	case "approve":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops approve <decision_id>")
			os.Exit(1)
		}
		decID := os.Args[2]
		decFile := filepath.Join(decisionsDir, decID+".json")
		decData, err := os.ReadFile(decFile)
		if err != nil {
			fmt.Printf("Decision not found: %v\\n", err)
			os.Exit(1)
		}
		var dec Decision
		json.Unmarshal(decData, &dec)
		if dec.Digest != computeDecisionDigest(dec) {
			fmt.Println("Decision modified")
			os.Exit(1)
		}
		
		key := getApprovalKey()
		if key == nil {
			fmt.Println("DENIED: CHANGEOPS_APPROVAL_KEY_FILE not set or invalid")
			os.Exit(1)
		}

		now := time.Now().UTC()
		app := Approval{
			Schema:         "changeops.approval/v1",
			ApprovalID     fmt.Sprintf("app-%x", sha256.Sum256([]byte(fmt.Sprintf("%s-%d", dec.ID, now.UnixNano()))))[:16],
			DecisionID:     dec.ID,
			DecisionDigest: dec.Digest,
			EvidenceDigest: dec.RuntimeEvidence.EvidenceDigest,
			Repo:           dec.Proposal.Repo,
			Action:         dec.Proposal.Action,
			Revision:       dec.Evidence.Revision,
			Approver:       "admin", // TODO: read from authenticated context
			IssuedAt:       now.Format(time.RFC3339),
			ExpiresAt:      now.Add(30 * time.Minute).Format(time.RFC3339),
			Nonce:          fmt.Sprintf("%d", now.UnixNano()),
		}
		app.Signature = signApproval(app, key)
		
		appData, _ := json.MarshalIndent(app, "", "  ")
		appFile := filepath.Join(approvalsDir, dec.ID+".json")
		os.WriteFile(appFile, appData, 0644)
		
		fmt.Printf("Decision %s approved.\\n", decID)
		appendAudit(map[string]interface{}{
			"event":       "approve",
			"decision_id": decID,
			"approval_id": app.ApprovalID,
		})

	case "execute":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops execute <decision_id>")
			os.Exit(1)
		}
		decID := os.Args[2]
		decFile := filepath.Join(decisionsDir, decID+".json")
		decData, err := os.ReadFile(decFile)
		if err != nil {
			fmt.Printf("Decision not found: %v\\n", err)
			os.Exit(1)
		}
		var dec Decision
		json.Unmarshal(decData, &dec)
		if dec.Digest != computeDecisionDigest(dec) {
			fmt.Println("DENIED: Decision modified")
			os.Exit(1)
		}
		
		// Replay protection
		if _, err := os.Stat(filepath.Join(receiptsDir, dec.ID+".json")); err == nil {
			fmt.Println("DENIED: Decision already executed")
			os.Exit(1)
		}

		repoCfg, ok := cfg.Repos[dec.Proposal.Repo]
		if !ok {
			fmt.Printf("UNKNOWN_REPOSITORY: %s\\n", dec.Proposal.Repo)
			os.Exit(1)
		}

		// Gather current evidence to check for staleness
		ev, rtEv := gatherEvidence(dec.Proposal.Repo, repoCfg.Path, repoCfg, configDigest)
		
		// If cache was missed, ev would have a new GeneratedAt which makes it a different EvidenceEnvelope, but the content checks should match what was in the decision if it's the exact same revision.
		// However, HowlFrame will just re-evaluate.
		
		key := getApprovalKey()
		if key == nil {
			fmt.Println("DENIED: CHANGEOPS_APPROVAL_KEY_FILE not set")
			os.Exit(1)
		}

		// Check for valid approval
		appFile := filepath.Join(approvalsDir, decID+".json")
		if appData, err := os.ReadFile(appFile); err == nil {
			var app Approval
			json.Unmarshal(appData, &app)
			if app.Signature == signApproval(app, key) && app.DecisionDigest == dec.Digest {
				exp, _ := time.Parse(time.RFC3339, app.ExpiresAt)
				if time.Now().UTC().Before(exp) {
					rtEv.Approved = "true"
				} else {
					fmt.Println("DENIED: Approval expired")
					os.Exit(1)
				}
			} else {
				fmt.Println("DENIED: Approval integrity invalid")
				os.Exit(1)
			}
		}

		// Write proposal back to a temp file for HowlFrame
		tmpProp := filepath.Join(baseDir, "tmp_proposal.json")
		propData, _ := json.Marshal(dec.Proposal)
		os.WriteFile(tmpProp, propData, 0644)
		defer os.Remove(tmpProp)

		res, err := invokeHowlFrame(tmpProp, ev, rtEv, repoCfg)
		if err != nil {
			fmt.Printf("Execution evaluation error: %v\\n", err)
			os.Exit(1)
		}

		if res["decision"].(string) != "ALLOW" {
			fmt.Printf("Execution DENIED: %s. Reason: %s\\n", res["decision"], res["reason"])
			if strings.Contains(res["reason"].(string), "STALE_EVIDENCE") {
				fmt.Println("STALE_EVIDENCE")
			}
			os.Exit(1)
		}

		// Perform bounded action
		fmt.Printf("Executing action: %s\\n", dec.Proposal.Action)
		success := false
		if dec.Proposal.Action == "create_release_candidate" {
			tag := fmt.Sprintf("changeops/rc-%s", rtEv.CurrentRevision[:7])
			out, err := gitCommand(repoCfg.Path, "tag", "-a", tag, "-m", "ChangeOps RC", rtEv.CurrentRevision)
			if err != nil {
				fmt.Printf("Failed to create RC tag: %v\\n%s\\n", err, out)
			} else {
				fmt.Printf("Created tag: %s\\n", tag)
				verify, _ := gitCommand(repoCfg.Path, "tag", "-l", tag)
				if verify != "" {
					fmt.Println("Verified: tag created successfully.")
					success = true
				} else {
					fmt.Println("Verification failed: tag not found.")
				}
			}
		} else if dec.Proposal.Action == "record_release_ready" {
			fmt.Println("Recorded release ready.")
			success = true
		} else if dec.Proposal.Action == "rollback_release_candidate" {
			tag := fmt.Sprintf("changeops/rc-%s", rtEv.CurrentRevision[:7])
			out, err := gitCommand(repoCfg.Path, "tag", "-d", tag)
			if err != nil {
				fmt.Printf("Failed to rollback RC tag: %v\\n%s\\n", err, out)
			} else {
				fmt.Printf("Rolled back tag: %s\\n", tag)
				tags, _ := gitCommand(repoCfg.Path, "tag", "-l", tag)
				if tags == "" {
					fmt.Println("Verified: tag removed.")
					success = true
				} else {
					fmt.Println("Verification failed: tag still exists.")
				}
			}
		} else {
			fmt.Printf("ACTION_NOT_ALLOWED: %s\\n", dec.Proposal.Action)
		}

		if success {
			// Create receipt
			appFile := filepath.Join(approvalsDir, decID+".json")
			var app Approval
			if appData, err := os.ReadFile(appFile); err == nil {
				json.Unmarshal(appData, &app)
			}
			receipt := ExecutionReceipt{
				Schema:       "changeops.execution_receipt/v1",
				DecisionID:   dec.ID,
				ApprovalID:   app.ApprovalID,
				Action:       dec.Proposal.Action,
				Repo:         dec.Proposal.Repo,
				Revision:     rtEv.CurrentRevision,
				ExecutedAt:   time.Now().UTC().Format(time.RFC3339),
				Verification: "PASS",
			}
			recData, _ := json.MarshalIndent(receipt, "", "  ")
			os.WriteFile(filepath.Join(receiptsDir, dec.ID+".json"), recData, 0644)
			
			// We DO NOT remove the decision file to preserve audit history!
			// We DO NOT remove the approval file to preserve audit history!
		}

		appendAudit(map[string]interface{}{
			"event":       "execute",
			"decision_id": decID,
			"action":      dec.Proposal.Action,
			"success":     success,
		})

	case "history":
		data, err := os.ReadFile(historyFile)
		if err != nil {
			fmt.Println("No history found.")
			return
		}
		fmt.Println(string(data))

	case "explain":
		if len(os.Args) < 3 {
			fmt.Println("Usage: changeops explain <decision_id>")
			os.Exit(1)
		}
		decID := os.Args[2]
		decFile := filepath.Join(decisionsDir, decID+".json")
		decData, err := os.ReadFile(decFile)
		if err != nil {
			fmt.Printf("Decision not found: %v\\n", err)
			os.Exit(1)
		}
		var dec Decision
		json.Unmarshal(decData, &dec)

		fmt.Printf("Decision: %s\\nAction: %s\\nRepo: %s\\nRevision: %s\\n\\nGates:\\n", dec.Result, dec.Proposal.Action, dec.Proposal.Repo, dec.Evidence.Revision)
		for _, g := range dec.Gates {
			fmt.Printf("  - %s: %s\\n", g.Name, g.Status)
		}
		fmt.Printf("\\nReason: %s\\n", dec.Reason)

	default:
		fmt.Printf("Unknown command: %s\\n", cmd)
		os.Exit(1)
	}
}
"""

with open("build_main.py", "w") as f:
    f.write('with open("adapter/main.go", "w") as f:\n')
    f.write('    f.write("""' + content + '""")\n')
