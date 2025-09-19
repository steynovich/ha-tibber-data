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

- **Tibber Account**: You need an active Tibber account with devices connected through the Tibber platform
- **Tibber Data API Access**: Your account must have access to the Tibber Data API
- **Home Assistant**: Running Home Assistant 2023.1 or later with HACS installed

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
     - `data-api-homes-read` (Homes and device data access)
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
- **Battery Level** (%) - For EVs and battery storage systems
- **Charging Power** (kW) - Current charging/discharging power
- **Temperature** (°C) - For thermostats and heat pumps
- **Energy Consumption** (kWh) - Total energy consumed
- **Solar Production** (kWh) - Total solar energy produced
- **Charging Current** (A) - Current draw during charging
- **Signal Strength** (%) - Device connectivity strength

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

#### "Authentication failed"
- Your OAuth2 tokens may have expired - try re-authenticating
- Go to the integration settings and click "Configure"
- Complete the OAuth2 flow again

#### "Cannot connect to Tibber Data API"
- Check your internet connection
- Verify your Tibber account has access to the Data API
- Contact Tibber support if the issue persists

#### Devices not showing up
- Make sure your devices are connected to Tibber and showing in the Tibber app
- Check that your OAuth2 client has the required scopes:
  - `openid`, `profile`, `email`, `offline_access`
  - `data-api-user-read`, `data-api-homes-read`
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