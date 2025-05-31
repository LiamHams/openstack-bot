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
CURRENT_DIR=$(pwd)

echo "📁 Setting up bot directory at $BOT_DIR..."

# Create directory if it doesn't exist
mkdir -p $BOT_DIR

# Check if we're already in the target directory
if [ "$CURRENT_DIR" = "$BOT_DIR" ]; then
    echo "ℹ️ Already in target directory, files are in place"
else
    echo "📥 Copying bot files from $CURRENT_DIR to $BOT_DIR..."
    
    # Copy files only if they exist and are different
    for file in main.py requirements.txt config.env; do
        if [ -f "$CURRENT_DIR/$file" ]; then
            if [ ! -f "$BOT_DIR/$file" ] || ! cmp -s "$CURRENT_DIR/$file" "$BOT_DIR/$file"; then
                cp "$CURRENT_DIR/$file" "$BOT_DIR/"
                echo "✅ Copied $file"
            else
                echo "ℹ️ $file already up to date"
            fi
        else
            echo "❌ $file not found in current directory!"
            exit 1
        fi
    done
fi

# Change to bot directory
cd $BOT_DIR

# Create Python virtual environment
echo "🔧 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📚 Installing Python dependencies..."
source venv/bin/activate
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
if [ -f /opt/openstack-bot/openstack_bot.log ]; then
    tail -n 10 /opt/openstack-bot/openstack_bot.log
else
    echo "Log file not found yet"
fi
EOF

# Restart script
cat > $BOT_DIR/restart.sh << 'EOF'
#!/bin/bash
sudo systemctl restart openstack-bot
sudo systemctl status openstack-bot
EOF

# Update script with GitHub integration
cat > $BOT_DIR/update.sh << 'EOF'
#!/bin/bash

echo "🔄 OpenStack Bot Update Script"
echo "=============================="

BOT_DIR="/opt/openstack-bot"
REPO_URL="https://github.com/LiamsHams/openstack-bot.git"
BACKUP_DIR="$BOT_DIR/backup_$(date +%Y%m%d_%H%M%S)"

# Function to print colored output
print_status() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

cd $BOT_DIR

print_status "Stopping OpenStack bot service..."
systemctl stop openstack-bot

# Create backup directory
print_status "Creating backup at $BACKUP_DIR..."
mkdir -p $BACKUP_DIR

# Backup important files
if [ -f "config.env" ]; then
    cp config.env $BACKUP_DIR/
    print_success "Configuration backed up"
fi

if [ -f "openstack_bot.log" ]; then
    cp openstack_bot.log $BACKUP_DIR/
    print_success "Logs backed up"
fi

# Check if this is a git repository
if [ -d ".git" ]; then
    print_status "Updating from Git repository..."
    
    # Stash any local changes to preserve config
    sudo -u openstackbot git stash push -m "Auto-stash before update $(date)"
    
    # Pull latest changes
    if sudo -u openstackbot git pull origin main; then
        print_success "Successfully pulled latest changes from GitHub"
    else
        print_warning "Git pull failed, trying to reset and pull..."
        sudo -u openstackbot git fetch origin
        sudo -u openstackbot git reset --hard origin/main
        if [ $? -eq 0 ]; then
            print_success "Successfully reset to latest version"
        else
            print_error "Failed to update from Git. Restoring backup..."
            cp $BACKUP_DIR/config.env ./
            systemctl start openstack-bot
            exit 1
        fi
    fi
else
    print_status "Not a git repository. Cloning fresh copy..."
    
    # Move current directory
    mv $BOT_DIR ${BOT_DIR}_old_$(date +%Y%m%d_%H%M%S)
    
    # Clone fresh repository
    if git clone $REPO_URL $BOT_DIR; then
        print_success "Successfully cloned repository"
        
        # Set proper ownership
        chown -R openstackbot:openstackbot $BOT_DIR
        cd $BOT_DIR
    else
        print_error "Failed to clone repository. Restoring old version..."
        mv ${BOT_DIR}_old_* $BOT_DIR
        cd $BOT_DIR
        systemctl start openstack-bot
        exit 1
    fi
fi

# Restore configuration
if [ -f "$BACKUP_DIR/config.env" ]; then
    cp $BACKUP_DIR/config.env ./
    print_success "Configuration restored"
else
    print_warning "No configuration backup found"
fi

# Update Python dependencies
print_status "Updating Python dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade pip
    if pip install -r requirements.txt; then
        print_success "Dependencies updated successfully"
    else
        print_error "Failed to update dependencies"
        exit 1
    fi
else
    print_status "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Set proper permissions
print_status "Setting proper permissions..."
chown -R openstackbot:openstackbot $BOT_DIR
chmod +x $BOT_DIR/main.py
chmod +x $BOT_DIR/*.sh

# Reload systemd in case service file changed
print_status "Reloading systemd configuration..."
systemctl daemon-reload

# Start the service
print_status "Starting OpenStack bot service..."
if systemctl start openstack-bot; then
    print_success "Bot service started successfully"
else
    print_error "Failed to start bot service"
    exit 1
fi

# Check service status
sleep 3
if systemctl is-active --quiet openstack-bot; then
    print_success "Bot is running successfully!"
    echo ""
    echo "📊 Service Status:"
    systemctl status openstack-bot --no-pager -l
else
    print_error "Bot failed to start properly"
    echo ""
    echo "📊 Service Status:"
    systemctl status openstack-bot --no-pager -l
    echo ""
    echo "📝 Recent logs:"
    journalctl -u openstack-bot -n 20 --no-pager
fi

echo ""
print_success "Update completed!"
echo "📁 Backup location: $BACKUP_DIR"
echo "📝 To view logs: journalctl -u openstack-bot -f"
echo "🔧 To check status: $BOT_DIR/status.sh"

EOF

# Auto-update script with scheduling
cat > $BOT_DIR/auto-update.sh << 'EOF'
#!/bin/bash

# Auto-update script that can be run via cron
# Usage: ./auto-update.sh [--force] [--check-only]

BOT_DIR="/opt/openstack-bot"
REPO_URL="https://github.com/LiamsHams/openstack-bot.git"
LOG_FILE="$BOT_DIR/auto-update.log"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_message "ERROR: Please run this script as root (use sudo)"
    exit 1
fi

cd $BOT_DIR

# Parse arguments
FORCE_UPDATE=false
CHECK_ONLY=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE_UPDATE=true
            ;;
        --check-only)
            CHECK_ONLY=true
            ;;
    esac
done

log_message "Starting auto-update check..."

# Check if git repository exists
if [ ! -d ".git" ]; then
    log_message "WARNING: Not a git repository. Run manual update first."
    exit 1
fi

# Fetch latest changes
sudo -u openstackbot git fetch origin

# Check if updates are available
LOCAL_COMMIT=$(sudo -u openstackbot git rev-parse HEAD)
REMOTE_COMMIT=$(sudo -u openstackbot git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] && [ "$FORCE_UPDATE" = false ]; then
    log_message "INFO: Bot is already up to date"
    if [ "$CHECK_ONLY" = true ]; then
        echo "No updates available"
        exit 0
    fi
else
    if [ "$CHECK_ONLY" = true ]; then
        echo "Updates available"
        log_message "INFO: Updates available but check-only mode enabled"
        exit 0
    fi
    
    log_message "INFO: Updates available. Starting update process..."
    
    # Run the update script
    if $BOT_DIR/update.sh >> $LOG_FILE 2>&1; then
        log_message "SUCCESS: Auto-update completed successfully"
    else
        log_message "ERROR: Auto-update failed"
        exit 1
    fi
fi

log_message "Auto-update check completed"
EOF

# Setup cron script
cat > $BOT_DIR/setup-cron.sh << 'EOF'
#!/bin/bash

echo "🕐 Setting up automatic updates with cron"
echo "========================================"

BOT_DIR="/opt/openstack-bot"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

echo "Select update frequency:"
echo "1) Daily at 3 AM"
echo "2) Weekly on Sunday at 3 AM"
echo "3) Custom schedule"
echo "4) Remove automatic updates"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 3 * * *"
        DESCRIPTION="daily at 3 AM"
        ;;
    2)
        CRON_SCHEDULE="0 3 * * 0"
        DESCRIPTION="weekly on Sunday at 3 AM"
        ;;
    3)
        echo ""
        echo "Enter cron schedule (format: minute hour day month weekday)"
        echo "Example: '0 3 * * *' for daily at 3 AM"
        read -p "Cron schedule: " CRON_SCHEDULE
        DESCRIPTION="custom schedule: $CRON_SCHEDULE"
        ;;
    4)
        # Remove existing cron job
        (crontab -l 2>/dev/null | grep -v "$BOT_DIR/auto-update.sh") | crontab -
        echo "✅ Automatic updates removed"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Add cron job
(crontab -l 2>/dev/null | grep -v "$BOT_DIR/auto-update.sh"; echo "$CRON_SCHEDULE $BOT_DIR/auto-update.sh") | crontab -

echo "✅ Automatic updates configured for $DESCRIPTION"
echo ""
echo "📝 Current cron jobs:"
crontab -l | grep -E "(openstack|auto-update)" || echo "No related cron jobs found"
echo ""
echo "🔧 To check update logs: tail -f $BOT_DIR/auto-update.log"
echo "🔧 To test auto-update: $BOT_DIR/auto-update.sh --check-only"

EOF

# Make scripts executable
chmod +x $BOT_DIR/*.sh

# Check if config needs to be updated
echo ""
echo "🔧 Checking configuration..."
if grep -q "your_telegram_bot_token_here" $BOT_DIR/config.env; then
    echo "⚠️ Configuration needs to be updated!"
    CONFIG_NEEDS_UPDATE=true
else
    echo "ℹ️ Configuration appears to be set"
    CONFIG_NEEDS_UPDATE=false
fi

echo ""
echo "✅ Installation completed successfully!"
echo ""

if [ "$CONFIG_NEEDS_UPDATE" = true ]; then
    echo "📋 IMPORTANT - Next steps:"
    echo "1. Edit the configuration file: nano $BOT_DIR/config.env"
    echo "2. Replace 'your_telegram_bot_token_here' with your actual bot token"
    echo "3. Start the bot: $BOT_DIR/start.sh"
else
    echo "📋 Next steps:"
    echo "1. Review the configuration file: nano $BOT_DIR/config.env"
    echo "2. Start the bot: $BOT_DIR/start.sh"
fi

echo ""
echo "🛠️ Available commands:"
echo "• Start bot: $BOT_DIR/start.sh"
echo "• Stop bot: $BOT_DIR/stop.sh"
echo "• Check status: $BOT_DIR/status.sh"
echo "• Restart bot: $BOT_DIR/restart.sh"
echo "• Update bot: $BOT_DIR/update.sh"
echo "• Setup Auto-Update: $BOT_DIR/setup-cron.sh"
echo ""
echo "📝 Logs location: $BOT_DIR/openstack_bot.log"
echo "📊 Service logs: journalctl -u openstack-bot -f"
echo "⚙️ Auto-Update logs: $BOT_DIR/auto-update.log"
echo ""
echo "⚠️ Don't forget to:"
echo "1. Create a Telegram bot via @BotFather"
echo "2. Get the bot token and add it to config.env"
echo "3. Configure your firewall if needed"
echo ""
echo "🚀 To start the bot now, run: $BOT_DIR/start.sh"
