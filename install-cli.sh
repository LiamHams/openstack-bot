#!/bin/bash

# OpenStack Telegram Bot CLI Installer
# This script installs the CLI menu for the bot

set -e

echo "🖥️ OpenStack Telegram Bot CLI Installer"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Check if bot is installed
BOT_DIR="/opt/openstack-bot"
if [ ! -d "$BOT_DIR" ]; then
    echo "❌ OpenStack Telegram Bot is not installed."
    echo "Please run the installation script first."
    exit 1
fi

# Copy CLI script
echo "📥 Installing CLI script..."
cp op-bot-cli.sh "$BOT_DIR/"
chmod +x "$BOT_DIR/op-bot-cli.sh"

# Create symlink
echo "🔗 Creating command link..."
ln -sf "$BOT_DIR/op-bot-cli.sh" /usr/local/bin/op-bot
chmod +x /usr/local/bin/op-bot

echo ""
echo "✅ CLI menu installed successfully!"
echo ""
echo "To use the CLI menu, simply type:"
echo "  op-bot"
echo ""
echo "You can now manage your OpenStack Telegram Bot from the command line."
