#!/bin/bash

# OpenStack Telegram Bot Uninstall Script
# This script completely removes the bot from the system

set -e

echo "🗑️ OpenStack Telegram Bot Uninstall Script"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Confirm uninstallation
echo "⚠️ WARNING: This will completely remove the OpenStack Telegram Bot from your system."
echo "All data, logs, and configurations will be deleted."
echo ""
read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""
echo "🔄 Stopping and disabling services..."

# Stop and disable systemd service
if systemctl is-active --quiet openstack-bot; then
    systemctl stop openstack-bot
    echo "✅ Service stopped"
fi

if systemctl is-enabled --quiet openstack-bot; then
    systemctl disable openstack-bot
    echo "✅ Service disabled"
fi

# Remove systemd service file
if [ -f "/etc/systemd/system/openstack-bot.service" ]; then
    rm /etc/systemd/system/openstack-bot.service
    echo "✅ Service file removed"
fi

# Reload systemd
systemctl daemon-reload
echo "✅ Systemd reloaded"

# Remove log rotation configuration
if [ -f "/etc/logrotate.d/openstack-bot" ]; then
    rm /etc/logrotate.d/openstack-bot
    echo "✅ Log rotation configuration removed"
fi

# Remove cron jobs
echo "🔄 Removing cron jobs..."
(crontab -l 2>/dev/null | grep -v "openstack-bot") | crontab -
echo "✅ Cron jobs removed"

# Remove CLI command
if [ -f "/usr/local/bin/op-bot" ]; then
    rm /usr/local/bin/op-bot
    echo "✅ CLI command removed"
fi

# Remove bot directory
echo "🔄 Removing bot files..."
BOT_DIR="/opt/openstack-bot"
if [ -d "$BOT_DIR" ]; then
    # Backup configuration if requested
    read -p "Would you like to backup the configuration before deletion? (y/N): " backup
    if [[ "$backup" == "y" || "$backup" == "Y" ]]; then
        BACKUP_DIR="$HOME/openstack-bot-backup-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        if [ -f "$BOT_DIR/config.env" ]; then
            cp "$BOT_DIR/config.env" "$BACKUP_DIR/"
            echo "✅ Configuration backed up to $BACKUP_DIR"
        fi
        if [ -f "$BOT_DIR/openstack_bot.log" ]; then
            cp "$BOT_DIR/openstack_bot.log" "$BACKUP_DIR/"
            echo "✅ Logs backed up to $BACKUP_DIR"
        fi
    fi
    
    # Remove directory
    rm -rf "$BOT_DIR"
    echo "✅ Bot directory removed"
fi

# Remove user account
echo "🔄 Removing bot user..."
if id "openstackbot" &>/dev/null; then
    userdel -r openstackbot 2>/dev/null || true
    echo "✅ User 'openstackbot' removed"
fi

echo ""
echo "✅ OpenStack Telegram Bot has been completely removed from your system."
echo ""
echo "The following items were removed:"
echo "• Bot service and configuration"
echo "• Bot files and directories"
echo "• Bot user account"
echo "• Cron jobs"
echo "• Log rotation configuration"
echo "• CLI command"
echo ""

if [[ "$backup" == "y" || "$backup" == "Y" ]]; then
    echo "Your configuration has been backed up to: $BACKUP_DIR"
fi

echo "Thank you for using OpenStack Telegram Bot!"
