# Sensables.IO IAQ Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

A Home Assistant custom integration for Sensables.IO air quality monitoring devices. This integration receives webhook data from your IAQ sensors and automatically creates entities with proper units, device classes, and icons.

![Sensables.IO IAQ](https://raw.githubusercontent.com/Madbeefer/sensables-iaq/main/images/logo.png)

## Features

- 🎛️ **GUI Configuration** - Easy setup through Home Assistant's integration interface
- 📍 **Location Support** - Optional location field for organizing sensors by room
- 🌡️ **Temperature Conversion** - Automatic Celsius to Fahrenheit conversion
- 🎨 **Sensor Icons** - Material Design Icons for all sensor types
- 📊 **Device Grouping** - All sensors from one device grouped together
- ⚙️ **Configurable** - Webhook ID, sensor prefix, and expiration settings
- 🔄 **Auto-Cleanup** - Expired sensors automatically removed

## Supported Sensors

- **Temperature** (°C/°F) 🌡️
- **Humidity** (%) 💧
- **Indoor Air Quality Index** 🌬️
- **VOC** (ppb) ⚗️
- **CO2** (ppm) 🌍
- **Particulate Matter**: PM1.0, PM2.5, PM10 (μg/m³) 🌫️
- **Radon** (Bq/m³) ☢️
- **Carbon Monoxide** (ppm) ⚠️
- **Gas Resistance** (Ω)
- **MQ7 & MQ4 Sensors**
- **Mold Risk** 🍄
- **Smoke Detection** 🔥

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/Madbeefer/sensables-iaq`
6. Select category: "Integration"
7. Click "Add"
8. Click "Install" on the Sensables.IO IAQ card
9. Restart Home Assistant
10. Go to Settings → Devices & Services → Add Integration
11. Search for "Sensables.IO IAQ"

### Manual Installation

1. Copy the `sensables_iaq` folder to your `custom_components` directory:
```
   custom_components/
   └── sensables_iaq/
       ├── __init__.py
       ├── config_flow.py
       ├── const.py
       ├── manifest.json
       └── strings.json
```

2. Restart Home Assistant

3. Go to Settings → Devices & Services → Add Integration

4. Search for "Sensables.IO IAQ"

## Configuration

### Setup

During initial setup, you'll configure:

- **Webhook ID**: Unique identifier for your webhook endpoint (default: `sensables_iaq`)
- **Sensor Prefix**: Prefix for all sensor entities (default: `sensables`)
- **Location (Optional)**: Location name to include in sensor IDs (e.g., "Kitchen")
- **Temperature Unit**: Choose Celsius or Fahrenheit (automatic conversion)
- **Expire After**: Time in seconds before inactive sensors are removed (default: 3600)

### Webhook Endpoint

Your webhook URL will be:
```
http://your-home-assistant:8123/api/webhook/[your-webhook-id]
```

## Usage

### Webhook Data Format

Your Sensables.IO device should send POST requests with:

**Headers:**
```
Content-Type: application/json
device-name: Your Device Name
```

**Example Payload:**
```json
{
  "temperature": 25,
  "humidity": 43,
  "iaq": 94,
  "voc": 1,
  "co2": 757,
  "gas": 178087,
  "pm1": 11,
  "pm25": 13,
  "pm10": 13,
  "radon": 0,
  "mq7": 0,
  "mq4": 0,
  "mold": 0,
  "smoke": 0,
  "co": 0
}
```

### Example Sensors Created

With **Location**: "Kitchen" and **Device Name**: "Air Monitor"

- `sensor.sensables_kitchen_air_monitor_temperature` - Temperature (77°F)
- `sensor.sensables_kitchen_air_monitor_humidity` - Humidity (43%)
- `sensor.sensables_kitchen_air_monitor_co2` - CO2 (757 ppm)
- `sensor.sensables_kitchen_air_monitor_pm25` - PM2.5 (13 μg/m³)

**Device Name**: "Kitchen Air Monitor"

All sensors grouped under one device in Home Assistant.

### Testing the Integration

**Manual Test:**
```bash
curl -X POST http://your-home-assistant:8123/api/webhook/sensables_iaq \
  -H "Content-Type: application/json" \
  -H "device-name: Test Device" \
  -d '{
    "temperature": 22.5,
    "humidity": 45,
    "co2": 687,
    "pm25": 8,
    "voc": 2
  }'
```

**Python Test:**
```python
import requests

url = "http://your-home-assistant:8123/api/webhook/sensables_iaq"
headers = {
    "Content-Type": "application/json",
    "device-name": "Office Monitor"
}
data = {
    "temperature": 23,
    "humidity": 52,
    "iaq": 87,
    "co2": 723,
    "pm25": 12
}

response = requests.post(url, json=data, headers=headers, timeout=5)
print(f"Status: {response.status_code}")
```

## Configuration Options

You can modify settings after installation:

1. Go to Settings → Devices & Services
2. Find "Sensables.IO IAQ"
3. Click "Configure"
4. Update your settings
5. Integration will reload automatically

## Multiple Devices

You can set up multiple integration instances with different webhook IDs for:
- Different device types
- Different locations
- Development vs production

## Automation Examples

### High CO2 Alert
```yaml
automation:
  - alias: "High CO2 Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.sensables_kitchen_air_monitor_co2
      above: 1000
    action:
      service: notify.mobile_app
      data:
        message: "High CO2 in Kitchen: {{ states('sensor.sensables_kitchen_air_monitor_co2') }} ppm"
```

### Poor Air Quality Notification
```yaml
automation:
  - alias: "Poor Air Quality"
    trigger:
      platform: numeric_state
      entity_id: sensor.sensables_bedroom_air_monitor_iaq
      above: 150
    action:
      service: notify.home_assistant
      data:
        title: "Air Quality Alert"
        message: "Air quality in bedroom is poor. Consider ventilation."
```

### Daily Air Quality Report
```yaml
automation:
  - alias: "Daily Air Quality Report"
    trigger:
      platform: time
      at: "09:00:00"
    action:
      service: notify.mobile_app
      data:
        title: "Morning Air Quality"
        message: >
          Kitchen:
          Temp: {{ states('sensor.sensables_kitchen_air_monitor_temperature') }}°F
          CO2: {{ states('sensor.sensables_kitchen_air_monitor_co2') }} ppm
          PM2.5: {{ states('sensor.sensables_kitchen_air_monitor_pm25') }} μg/m³
```

## Troubleshooting

### Integration Not Showing
- Ensure all files are in `custom_components/sensables_iaq/`
- Check `manifest.json` has `"config_flow": true`
- Restart Home Assistant
- Clear browser cache

### Webhook Returns 401
- Webhook should not require authentication
- Check reverse proxy settings
- Verify URL format

### Sensors Not Appearing
- Check Home Assistant logs (Settings → System → Logs)
- Verify device-name header is being sent
- Test with curl command above

### Sensors Disappearing
- Check "Expire After" setting
- Verify device is sending data regularly
- Review logs for expiration messages

### Temperature Not Converting
- Check temperature unit setting in integration config
- Verify incoming data is numeric
- Check logs for conversion errors

## Development

### Running Locally
```bash
# Clone repository
git clone https://github.com/Madbeefer/sensables-iaq.git

# Copy to Home Assistant
cp -r sensables-iaq/custom_components/sensables_iaq ~/.homeassistant/custom_components/

# Restart Home Assistant
```

### Debug Logging
```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.sensables_iaq: debug
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/Madbeefer/sensables-iaq/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Madbeefer/sensables-iaq/discussions)
- **Documentation**: [Wiki](https://github.com/Madbeefer/sensables-iaq/wiki)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 1.0.0 (2025-02-22)
- Initial release
- GUI configuration flow
- Temperature unit conversion (C/F)
- Optional location field
- Sensor icons (MDI)
- Device grouping
- Auto-cleanup of expired sensors
- Support for 15+ air quality sensor types

## Credits

- Created by [@Madbeefer](https://github.com/Madbeefer)
- Designed for [Sensables.IO](https://sensables.io) air quality monitors
- Built for [Home Assistant](https://www.home-assistant.io/)

## Disclaimer

This is a third-party integration and is not officially affiliated with or endorsed by Sensables.IO.

---

**Made with ❤️ for the Home Assistant community**

[releases-shield]: https://img.shields.io/github/release/Madbeefer/sensables-iaq.svg
[releases]: https://github.com/Madbeefer/sensables-iaq/releases
[license-shield]: https://img.shields.io/github/license/Madbeefer/sensables-iaq.svg
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
