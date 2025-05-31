#!/bin/bash

# OpenStack Telegram Bot Installation Script
# This script installs the bot and its dependencies on Ubuntu 22.04

set -e

echo "🤖 OpenStack Telegram Bot Installation Script"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Python 3 and pip if not already installed
echo "🐍 Installing Python 3 and pip..."
apt install -y python3 python3-pip python3-venv git

# Create bot user
echo "👤 Creating bot user..."
if ! id "openstackbot" &>/dev/null; then
    useradd -m -s /bin/bash openstackbot
    echo "✅ User 'openstackbot' created"
else
    echo "ℹ️ User 'openstackbot' already exists"
fi

# Create bot directory
BOT_DIR="/opt/openstack-bot"
echo "📁 Creating bot directory at $BOT_DIR..."
mkdir -p $BOT_DIR
cd $BOT_DIR

# Download or copy bot files (assuming they're in current directory)
echo "📥 Setting up bot files..."
if [ -f "main.py" ]; then
    cp main.py $BOT_DIR/
    cp requirements.txt $BOT_DIR/
    cp config.env $BOT_DIR/
else
    echo "❌ Bot files not found in current directory!"
    echo "Please ensure main.py, requirements.txt, and config.env are present"
    exit 1
fi

# Create Python virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set proper permissions
echo "🔐 Setting permissions..."
chown -R openstackbot:openstackbot $BOT_DIR
chmod +x $BOT_DIR/main.py

# Create systemd service file
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/openstack-bot.service << EOF
[Unit]
Description=OpenStack Telegram Bot
After=network.target

[Service]
Type=simple
User=openstackbot
Group=openstackbot
WorkingDirectory=$BOT_DIR
Environment=PATH=$BOT_DIR/venv/bin
EnvironmentFile=$BOT_DIR/config.env
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation configuration
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/openstack-bot << EOF
$BOT_DIR/openstack_bot.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    su openstackbot openstackbot
}
EOF

# Reload systemd and enable service
echo "🔄 Configuring systemd service..."
systemctl daemon-reload
systemctl enable openstack-bot

# Create helper scripts
echo "🛠️ Creating helper scripts..."

# Start script
cat > $BOT_DIR/start.sh << 'EOF'
#!/bin/bash
sudo systemctl start openstack-bot
sudo systemctl status openstack-bot
EOF

# Stop script
cat > $BOT_DIR/stop.sh << 'EOF'
#!/bin/bash
sudo systemctl stop openstack-bot
sudo systemctl status openstack-bot
EOF

# Status script
cat > $BOT_DIR/status.sh << 'EOF'
#!/bin/bash
echo "=== Service Status ==="
sudo systemctl status openstack-bot

echo -e "\n=== Recent Logs ==="
sudo journalctl -u openstack-bot -n 20 --no-pager

echo -e "\n=== Log File ==="
tail -n 10 /opt/openstack-bot/openstack_bot.log
EOF

# Restart script
cat > $BOT_DIR/restart.sh << 'EOF'
#!/bin/bash
sudo systemctl restart openstack-bot
sudo systemctl status openstack-bot
EOF

# Update script
cat > $BOT_DIR/update.sh << 'EOF'
#!/bin/bash
echo "🔄 Updating OpenStack Bot..."
cd /opt/openstack-bot
sudo systemctl stop openstack-bot

# Backup current config
sudo cp config.env config.env.backup

# Pull latest changes (if using git)
if [ -d ".git" ]; then
    sudo -u openstackbot git pull
fi

# Restore config
sudo cp config.env.backup config.env

# Update dependencies
sudo -u openstackbot /opt/openstack-bot/venv/bin/pip install -r requirements.txt

sudo systemctl start openstack-bot
echo "✅ Bot updated and restarted"
EOF

# Make scripts executable
chmod +x $BOT_DIR/*.sh

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit the configuration file: nano $BOT_DIR/config.env"
echo "2. Add your Telegram Bot Token to the config file"
echo "3. Start the bot: $BOT_DIR/start.sh"
echo ""
echo "🛠️ Available commands:"
echo "• Start bot: $BOT_DIR/start.sh"
echo "• Stop bot: $BOT_DIR/stop.sh"
echo "• Check status: $BOT_DIR/status.sh"
echo "• Restart bot: $BOT_DIR/restart.sh"
echo "• Update bot: $BOT_DIR/update.sh"
echo ""
echo "📝 Logs location: $BOT_DIR/openstack_bot.log"
echo "📊 Service logs: journalctl -u openstack-bot -f"
echo ""
echo "⚠️ Don't forget to:"
echo "1. Create a Telegram bot via @BotFather"
echo "2. Get the bot token and add it to config.env"
echo "3. Configure your firewall if needed"
