# Tasks: HACS Compatible Tibber Data Integration for Home Assistant

**Input**: Design documents from `/specs/001-build-a-hacs/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Tech stack: Python 3.11+, Home Assistant Core, aiohttp, HACS framework
   → Extract: custom_components structure, async operations
2. Load design documents:
   → data-model.md: TibberHome, TibberDevice, DeviceCapability, DeviceAttribute, OAuthSession
   → contracts/: OAuth2 flow, homes, devices, capabilities endpoints
   → research.md: OAuth2 contact-based registration, 60s polling intervals
   → quickstart.md: Installation scenarios, device discovery, automation testing
3. Generate tasks by category:
   → Setup: HACS structure, manifest.json, dependencies
   → Tests: contract tests, config flow tests, coordinator tests
   → Core: API client, data models, coordinator, entities
   → Integration: config flow, platforms, device registry
   → Polish: GitHub Actions, documentation, final validation
4. Apply TDD principles: All tests before implementation
5. Mark [P] for parallel execution (independent files/components)
6. Number tasks sequentially (T001, T002...)
7. SUCCESS: 35 tasks ready for execution
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup
- [ ] T001 Create HACS-compatible project structure per implementation plan
- [ ] T002 Initialize manifest.json with HACS metadata in custom_components/tibber_data/
- [ ] T003 [P] Configure HACS validation files: hacs.json, .github/workflows/validate.yml
- [ ] T004 [P] Create requirements.txt and setup GitHub Actions workflows
- [ ] T005 [P] Initialize test configuration with pytest and Home Assistant test helpers in tests/conftest.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### OAuth2 Contract Tests
- [ ] T006 [P] Contract test OAuth2 authorization endpoint in tests/test_api/test_oauth2_auth.py
- [ ] T007 [P] Contract test OAuth2 token exchange in tests/test_api/test_oauth2_token.py
- [ ] T008 [P] Contract test OAuth2 token refresh in tests/test_api/test_oauth2_refresh.py

### API Contract Tests
- [ ] T009 [P] Contract test GET /v1/homes in tests/test_api/test_homes.py
- [ ] T010 [P] Contract test GET /v1/homes/{homeId} in tests/test_api/test_home_details.py
- [ ] T011 [P] Contract test GET /v1/homes/{homeId}/devices in tests/test_api/test_devices.py
- [ ] T012 [P] Contract test GET /v1/homes/{homeId}/devices/{deviceId} in tests/test_api/test_device_details.py
- [ ] T013 [P] Contract test GET /v1/homes/{homeId}/devices/{deviceId}/history in tests/test_api/test_device_history.py

### Integration Tests
- [ ] T014 [P] Integration test OAuth2 configuration flow in tests/test_config_flow.py
- [ ] T015 [P] Integration test device discovery coordinator in tests/test_coordinator.py
- [ ] T016 [P] Integration test component initialization in tests/test_init.py
- [ ] T017 [P] Integration test sensor entities in tests/test_sensor.py
- [ ] T018 [P] Integration test binary sensor entities in tests/test_binary_sensor.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### API Client and Models
- [ ] T019 [P] OAuthSession model in custom_components/tibber_data/api/models.py
- [ ] T020 [P] TibberHome model in custom_components/tibber_data/api/models.py
- [ ] T021 [P] TibberDevice model in custom_components/tibber_data/api/models.py
- [ ] T022 [P] DeviceCapability model in custom_components/tibber_data/api/models.py
- [ ] T023 [P] DeviceAttribute model in custom_components/tibber_data/api/models.py
- [ ] T024 OAuth2 client implementation in custom_components/tibber_data/api/client.py
- [ ] T025 Tibber Data API client implementation in custom_components/tibber_data/api/client.py

### Integration Components
- [ ] T026 Constants and configuration in custom_components/tibber_data/const.py
- [ ] T027 Base entity classes in custom_components/tibber_data/entity.py
- [ ] T028 Data update coordinator in custom_components/tibber_data/coordinator.py
- [ ] T029 OAuth2 configuration flow in custom_components/tibber_data/config_flow.py
- [ ] T030 Component entry point and setup in custom_components/tibber_data/__init__.py

### Platform Implementations
- [ ] T031 Sensor platform for device capabilities in custom_components/tibber_data/sensor.py
- [ ] T032 Binary sensor platform for device attributes in custom_components/tibber_data/binary_sensor.py

## Phase 3.4: Integration & Validation
- [ ] T033 Device registry integration and entity relationship setup
- [ ] T034 Error handling, token refresh, and recovery mechanisms
- [ ] T035 Run quickstart.md validation scenarios and fix any issues

## Dependencies
- Setup (T001-T005) before all other phases
- All tests (T006-T018) before implementation (T019-T032)
- Models (T019-T023) before API client (T024-T025)
- Core components (T026-T028) before config flow (T029)
- Config flow (T029) before component init (T030)
- Entity framework (T027) before platforms (T031-T032)
- Implementation complete before validation (T033-T035)

## Parallel Execution Examples

### Contract Tests Phase (T006-T013)
```bash
# Launch all OAuth2 contract tests together:
Task: "Contract test OAuth2 authorization endpoint in tests/test_api/test_oauth2_auth.py"
Task: "Contract test OAuth2 token exchange in tests/test_api/test_oauth2_token.py"
Task: "Contract test OAuth2 token refresh in tests/test_api/test_oauth2_refresh.py"

# Launch all API contract tests together:
Task: "Contract test GET /v1/homes in tests/test_api/test_homes.py"
Task: "Contract test GET /v1/homes/{homeId} in tests/test_api/test_home_details.py"
Task: "Contract test GET /v1/homes/{homeId}/devices in tests/test_api/test_devices.py"
```

### Integration Tests Phase (T014-T018)
```bash
# Launch all integration tests together:
Task: "Integration test OAuth2 configuration flow in tests/test_config_flow.py"
Task: "Integration test device discovery coordinator in tests/test_coordinator.py"
Task: "Integration test component initialization in tests/test_init.py"
Task: "Integration test sensor entities in tests/test_sensor.py"
Task: "Integration test binary sensor entities in tests/test_binary_sensor.py"
```

### Data Models Phase (T019-T023)
```bash
# Launch all model implementations together:
Task: "OAuthSession model in custom_components/tibber_data/api/models.py"
Task: "TibberHome model in custom_components/tibber_data/api/models.py"
Task: "TibberDevice model in custom_components/tibber_data/api/models.py"
Task: "DeviceCapability model in custom_components/tibber_data/api/models.py"
Task: "DeviceAttribute model in custom_components/tibber_data/api/models.py"
```

## Notes
- [P] tasks = different files, no dependencies between them
- Must verify all tests fail before implementing (TDD principle)
- Each task should result in a Git commit
- OAuth2 client registration requires contacting Tibber support
- Integration must meet Home Assistant Platinum quality standards
- All operations must be fully async for HA compatibility

## Task Generation Rules Applied

1. **From Contracts**: 8 endpoint contracts → 8 contract test tasks [P]
2. **From Data Model**: 5 entities → 5 model creation tasks [P]
3. **From Quickstart**: 10 scenarios → 5 integration test tasks [P]
4. **HACS Requirements**: Setup, validation, GitHub Actions
5. **HA Platform Standards**: Coordinator, config flow, entity platforms

## Validation Checklist
- [✓] All contracts have corresponding tests (T006-T013)
- [✓] All entities have model tasks (T019-T023)
- [✓] All tests come before implementation (Phase 3.2 → 3.3)
- [✓] Parallel tasks truly independent (different files)
- [✓] Each task specifies exact file path
- [✓] No task modifies same file as another [P] task
- [✓] TDD principle enforced (tests must fail before implementation)
- [✓] HACS compatibility requirements included
- [✓] Home Assistant integration patterns followed