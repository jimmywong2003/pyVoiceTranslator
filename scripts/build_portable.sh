#!/bin/bash
# =============================================================================
# Build Portable Executable - Phase 5
# =============================================================================
# Creates standalone executable using PyInstaller
#
# Usage:
#   ./scripts/build_portable.sh [macos|windows]
#
# Output:
#   dist/VoiceTranslate.app (macOS)
#   dist/VoiceTranslate.exe (Windows)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="VoiceTranslate"
APP_VERSION="2.0.0"

# Detect platform
PLATFORM=${1:-"auto"}
if [ "$PLATFORM" == "auto" ]; then
    case "$(uname -s)" in
        Darwin*) PLATFORM="macos" ;;
        MINGW*|CYGWIN*) PLATFORM="windows" ;;
        *) PLATFORM="linux" ;;
    esac
fi

echo -e "${GREEN}Building VoiceTranslate Pro v${APP_VERSION} for ${PLATFORM}${NC}"
echo "================================================"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}Error: PyInstaller not found${NC}"
    echo "Install with: pip install pyinstaller"
    exit 1
fi

# Build based on platform
cd "$(dirname "$0")/.."

case "$PLATFORM" in
    macos)
        echo -e "${YELLOW}Building macOS app bundle...${NC}"
        pyinstaller src/app/config/voice-translate-macos.spec \
            --clean \
            --noconfirm
        
        echo -e "${GREEN}Build complete!${NC}"
        echo "Output: dist/VoiceTranslate.app"
        echo ""
        echo "To run:"
        echo "  open dist/VoiceTranslate.app"
        echo ""
        echo "To fix macOS Gatekeeper (if needed):"
        echo "  xattr -cr dist/VoiceTranslate.app"
        ;;
    
    windows)
        echo -e "${YELLOW}Building Windows executable...${NC}"
        pyinstaller src/app/config/voice-translate-windows.spec \
            --clean \
            --noconfirm
        
        echo -e "${GREEN}Build complete!${NC}"
        echo "Output: dist/VoiceTranslate.exe"
        ;;
    
    linux)
        echo -e "${YELLOW}Building Linux executable...${NC}"
        # Use macOS spec as base (adjust as needed)
        pyinstaller src/app/config/voice-translate-macos.spec \
            --clean \
            --noconfirm
        
        echo -e "${GREEN}Build complete!${NC}"
        echo "Output: dist/VoiceTranslate"
        ;;
    
    *)
        echo -e "${RED}Unknown platform: $PLATFORM${NC}"
        echo "Usage: $0 [macos|windows]"
        exit 1
        ;;
esac

# Show build info
echo ""
echo -e "${GREEN}Build Information:${NC}"
echo "  App Name: ${APP_NAME}"
echo "  Version:  ${APP_VERSION}"
echo "  Platform: ${PLATFORM}"
echo "  Date:     $(date)"

# Size check
if [ -d "dist/VoiceTranslate.app" ]; then
    SIZE=$(du -sh dist/VoiceTranslate.app | cut -f1)
    echo "  Size:     ${SIZE}"
elif [ -f "dist/VoiceTranslate.exe" ]; then
    SIZE=$(du -sh dist/VoiceTranslate.exe | cut -f1)
    echo "  Size:     ${SIZE}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
