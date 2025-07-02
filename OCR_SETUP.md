# OCR Setup Instructions

## Windows (Tesseract Installation)

1. **Download Tesseract for Windows:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download the latest installer (e.g., `tesseract-ocr-w64-setup-v5.3.3.20231005.exe`)

2. **Install Tesseract:**
   - Run the installer
   - Install to the default location: `C:\Program Files\Tesseract-OCR\`
   - Make sure to check "Add to PATH" during installation

3. **Verify Installation:**
   - Open Command Prompt and run: `tesseract --version`
   - If it doesn't work, manually add to PATH:
     - Add `C:\Program Files\Tesseract-OCR\` to your system PATH environment variable

## Alternative: Auto-detection in Code

The code will try to auto-detect Tesseract installation and fall back to visual comparison if OCR fails.

## Comparison Methods Available:

- **"text"** - Pure OCR text comparison (most accurate for text changes)
- **"combined"** - OCR + visual methods (recommended)
- **"ssim"** - Structural similarity (original method)
- **"phash"** - Perceptual hash (good for minor visual changes)
