# Quickstart Guide: Tibber Data Integration

**Date**: 2025-09-18
**Purpose**: Validation scenarios for successful integration implementation

## Prerequisites

1. **Home Assistant Instance**: Running version 2024.4.1 or later
2. **Tibber Account**: Active account with connected IoT devices
3. **OAuth2 Client**: Registered with Tibber (contact support at developer.tibber.com)
4. **HACS Installation**: Home Assistant Community Store installed and configured

## Installation Scenarios

### Scenario 1: HACS Installation (Primary Path)

**Given**: User has HACS installed and OAuth2 client credentials
**When**: Installing the Tibber Data integration through HACS
**Then**: Integration appears in HA integrations and can be configured

**Steps**:
1. Open Home Assistant
2. Navigate to HACS → Integrations
3. Click "+ EXPLORE & DOWNLOAD REPOSITORIES"
4. Search for "Tibber Data"
5. Click "DOWNLOAD"
6. Restart Home Assistant
7. Navigate to Settings → Devices & Services → Integrations
8. Click "+ ADD INTEGRATION"
9. Search for and select "Tibber Data"

**Success Criteria**:
- Integration appears in available integrations list
- Configuration flow starts without errors
- OAuth2 authorization redirect works correctly

### Scenario 2: OAuth2 Configuration Flow

**Given**: Integration is installed and user has valid OAuth2 client
**When**: Configuring the integration for first time
**Then**: OAuth2 flow completes successfully and devices are discovered

**Steps**:
1. Start integration configuration
2. Enter OAuth2 client ID when prompted
3. Click "Authorize with Tibber"
4. Complete OAuth2 flow in browser
5. Return to Home Assistant
6. Verify device discovery completed

**Success Criteria**:
- Browser opens Tibber authorization page
- User can grant permissions successfully
- Authorization code is exchanged for access token
- Integration shows "Configuration successful" message
- Devices appear in device registry within 60 seconds

## Device Discovery Testing

### Scenario 3: Multi-Home Device Discovery

**Given**: User has multiple Tibber homes with various devices
**When**: Integration discovers devices
**Then**: All homes and devices are properly represented in HA

**Test Data Requirements**:
- At least 2 Tibber homes
- Minimum device types: EV, charger, thermostat
- Mix of online and offline devices

**Verification Steps**:
1. Check Devices & Services → Tibber Data
2. Verify each home appears as separate area/device
3. Verify all expected devices are listed
4. Check device entities are created correctly
5. Verify device states reflect actual values

**Success Criteria**:
- All homes discovered and named correctly
- All connected devices appear in device list
- Device types are correctly identified
- Online/offline status matches actual state
- Entity states show current capability values

### Scenario 4: Entity State Updates

**Given**: Devices are discovered and online
**When**: Device states change in Tibber system
**Then**: Entity states update in Home Assistant within refresh interval

**Test Actions**:
1. Start EV charging (if available)
2. Change thermostat temperature
3. Wait for coordinator update cycle (60 seconds)
4. Check entity states in HA

**Success Criteria**:
- Entity states reflect actual device changes
- Updates occur within 60-90 seconds
- No unnecessary API calls made
- Error states handled gracefully

## Error Handling Scenarios

### Scenario 5: OAuth2 Token Expiry

**Given**: Integration has been running with valid tokens
**When**: Access token expires
**Then**: Integration refreshes token automatically or triggers reauth

**Test Steps**:
1. Let integration run until token expires
2. Verify automatic refresh occurs
3. If refresh fails, verify reauth notification appears
4. Complete reauth flow if required

**Success Criteria**:
- Token refresh occurs automatically before expiry
- No service interruption during token refresh
- Reauth notification appears if refresh fails
- Reauth flow completes successfully

### Scenario 6: API Unavailable

**Given**: Integration is configured and running
**When**: Tibber Data API becomes unavailable
**Then**: Integration handles errors gracefully

**Simulation**:
1. Block network access to data-api.tibber.com
2. Wait for next coordinator update
3. Verify error handling behavior
4. Restore network access
5. Verify service recovery

**Success Criteria**:
- Entities marked as "unavailable" during outage
- No excessive retry attempts
- Service recovers automatically when API available
- Users notified of persistent issues

### Scenario 7: Device Connectivity Issues

**Given**: Devices are discovered and configured
**When**: A device goes offline
**Then**: Device status updates correctly in HA

**Test Steps**:
1. Disconnect a test device from network
2. Wait for next API update cycle
3. Verify device shows as offline
4. Reconnect device
5. Verify device shows as online again

**Success Criteria**:
- Offline devices marked unavailable in HA
- Device capabilities marked unavailable when offline
- Online status updates when connectivity restored
- No phantom state updates while offline

## Automation Integration Testing

### Scenario 8: Entity Usage in Automations

**Given**: Devices are discovered and entities available
**When**: Creating automations using Tibber device entities
**Then**: Entities work correctly in automation triggers and conditions

**Test Automations**:
1. **EV Charging Alert**: Trigger when EV starts/stops charging
2. **Temperature Control**: Use thermostat state in climate automation
3. **Energy Monitoring**: Track solar production or battery state

**Verification**:
1. Create test automations using Tibber entities
2. Verify entities appear in automation editor
3. Test automation triggers work correctly
4. Verify state changes trigger automations

**Success Criteria**:
- All entity types available in automation editor
- Automation triggers fire correctly
- Entity states usable in conditions and templates
- No automation failures due to entity unavailability

## Performance Validation

### Scenario 9: Resource Usage Monitoring

**Given**: Integration running with multiple devices
**When**: Monitoring system performance over 24 hours
**Then**: Resource usage remains within acceptable limits

**Monitoring Criteria**:
- CPU usage during coordinator updates
- Memory usage growth over time
- Network requests frequency and size
- Database query performance

**Benchmarks**:
- Coordinator updates complete within 5 seconds
- Memory usage stable (no memory leaks)
- API rate limits respected (max 100 req/5min)
- No significant HA performance impact

### Scenario 10: Large Scale Testing

**Given**: User with maximum expected device count
**When**: Integration handles large number of devices
**Then**: Performance remains acceptable

**Test Configuration**:
- 3 Tibber homes
- 20+ devices total
- Mix of all supported device types
- Simulated high-frequency capability changes

**Performance Targets**:
- Initial device discovery completes within 30 seconds
- Regular updates complete within 10 seconds
- Entity state propagation within 2 seconds
- No timeout errors during bulk operations

## Validation Completion Checklist

### Integration Health
- [ ] All installation scenarios pass
- [ ] OAuth2 flow completes successfully
- [ ] Device discovery works for all supported types
- [ ] Entity states update correctly
- [ ] Error scenarios handled gracefully

### User Experience
- [ ] Configuration flow is intuitive
- [ ] Device names and entities are user-friendly
- [ ] Integration appears correctly in HA UI
- [ ] Documentation is clear and complete
- [ ] Error messages are helpful

### Technical Quality
- [ ] No memory leaks detected
- [ ] Performance within acceptable limits
- [ ] API rate limits respected
- [ ] Proper async operation confirmed
- [ ] All tests pass in CI/CD pipeline

### HACS Compliance
- [ ] Integration installs via HACS
- [ ] All required files present and valid
- [ ] GitHub Actions validation passes
- [ ] Documentation meets HACS standards
- [ ] Release process works correctly

**Integration Ready**: All scenarios pass and checklist complete