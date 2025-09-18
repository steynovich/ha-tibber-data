# Implementation Plan: HACS Compatible Tibber Data Integration for Home Assistant

**Branch**: `001-build-a-hacs` | **Date**: 2025-09-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-build-a-hacs/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → Feature spec loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detected Project Type: single (Home Assistant integration)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → No violations detected (template constitution)
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → Resolve OAuth2 client setup and refresh frequency questions
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file
7. Re-evaluate Constitution Check section
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

## Summary
Build a HACS-compatible Home Assistant integration that leverages the Tibber Data API to automatically discover and monitor IoT devices (EVs, chargers, thermostats, solar inverters, batteries) connected through Tibber platform. The integration must meet Platinum quality standards with OAuth2 authentication, full async operation, comprehensive testing, and automated HACS validation via GitHub Actions.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: Home Assistant Core, aiohttp, HACS framework
**Storage**: Home Assistant entity registry, state machine
**Testing**: pytest, Home Assistant test framework, pytest-homeassistant-custom-component
**Target Platform**: Home Assistant OS/Supervised/Container/Core
**Project Type**: single - Home Assistant custom integration
**Performance Goals**: <5s device discovery, <2s state updates, efficient polling
**Constraints**: Async-only operations, HA Platinum standards, HACS compatibility
**Scale/Scope**: Support multiple homes, unlimited devices per home, real-time updates

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since the project uses a template constitution document, no specific violations are identified. Standard development best practices will apply:
- Test-driven development
- Clear separation of concerns
- Comprehensive documentation
- Type annotations

## Project Structure

### Documentation (this feature)
```
specs/001-build-a-hacs/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Home Assistant Custom Integration Structure
custom_components/tibber_data/
├── __init__.py          # Component setup and entry point
├── manifest.json        # Integration metadata for HACS
├── config_flow.py       # OAuth2 configuration flow
├── const.py            # Constants and configuration
├── coordinator.py      # Data update coordinator
├── entity.py           # Base entity classes
├── sensor.py           # Sensor entities
├── binary_sensor.py    # Binary sensor entities
├── switch.py           # Switch entities (if applicable)
└── api/
    ├── __init__.py
    ├── client.py       # Tibber Data API client
    └── models.py       # Data models

tests/
├── conftest.py         # Test configuration
├── test_init.py        # Component initialization tests
├── test_config_flow.py # Configuration flow tests
├── test_coordinator.py # Data coordinator tests
└── test_api/
    ├── test_client.py  # API client tests
    └── test_models.py  # Model tests

.github/
└── workflows/
    ├── validate.yml    # HACS validation
    ├── test.yml        # Automated testing
    └── release.yml     # Release automation

hacs.json               # HACS metadata
README.md              # Integration documentation
requirements.txt       # Python dependencies
```

**Structure Decision**: Single project structure optimized for Home Assistant custom integration with HACS compatibility

## Phase 0: Outline & Research

**Extract unknowns from Technical Context** above:
1. **OAuth2 client registration process**: Need to determine if Tibber provides self-service developer portal or requires manual approval
2. **Device state refresh frequency**: Research optimal polling intervals and user configuration options
3. **Home Assistant integration patterns**: Best practices for async coordinators and entity management
4. **HACS publishing requirements**: Specific validation rules and metadata requirements

**Generate and dispatch research agents**:
- Task: "Research Tibber Data API OAuth2 client registration process and developer onboarding"
- Task: "Find optimal polling strategies for Home Assistant integrations with external APIs"
- Task: "Research Home Assistant Platinum quality standards implementation patterns"
- Task: "Find HACS publishing requirements and GitHub Actions best practices"

**Consolidate findings** in `research.md` using format:
- Decision: [what was chosen]
- Rationale: [why chosen]
- Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - TibberHome: homeId, metadata, device relationships
   - TibberDevice: deviceId, externalId, capabilities, attributes
   - DeviceCapability: name, value, unit, lastUpdated
   - DeviceAttribute: connectivity, firmware, metadata
   - OAuthSession: tokens, scopes, expiry

2. **Generate API contracts** from functional requirements:
   - OAuth2 Authorization flow endpoints
   - Home discovery and device enumeration
   - Device state and capability endpoints
   - Device history retrieval (preview)
   - Output OpenAPI schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - OAuth2 flow validation tests
   - API client response parsing tests
   - Rate limiting and error handling tests
   - Tests must fail initially (no implementation)

4. **Extract test scenarios** from user stories:
   - Installation and OAuth setup flow
   - Device discovery and entity creation
   - State updates and automation triggers
   - Error recovery and connectivity issues

5. **Update agent file incrementally**:
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
   - Add Home Assistant integration context
   - Include Tibber API specifics
   - Maintain HACS compatibility requirements

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs
- Each API contract → contract test task [P]
- Each entity model → implementation task [P]
- Each configuration flow → UI test task
- Integration and end-to-end tests
- HACS validation and GitHub Actions setup

**Ordering Strategy**:
- TDD order: Tests before implementation
- Foundation first: manifest.json, __init__.py, const.py
- Core functionality: API client, data models, coordinator
- Integration layer: config flow, entities, platforms
- Quality assurance: comprehensive tests, HACS validation
- Mark [P] for parallel execution (independent components)

**Estimated Output**: 30-35 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, HACS validation, Home Assistant compatibility)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations identified - using template constitution.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `.specify/memory/constitution.md`*