# Phase 5: Cleanup, Consolidation & Repository Alignment

**Status**: DRAFT
**Branch**: `core-rebuild`
**Goal**: Bring repository into full alignment with HACS/HA standards while completing refactoring cleanup

---

## Current State Analysis

### ✅ Already Compliant
- **Core refactoring complete** (Phases 1-4 done)
- `pyproject.toml` with consolidated tooling
- `uv.lock` committed
- `LICENSE`, `README.md`, `CLAUDE.md` present
- `hacs.json` exists
- `custom_components/magic_areas/` structure present
- Test coverage: 95% (235 tests passing)

### ❌ Non-Compliant (AGENTS.md violations)

**Legacy Files to Remove:**
```
requirements.txt (empty but should not exist)
requirements-test.txt (duplicates pyproject.toml)
requirements-docs.txt (duplicates pyproject.toml)
setup.cfg (moved to pyproject.toml)
tox.ini (replaced by pytest + uv)
pylintrc (moved to pyproject.toml)
.ruff.toml (should be in pyproject.toml)
```

**Root-Level Artifacts:**
```
base/ (outdated entities.py - 193 lines vs current 349 lines)
config/ (HA dev config for obsolete scripts/)
scripts/ (all tox-based - obsolete with uv)
info.md (10-line file, possible duplicate/outdated)
```

**Incomplete HACS Metadata:**
```json
// hacs.json - Missing required fields
{
  "name": "Magic Areas",
  "homeassistant": "2026.1.0",
  "render_readme": true
  // MISSING: "domain": "magic_areas"
}
```

### 🔄 Internal Structure Improvements Needed

**Constants Organization:**
Current state (GOOD - intentionally de-consolidated):
- `core_constants.py` (12 lines) → Rename to `const.py` for HA convention
- `config_keys.py` (148 lines) - Config keys ✅ Keep
- `defaults.py` (87 lines) - Default values ✅ Keep
- `enums.py` (91 lines) - Type-safe enums ✅ Keep
- `area_constants.py` (27 lines) - Area constants ✅ Keep
- `features.py`, `policy.py`, etc. ✅ Keep

Action needed: Simple rename `core_constants.py` → `const.py` (no consolidation)

**Platform Organization:**
Current: Individual platform directories (`binary_sensor/`, `sensor/`, `switch/`, etc.)
Suggestion: Consider `platforms/` subdirectory for clarity (optional - not required by HA)

---

## Phase 5 Breakdown

### Sprint 1: Remove Legacy Files & Artifacts (0.5 day)

**Goal**: Remove all legacy packaging, tooling, and obsolete development artifacts

**Actions:**

#### 1.1: Delete Legacy Packaging Files
```bash
rm requirements.txt requirements-test.txt requirements-docs.txt
rm setup.cfg tox.ini pylintrc
```

#### 1.2: Merge .ruff.toml into pyproject.toml
```bash
# Read current .ruff.toml settings
cat .ruff.toml

# Merge into pyproject.toml [tool.ruff] section
# Verify no conflicts with existing config
# Delete .ruff.toml after merge
rm .ruff.toml
```

#### 1.3: Delete Obsolete Directories
```bash
# All scripts use tox (which we're removing)
rm -rf scripts/
# scripts/develop - Uses config/ for HA dev server (tox-based)
# scripts/lint - Runs tox -e lint
# scripts/test - Runs tox -e ha-stable/ha-beta
# scripts/setup - Obsolete setup

# HA dev config used only by scripts/develop
rm -rf config/

# Outdated version (193 lines vs current 349 lines in custom_components/)
rm -rf base/
```

#### 1.4: Review Root Files
```bash
# 10-line file, review if duplicate/outdated
cat info.md
# Decision: Delete if redundant with README.md

# Security linting config - review if still needed with ruff
cat bandit.yaml
# Decision: Keep if actively used, or merge into pyproject.toml
```

#### 1.5: Organize Planning Documentation (Optional)
Consider moving planning docs to `docs/contributing/`:
```bash
# Create contributing docs directory
mkdir -p docs/contributing

# Move planning docs (optional)
mv "design philosophy.md" docs/contributing/design-philosophy.md
mv implementation-plan.md docs/contributing/implementation-plan.md
mv REFACTOR.md docs/contributing/refactoring-guide.md

# Keep PHASE-5-PLAN.md at root (active planning)
```

#### 1.6: Create Development Guide (Replace scripts/)
Create `docs/contributing/development.md` with uv-based commands:
```markdown
# Development Guide

## Setup
\`\`\`bash
# Clone and setup
git clone <repo>
cd magic-areas
uv sync
\`\`\`

## Running Tests
\`\`\`bash
# Full test suite
uv run pytest tests/ --cov=custom_components.magic_areas

# Specific test file
uv run pytest tests/config_flow/test_config_flow_basic.py -v
\`\`\`

## Linting & Type Checking
\`\`\`bash
# Linting
uv run ruff check custom_components/magic_areas/

# Formatting
uv run ruff format custom_components/magic_areas/

# Type checking
uv run mypy custom_components/magic_areas/
\`\`\`

## Local Development with Home Assistant
See [Home Assistant development docs](https://developers.home-assistant.io/docs/development_environment)
\`\`\`
```

#### 1.7: Review Dotfiles (Optional)
- `.devcontainer.json` - Keep if actively used
- `.vscode/` - Keep if actively used
- `.pre-commit-config.yaml` - Ensure hooks reference pyproject.toml tools

**Testing:**
```bash
# Verify uv can install without legacy files
uv sync

# Verify all tools work from pyproject.toml
uv run pytest tests/
uv run mypy custom_components/magic_areas/
uv run ruff check custom_components/magic_areas/
```

**Acceptance:**
- ✅ All legacy packaging files removed
- ✅ Obsolete directories removed (scripts/, config/, base/)
- ✅ .ruff.toml merged into pyproject.toml
- ✅ info.md reviewed and removed if redundant
- ✅ bandit.yaml decision made (keep or merge)
- ✅ Planning docs organized (optional)
- ✅ Development guide created in docs/contributing/
- ✅ No references to deleted files in CI/docs
- ✅ Tests pass: `uv run pytest tests/`
- ✅ Linting passes: `uv run ruff check custom_components/magic_areas/`

---

### Sprint 2: Repository Structure Alignment (1 day)

**Goal**: Align repository with AGENTS.md target structure

#### 2.1: Fix hacs.json

Add missing required fields:
```json
{
  "name": "Magic Areas",
  "domain": "magic_areas",
  "homeassistant": "2026.1.0",
  "render_readme": true
}
```

#### 2.2: Constants Organization (Minimal Change)

**Current State (GOOD - Keep the focused split):**

We intentionally de-consolidated constants from the fork baseline. Current focused modules:
- `core_constants.py` (12 lines) - Core integration constants
- `config_keys.py` (148 lines) - All config keys and defaults
- `defaults.py` (87 lines) - Default policy values
- `enums.py` (91 lines) - Type-safe enumerations
- `area_constants.py` (27 lines) - Area-specific constants
- `features.py` - Feature identifiers
- `feature_info.py` - Feature metadata
- `policy.py` - Feature policies
- `ha_domains.py` - HA domain constants

**Action: Simple Rename Only**

Rename `core_constants.py` → `const.py` (HA naming convention):
```python
# custom_components/magic_areas/const.py (renamed from core_constants.py)
"""Primary integration constants for Magic Areas.

Other constants are organized in focused modules:
- config_keys.py - Configuration keys and defaults
- defaults.py - Feature default values
- enums.py - Type-safe enumerations
- area_constants.py - Area-specific constants
- features.py - Feature identifiers
- policy.py - Feature availability policies
"""

DOMAIN = "magic_areas"
EVENT_MAGICAREAS_AREA_STATE_CHANGED = "magicareas_area_state_changed"
# ... rest of file unchanged
```

**Updates needed:**
```python
# Update imports across codebase (simple find/replace)
# OLD: from custom_components.magic_areas.core_constants import DOMAIN
# NEW: from custom_components.magic_areas.const import DOMAIN
```

**Rationale**: Official HA integrations expect `const.py` for the DOMAIN constant, but they
don't require all constants in one file. Our focused split is good architecture - keep it.

#### 2.3: Internal Directory Review

Current structure is acceptable:
```
custom_components/magic_areas/
├── __init__.py           ✅ Setup/unload
├── const.py              ⬅️ NEW (consolidates core_constants.py)
├── manifest.json         ✅
├── config_flow.py        ✅
├── coordinator.py        ✅
├── diagnostics.py        ✅
├── models.py             ✅
├── base/                 ✅ Base entity classes
├── binary_sensor/        ✅ Platform
├── config_flows/         ✅ Config flow helpers (custom - good pattern)
├── core/                 ✅ Domain logic (custom - good pattern)
├── helpers/              ✅ Utility functions
├── media_player/         ✅ Platform
├── schemas/              ✅ Config schemas (custom - good pattern)
├── sensor/               ✅ Platform
├── switch/               ✅ Platform
└── translations/         ✅ i18n
```

**Note**: AGENTS.md suggests `platforms/` but individual platform dirs (`sensor/`, `switch/`) is
also standard HA pattern. No change needed unless you prefer consolidation.

#### 2.4: Documentation Organization

Consolidate all documentation in root `docs/` (no need for custom_components/magic_areas/docs/):

```
docs/
├── source/              ✅ KEEP (legacy user docs - address later)
├── migration/           ✅ KEEP (fork migration notes - technical)
│   ├── README.md
│   ├── architecture.md
│   ├── coordinator.md
│   ├── config-flow.md
│   └── tests.md
└── contributing/        ⬅️ NEW (consolidate all contributor docs)
    ├── development.md   (setup, testing, linting - replaces scripts/)
    ├── architecture.md  (high-level design overview)
    ├── testing.md       (test patterns and guidelines)
    ├── adding-features.md (how to add new features)
    ├── design-philosophy.md (moved from root)
    ├── implementation-plan.md (moved from root)
    └── refactoring-guide.md (moved from root)
```

**Rationale:**
- Root `docs/` is explicitly allowed by AGENTS.md for documentation
- Simpler structure - all contributor docs in one place
- `docs/migration/` stays (technical fork migration notes)
- No need for internal `custom_components/magic_areas/docs/`

**Acceptance:**
- ✅ hacs.json has all required fields (domain, name, homeassistant, render_readme)
- ✅ `const.py` renamed from core_constants.py (focused split maintained)
- ✅ Documentation organized in `docs/contributing/`
- ✅ Development guide created (replaces scripts/)
- ✅ All imports updated (core_constants → const)
- ✅ Tests pass after rename

---

### Sprint 3: Remove Dead Code & Unused Helpers (0.5 day)

**Goal**: Clean up code that's no longer needed after Phases 1-4

#### 3.1: Identify Dead Code

Run analysis:
```bash
# Find unused imports
uv run ruff check --select F401 custom_components/magic_areas/

# Find unused functions (manual review)
grep -r "^def " custom_components/magic_areas/ | while read -r line; do
  func=$(echo "$line" | sed 's/.*def \([^(]*\).*/\1/')
  count=$(grep -r "$func" custom_components/magic_areas/ | wc -l)
  if [ "$count" -eq 1 ]; then
    echo "Potentially unused: $line"
  fi
done
```

#### 3.2: Known Cleanup Targets

Based on previous refactoring:

1. **Dead functions in `core/meta.py`** (from implementation-plan.md):
   - `build_meta_presence_sensors()` at lines 38-44 (already removed per plan?)
   - Verify removal, check for other dead code

2. **Duplicate entity filtering logic**:
   - Check if any old filtering patterns remain in platforms
   - All should use coordinator snapshot

3. **Unused constants**:
   - After consolidation, check for unused constants in old files

4. **Legacy attributes module**:
   - `attrs.py` - Review if still needed after core extraction

#### 3.3: Deprecated Helpers Review

Check `helpers/` directory:
- `helpers/area.py` - Still used?
- `helpers/timer.py` - Still used?
- `util.py` (root level) - Still used?

**Acceptance:**
- No unused imports (ruff clean)
- No dead functions
- No duplicate logic
- Coverage remains 95%+

---

### Sprint 4: Documentation Updates (0.5 day)

**Goal**: Update all documentation to reflect new structure

#### 4.1: Update CLAUDE.md

Add Phase 5 completion:
```markdown
## Project Status

- **Branch**: `core-rebuild`
- **Phase 1**: ✅ Complete - Boundary alignment
- **Phase 2**: ✅ Complete - Core domain logic extraction
- **Phase 3**: ✅ Complete - Platform adapter simplification
- **Phase 4**: ✅ Complete - Config flow modularization
- **Phase 5**: ✅ Complete - Repository alignment & cleanup
- **Overall Coverage**: 95%+ (235+ tests passing)

## Repository Structure

Now fully aligned with HACS/HA standards:
- Legacy files removed
- Constants consolidated
- Documentation organized
- HACS metadata complete
```

#### 4.2: Update README.md

Sections to review/update:
- Installation instructions (ensure HACS-focused)
- Development setup (reference uv, not requirements.txt)
- Contributing section (reference CONTRIBUTING.md)
- Badge links (build status, coverage, etc.)

#### 4.3: Update CONTRIBUTING.md

Ensure it references:
- `uv sync` for setup (not pip)
- `pyproject.toml` for tooling
- Test commands using uv
- No references to tox/setup.py

#### 4.4: Create Developer Docs

In `docs/contributing/` (created in Sprint 1):
- `development.md` - Setup, testing, linting (replaces scripts/)
- `architecture.md` - Coordinator → core → platforms flow
- `testing.md` - Test patterns and guidelines
- `adding-features.md` - How to add new features

#### 4.5: Update Migration Docs

In `docs/migration/`:
- Add Phase 4 & 5 to migration notes
- Document config flow modularization
- Document repository restructuring

**Acceptance:**
- All docs reference current structure
- No references to removed files
- Developer docs exist for key patterns

---

### Sprint 5: Quality Scale & Final Checks (0.5 day)

**Goal**: Verify Bronze tier compliance and prepare for merge

#### 5.1: Home Assistant Quality Scale Check

Verify Bronze tier requirements:
```markdown
✅ Config flow with tests
✅ Unique IDs for all entities
✅ DataUpdateCoordinator pattern
✅ Async-only (no blocking I/O)
✅ Proper availability semantics
✅ Type hints throughout
✅ Test coverage (95%+)
```

#### 5.2: HACS Validation

```bash
# Validate hacs.json
uv run python -c "import json; json.load(open('hacs.json'))"

# Check manifest.json
uv run python -c "import json; json.load(open('custom_components/magic_areas/manifest.json'))"

# Verify domain match
grep '"domain"' hacs.json custom_components/magic_areas/manifest.json
```

#### 5.3: CI/CD Check

Ensure `.github/workflows/` references:
- `uv sync` (not pip install)
- `uv run pytest` (not tox)
- `uv run mypy` (not direct mypy)
- `uv run ruff` (not flake8/black/isort)

#### 5.4: Final Test Suite Run

```bash
# Full test suite with coverage
uv run pytest tests/ --cov=custom_components.magic_areas --cov-report=term-missing

# Type checking
uv run mypy custom_components/magic_areas

# Linting
uv run ruff check custom_components/magic_areas

# Formatting check
uv run ruff format --check custom_components/magic_areas
```

#### 5.5: Import Path Verification

Verify no imports broken by restructuring:
```bash
# Test that integration loads
uv run python -c "import custom_components.magic_areas"

# Test key imports
uv run python -c "from custom_components.magic_areas.const import DOMAIN"
uv run python -c "from custom_components.magic_areas.core.aggregates import select_aggregate_sensor"
```

**Acceptance:**
- All quality checks pass
- HACS validation passes
- CI configuration updated
- No broken imports
- Tests: 95%+ coverage, all passing

---

## Phase 5 Summary

### Total Effort: ~3 days

### Key Deliverables:
1. ✅ Legacy files removed (requirements.txt, setup.cfg, etc.)
2. ✅ Repository structure aligned with AGENTS.md
3. ✅ hacs.json complete and valid
4. ✅ Constants organized (renamed core_constants.py → const.py, kept focused split)
5. ✅ Dead code removed
6. ✅ Documentation updated and organized
7. ✅ Quality scale verified (Bronze tier)
8. ✅ Ready for HACS distribution

### Files Created:
- `docs/contributing/development.md` (replaces scripts/)
- `docs/contributing/architecture.md`
- `docs/contributing/testing.md`
- `docs/contributing/adding-features.md`

### Files Renamed:
- `core_constants.py` → `const.py` (HA naming convention)
- `design philosophy.md` → `docs/contributing/design-philosophy.md`
- `implementation-plan.md` → `docs/contributing/implementation-plan.md`
- `REFACTOR.md` → `docs/contributing/refactoring-guide.md`

### Files Modified:
- `hacs.json` (add domain field)
- `pyproject.toml` (merge .ruff.toml)
- `CLAUDE.md` (add Phase 5 completion)
- `README.md` (update dev setup)
- `CONTRIBUTING.md` (reference uv)
- `.github/workflows/*.yml` (update CI commands)

### Files Removed:
- `requirements.txt` (empty, duplicates pyproject.toml)
- `requirements-test.txt` (duplicates pyproject.toml)
- `requirements-docs.txt` (duplicates pyproject.toml)
- `setup.cfg` (moved to pyproject.toml)
- `tox.ini` (replaced by uv + pytest)
- `pylintrc` (moved to pyproject.toml)
- `.ruff.toml` (merged into pyproject.toml)
- `scripts/` directory (all tox-based, obsolete)
  - scripts/develop
  - scripts/lint
  - scripts/test
  - scripts/setup
- `base/` directory (outdated entities.py - 193 vs 349 lines)
- `config/` directory (HA dev config for obsolete scripts)
- `info.md` (if redundant with README.md)

### Post-Phase 5 State

```
magic-areas/
├── .github/              (CI/CD workflows)
├── assets/               (badges, images)
├── custom_components/
│   └── magic_areas/
│       ├── __init__.py
│       ├── manifest.json
│       ├── const.py      ⬅️ RENAMED (from core_constants.py)
│       ├── config_keys.py (focused constants - kept)
│       ├── defaults.py   (focused constants - kept)
│       ├── enums.py      (focused constants - kept)
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── diagnostics.py
│       ├── models.py
│       ├── base/         (entity base classes)
│       ├── binary_sensor/
│       ├── config_flows/ (config flow helpers)
│       ├── core/         (domain logic)
│       ├── helpers/
│       ├── media_player/
│       ├── schemas/      (config schemas)
│       ├── sensor/
│       ├── switch/
│       └── translations/
├── docs/
│   ├── source/           (legacy user docs)
│   ├── migration/        (fork migration technical docs)
│   └── contributing/     ⬅️ NEW (all contributor docs)
│       ├── development.md
│       ├── architecture.md
│       ├── testing.md
│       ├── adding-features.md
│       ├── design-philosophy.md (moved from root)
│       ├── implementation-plan.md (moved from root)
│       └── refactoring-guide.md (moved from root)
├── tests/
│   ├── config_flow/
│   ├── integration/
│   ├── platforms/
│   └── unit/
├── pyproject.toml        (consolidated tooling)
├── uv.lock
├── hacs.json             (complete metadata)
├── LICENSE
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── CONTRIBUTING.md
└── CODE_OF_CONDUCT.md
```

---

## Risk Assessment

### Low Risk:
- Removing legacy files (not used by runtime)
- Adding hacs.json fields
- Documentation updates

### Medium Risk:
- Constants consolidation (requires updating imports)
- Moving root artifacts (check for references)

### Mitigation:
- Run full test suite after each sprint
- Use git to track all moves/renames
- Test integration load in HA dev environment

---

## Success Criteria

✅ All legacy packaging files removed
✅ Repository matches AGENTS.md structure
✅ HACS validation passes
✅ All 235+ tests pass
✅ Coverage remains 95%+
✅ MyPy clean
✅ Ruff clean
✅ Documentation complete and accurate
✅ No broken imports
✅ CI/CD updated and passing
✅ Ready for HACS distribution

---

## Next Steps After Phase 5

1. **Merge to main** - `core-rebuild` → `main`
2. **Tag release** - Semantic versioning (e.g., `v4.5.0`)
3. **HACS submission** - If not already listed
4. **Announce** - Update README with new structure
5. **Monitor** - Watch for issues from users

---

**Phase 5 transforms the repository from "working custom component" to "professionally structured HACS integration" while maintaining 100% behavioral compatibility.**
