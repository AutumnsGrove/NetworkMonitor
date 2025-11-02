# Extension Icons

## Required Icons
- `icon-48.png` - 48×48 px icon
- `icon-96.png` - 96×96 px icon

## Generating Icons

Use an online tool or graphic design software to create simple icons:
- Network/wifi symbol (📡)
- Monitor/graph symbol (📊)
- Colors: Blue (#0066cc) and Green (#00994d)

## Quick Generation Methods

### Method 1: Using ImageMagick
```bash
# Convert emoji to PNG (requires imagemagick)
convert -size 48x48 -background none -fill '#0066cc' -pointsize 40 label:'📡' icon-48.png
convert -size 96x96 -background none -fill '#0066cc' -pointsize 80 label:'📡' icon-96.png
```

### Method 2: Using Online Icon Generators
- [Favicon.io](https://favicon.io/) - Free favicon generator
- [RealFaviconGenerator](https://realfavicongenerator.net/) - Advanced icon generator
- [Canva](https://www.canva.com/) - Graphic design tool

### Method 3: Manual Creation
Use any image editor (GIMP, Photoshop, Sketch, Figma) to create:
1. 48×48 px PNG with transparent background
2. 96×96 px PNG with transparent background
3. Simple network/monitoring themed design
4. Blue/green color scheme

## Placeholder Icons

For testing purposes, you can use these simple base64 data URIs in manifest.json:

```json
"icons": {
  "48": "data:image/svg+xml;base64,...",
  "96": "data:image/svg+xml;base64,..."
}
```

However, for distribution, proper PNG files are required.

## Icon Design Guidelines

**Do:**
- Use simple, recognizable symbols
- Use high contrast colors
- Make it scalable (looks good at all sizes)
- Use transparent background
- Keep it minimal and clean

**Don't:**
- Use complex gradients
- Use too many colors
- Use small text or details
- Use white on transparent (invisible in some contexts)

## Testing Icons

After creating icons:
1. Check they appear in browser extension manager
2. Verify they're visible in both light and dark themes
3. Test at different sizes to ensure clarity

## Alternative: Use System Icons

For internal/personal use, you can skip custom icons and use browser defaults by removing the "icons" field from manifest.json. The browser will display a generic extension icon.
