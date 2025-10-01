# Tibber Data Integration for Home Assistant

A HACS-compatible Home Assistant integration that provides access to the Tibber Data API for monitoring IoT devices connected through the Tibber platform.

## Supported Devices

- **Electric Vehicles (EV)** - Battery level, charging status, charging power
- **EV Chargers** - Charging current, power output, connectivity status
- **Thermostats** - Temperature readings, heating status, target temperature
- **Solar Inverters** - Solar production, power output
- **Battery Storage** - Battery level, charging/discharging status
- **Heat Pumps** - Temperature control, power consumption

## Features

- **Automatic Device Discovery** - Discovers all devices connected to your Tibber account
- **Real-time Monitoring** - Updates device states every 60 seconds
- **OAuth2 Authentication** - Secure authentication using Home Assistant's application credentials
- **Device Organization** - Groups devices by Tibber homes for easy management
- **Home Assistant Integration** - Full integration with automations, scripts, and dashboards
- **HACS Compatible** - Easy installation and updates through HACS

## Prerequisites

- **Tibber Account**: You need an active Tibber account
- **Connected Devices**: You must have IoT devices connected through the Tibber platform (EVs, EV chargers, thermostats, solar inverters, etc.)
- **Tibber Data API Access**: Your account must have access to the Tibber Data API (contact Tibber support if unsure)
- **Home Assistant**: Running Home Assistant 2023.1 or later with HACS installed

### ⚠️ **Important Notes About Tibber Data API**

The Tibber Data API is **different** from the regular Tibber GraphQL API. It requires:

1. **Special API Access**: Not all Tibber customers automatically have Data API access
2. **Connected Devices**: You must have devices connected through Tibber's IoT platform
3. **Device Categories**: Supported devices include:
   - Electric Vehicles (EVs) with Tibber integration
   - EV Chargers connected to Tibber
   - Smart Thermostats
   - Solar Inverters
   - Battery Storage Systems
   - Heat Pumps

**If you only have a regular Tibber electricity subscription without connected IoT devices, this integration will not work.**

## Installation

### 1. Install via HACS

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button and search for "Tibber Data"
4. Click "Download"
5. Restart Home Assistant

### 2. Set up OAuth2 Application Credentials

Before configuring the integration, you need to register an OAuth2 application with Tibber:

#### Register with Tibber
1. Go to [Tibber Data API Client Management](https://data-api.tibber.com/clients/manage)
2. Log in with your Tibber account credentials
3. Create a new OAuth2 client application:
   - **Application name**: "Home Assistant Integration" (or similar)
   - **Redirect URI**: `https://your-home-assistant-url/auth/external/callback`
   - **Required scopes**:
     - `openid` (OpenID Connect)
     - `profile` (Basic profile information)
     - `email` (Email address)
     - `offline_access` (Refresh token support)
     - `data-api-user-read` (User data access)
     - `data-api-homes-read` (Homes data access)
     - `data-api-vehicles-read` (Electric vehicle data access)
     - `data-api-chargers-read` (EV charger data access)
     - `data-api-thermostats-read` (Thermostat data access)
     - `data-api-energy-systems-read` (Battery storage and energy system data access)
     - `data-api-inverters-read` (Solar inverter data access)
4. Save your **Client ID** - you'll need this for Home Assistant

#### Add Credentials to Home Assistant
1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration** and search for "Application Credentials"
3. Select "Application Credentials"
4. Choose "Tibber Data" from the list
5. Enter the **Client ID** provided by Tibber support
6. Leave **Client Secret** empty (not required for Tibber Data API)
7. Click "Create"

### 3. Configure the Integration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Tibber Data" and select it
3. Click "Continue" to start the OAuth2 authentication flow
4. You'll be redirected to Tibber's authorization page
5. Log in with your Tibber account and grant permissions
6. You'll be redirected back to Home Assistant
7. The integration will discover your devices automatically

## Configuration

### Options

You can configure the following options after setup:

- **Update Interval**: How often to poll the API (30-900 seconds, default: 60)
- **Include Offline Devices**: Whether to include devices that are currently offline

### Multiple Homes

If you have multiple Tibber homes, all devices will be discovered automatically. Devices will be organized by home in the Home Assistant device registry.

## Entities

The integration creates the following types of entities:

### Sensors

**Capability Sensors** (from device capabilities):
- **Battery Level** (%) - For EVs and battery storage systems
- **Charging Power** (kW) - Current charging/discharging power
- **Temperature** (°C) - For thermostats and heat pumps
- **Energy Consumption** (kWh) - Total energy consumed
- **Solar Production** (kWh) - Total solar energy produced
- **Charging Current** (A) - Current draw during charging
- **Signal Strength** (%) - Device connectivity strength
- **Charging Status** (ENUM) - Vehicle charging status (Idle/Charging/Complete/Error/Unknown)
- **Connector Status** (ENUM) - Vehicle plug status (Connected/Disconnected/Unknown)
- **Cellular Connectivity** (ENUM) - Cellular connection status
- **WiFi Connectivity** (ENUM) - WiFi connection status
- **Estimated Range** (km) - Remaining driving range (converted from meters)
- **Energy Flow Sensors** - Automatically formatted for clarity:
  - Grid Import Energy (Hour/Day/etc.) - Energy imported from grid
  - Grid Export Energy from Battery (Hour/Day/etc.) - Battery energy exported to grid
  - Load Energy from Battery (Hour/Day/etc.) - Battery energy used by load

**Attribute Sensors** (from device attributes):
- **VIN Number** - Vehicle identification number (diagnostic)
- **Serial Number** - Device serial number (diagnostic)
- **Firmware Version** - Current firmware version (diagnostic)
- Other string/numeric device attributes as applicable

### Binary Sensors
- **Online** - Whether the device is connected
- **Update Available** - Firmware update availability
- **Charging** - Whether EV/battery is currently charging
- **Error Status** - Any device errors or problems

## Automation Examples

### EV Charging Notification
```yaml
automation:
  - alias: "EV Charging Started"
    trigger:
      - platform: state
        entity_id: binary_sensor.tesla_charging
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Tesla has started charging"
```

### Smart Thermostat Control
```yaml
automation:
  - alias: "Adjust Temperature Based on Solar Production"
    trigger:
      - platform: numeric_state
        entity_id: sensor.solar_inverter_power
        above: 2000
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room_thermostat
        data:
          temperature: 22
```

## Troubleshooting

### Common Issues

#### "Missing OAuth2 credentials configured"
- Make sure you've set up Application Credentials as described above
- Verify the Client ID is correct
- Ensure you selected "Tibber Data" when creating the application credential

#### "Authentication failed" or "Invalid request" during OAuth2 flow
- **PKCE Implementation**: This integration automatically includes PKCE (Proof Key for Code Exchange) support required by Tibber
  - No manual configuration needed - PKCE parameters are added automatically
  - If you still see "invalid request" errors, the issue is likely with client registration
- **Check Redirect URI**: Ensure your OAuth2 client is configured with the exact redirect URI:
  - For Home Assistant Cloud: `https://my.home-assistant.io/redirect/oauth`
  - For Local Installation: `https://YOUR-HA-URL/auth/external/callback`
  - URI must match exactly (case-sensitive)
- **Verify Client Registration**: At [Tibber Client Management](https://data-api.tibber.com/clients/manage):
  - **Application Type**: Public Client (no client secret)
  - **Required Scopes**: `openid`, `profile`, `email`, `offline_access`, `data-api-user-read`, `data-api-homes-read`
  - **Redirect URI**: Must match your Home Assistant setup exactly
- **Troubleshooting Steps**:
  1. Delete and recreate your Home Assistant application credential
  2. Verify the Client ID matches your Tibber registration exactly
  3. Ensure you're using Home Assistant 2023.1 or later
  4. Try the OAuth flow again

#### "Token expired" or authentication stops working after some time
- **Automatic Token Refresh**: The integration automatically refreshes expired tokens
- **Reauth Flow**: If token refresh fails, you'll receive a notification to re-authenticate
  - Go to **Settings** → **Devices & Services** → **Tibber Data**
  - Click "Configure" or the notification banner
  - Complete the authentication flow again
- **If reauth doesn't trigger automatically**:
  1. Try reloading the integration
  2. If issues persist, remove and re-add the integration

#### "Cannot connect to Tibber Data API"
- Check your internet connection
- Verify your Tibber account has access to the Data API
- Contact Tibber support if the issue persists

#### "No homes found" during setup
- **Most Common Issue**: You may not have Tibber Data API access or connected devices
- **Check Your Account**:
  1. Log in to [Tibber Data API Client Management](https://data-api.tibber.com/clients/manage)
  2. If you can't access this page, you don't have Data API access
  3. Contact Tibber support to request Data API access
- **Verify Connected Devices**:
  1. Open the regular Tibber mobile app
  2. Check if you have any connected IoT devices (EVs, chargers, thermostats, etc.)
  3. If not, you need to connect devices first before using this integration
- **API Endpoint Test**: The integration tries to access `/v1/homes` - this only returns homes with connected IoT devices

#### Devices not showing up
- Make sure your devices are connected to Tibber and showing in the Tibber app
- Check that your OAuth2 client has the required scopes:
  - `openid`, `profile`, `email`, `offline_access`
  - `data-api-user-read`, `data-api-homes-read`
  - `data-api-vehicles-read`, `data-api-chargers-read`, `data-api-thermostats-read`
  - `data-api-energy-systems-read`, `data-api-inverters-read`
- Try reloading the integration

### Debug Logging

To enable debug logging for troubleshooting:

```yaml
logger:
  default: warning
  logs:
    custom_components.tibber_data: debug
```

## API Rate Limits

The Tibber Data API has the following limits:
- **100 requests per 5 minutes** per IP address
- The integration respects these limits automatically
- Default update interval (60 seconds) stays well within limits

## Support

- **Issues**: [GitHub Issues](https://github.com/steynovich/ha-tibber-data/issues)
- **Documentation**: [Tibber Data API Docs](https://data-api.tibber.com/docs/)
- **Tibber Support**: Contact via the Tibber app or website

## Contributing

Contributions are welcome! Please see the [contributing guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.