# HowlChangeOps Rebranding & Ecosystem Harmonization Milestone

## Objective
Rebrand and migrate ChangeOps to **HowlChangeOps** across the Howl ecosystem, establishing canonical naming, repository URLs, CLI aliases, and documentation while maintaining full backward compatibility.

## Canonical Identity
- **Product Name:** HowlChangeOps
- **Repository Slug:** `howlchangeops`
- **Canonical URL:** `https://github.com/howlcipher/howlchangeops`
- **GitHub Pages:** `https://howlcipher.github.io/howlchangeops/`
- **Ecosystem Role:** The approval, execution-boundary, verification, and rollback component of the Howl ecosystem.

## Changes Implemented
1. **Source & Toolchain:**
   - Renamed policy source to `src/howlchangeops.howl` with compiled artifact `howlchangeops.hfbc`.
   - Symlinked legacy `src/changeops.howl` and `changeops.hfbc` for backward compatibility.
   - Built adapter binary `howlchangeops` and preserved `changeops` CLI alias.
   - Updated Go module to `module howlchangeops`.
2. **Environment & Configuration:**
   - Added primary support for `HOWLCHANGEOPS_BASE` and `HOWLCHANGEOPS_APPROVAL_KEY_FILE` with fallback to `CHANGEOPS_BASE` and `CHANGEOPS_APPROVAL_KEY_FILE`.
   - Added primary support for `config/howlchangeops-config.json` with fallback to `config/changeops-config.json`.
   - Updated evidence, approval, and execution receipt schemas to `howlchangeops.*/v1`.
   - Updated release candidate tag formatting to `howlchangeops/rc-<sha>`.
3. **Documentation & GitHub Pages:**
   - Rebranded landing page `docs/index.html` with updated titles, meta tags, OpenGraph/Twitter social cards, drawer navigation, and ecosystem links.
   - Updated `README.md`, threat models, reports, and social preview assets.
4. **Validation:**
   - Integration tests, adversarial tests, and authority bypass suites all executed and passed cleanly.
