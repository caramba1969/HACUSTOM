# My Custom Device - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Custom Home Assistant integration for My Custom Device.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/my_custom_device` directory to your `custom_components` folder in your Home Assistant config directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "+ Add Integration"
3. Search for "My Custom Device"
4. Follow the configuration steps:
   - Enter a name for your device
   - Enter the host address
   - Enter the port (default: 8080)

## Features

- Sensor entity for device status
- Configuration through UI (Config Flow)
- Full HACS compatibility

## Development

This integration includes:
- Configuration flow for easy setup
- Sensor platform (expandable to other platforms)
- Proper error handling
- Localization support via strings.json

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/yourgithubusername/my_custom_device/issues).

## License

MIT License - See LICENSE file for details
