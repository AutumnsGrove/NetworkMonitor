# Network Monitor - Browser Extension

WebExtension for tracking active tab domains in Zen Browser (Firefox-based).

## Features

- Tracks currently active browser tab
- Reports domain to Network Monitor API
- Privacy-focused: Only tracks active tab, not all tabs
- Lightweight: Minimal resource usage
- Automatic rollup: Reports parent domain (netflix.com instead of www.netflix.com)

## Installation

### Development Installation (Temporary)

1. Open Zen Browser
2. Navigate to `about:debugging`
3. Click "This Zen" (or "This Firefox")
4. Click "Load Temporary Add-on"
5. Navigate to `extension/manifest.json` and select it
6. Extension will be loaded until browser restart

### Permanent Installation (Advanced)

1. Zip the extension directory:
   ```bash
   cd extension
   zip -r network-monitor-extension.zip *
   ```

2. Sign the extension:
   - Visit [https://addons.mozilla.org/developers/](https://addons.mozilla.org/developers/)
   - Upload zip file
   - Download signed .xpi file

3. Install signed extension:
   - Open Zen Browser
   - Drag and drop .xpi file into browser
   - Confirm installation

## Configuration

### API Endpoint
Default: `http://localhost:7500/api/browser/active-tab`

To change, edit `extension/background.js`:
```javascript
const API_ENDPOINT = 'http://localhost:7500/api/browser/active-tab';
```

### Report Interval
Default: 5 seconds

To change, edit `extension/background.js`:
```javascript
const REPORT_INTERVAL = 5000; // milliseconds
```

### Browser Name
Default: "zen"

To change, edit `extension/background.js`:
```javascript
const BROWSER_NAME = 'zen';
```

## Testing

1. Install extension (see above)
2. Ensure Network Monitor API is running:
   ```bash
   cd /path/to/NetworkMonitor
   uv run python src/webserver.py
   ```
3. Open any website (e.g., https://netflix.com)
4. Check browser console (F12 → Console) for extension logs
5. Check API logs for incoming POST requests
6. Query database to verify domain was recorded:
   ```bash
   sqlite3 ~/.netmonitor/network_monitor.db "SELECT * FROM browser_domain_samples ORDER BY timestamp DESC LIMIT 10;"
   ```

## Troubleshooting

### Extension doesn't load
- Check manifest.json syntax (use JSONLint)
- Ensure icons directory exists
- Check browser console for errors

### No data appears in dashboard
- Ensure API server is running (localhost:7500)
- Check browser console for CORS or network errors
- Verify extension permissions in about:addons
- Test API endpoint manually:
  ```bash
  curl -X POST http://localhost:7500/api/browser/active-tab \
    -H "Content-Type: application/json" \
    -d '{"domain": "test.com", "timestamp": 1234567890, "browser": "zen"}'
  ```

### Extension stops working after browser restart
- This is expected for temporary add-ons
- Reload extension from about:debugging
- Or install permanently (see above)

## Privacy & Security

- **Local Only**: All data stays on your machine
- **Active Tab Only**: Extension only tracks the currently active tab
- **No Full URLs**: Only domain names are reported (no paths, parameters, or query strings)
- **No Telemetry**: Extension does not send data to any third party
- **Minimal Permissions**: Only requests `tabs` and `localhost` permissions

## Development

### File Structure
```
extension/
├── manifest.json       # Extension metadata
├── background.js       # Main extension logic
├── icons/
│   ├── icon-48.png    # 48×48 icon
│   └── icon-96.png    # 96×96 icon
└── README.md          # This file
```

### Making Changes

1. Edit files in `extension/` directory
2. Reload extension:
   - Go to `about:debugging`
   - Click "Reload" next to Network Monitor extension
3. Test changes

### Debugging

- Open browser console: F12 → Console
- Filter by "Network Monitor" to see extension logs
- Use `console.log()` in background.js for debugging

## API Integration

The extension sends POST requests to `/api/browser/active-tab` with this payload:

```json
{
  "domain": "netflix.com",
  "timestamp": 1699123456,
  "browser": "zen"
}
```

The API endpoint is already implemented in `src/api/browser.py`.

## Future Enhancements

- Settings page (popup UI) for configuring API endpoint and interval
- Statistics display in extension popup
- Support for multiple browsers (Chrome, Safari)
- Whitelist/blacklist for domain tracking
- Offline queue for API requests
