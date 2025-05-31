# OpenStack Bot

## 📖 Overview

This bot automates various OpenStack management tasks, providing a streamlined interface for common operations.

## ✨ Features

- **Instance Management**: Create, delete, and manage OpenStack instances.
- **Volume Management**: Create, attach, and detach volumes.
- **Network Management**: Create and manage networks, subnets, and routers.
- **Security Group Management**: Create and manage security groups and rules.
- **Image Management**: Upload, download, and manage images.
- **Flavor Management**: Create and manage flavors.
- **Keypair Management**: Create and manage keypairs.
- **Floating IP Management**: Allocate and associate floating IPs.
- **Snapshot Management**: Create and manage snapshots.
- **Orchestration**: Deploy and manage stacks using Heat templates.
- **Monitoring**: Monitor OpenStack resources and send alerts.
- **Reporting**: Generate reports on OpenStack usage and costs.

## 🚀 Getting Started

### Prerequisites

- Python 3.6+
- OpenStack CLI tools
- OpenStack credentials

### Installation

1. Clone the repository:
   \`\`\`bash
   git clone https://github.com/your-username/openstack-bot.git
   cd openstack-bot
   \`\`\`

2. Install the dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. Configure the bot:
   - Copy `config.env.example` to `config.env`
   - Update the `config.env` file with your OpenStack credentials and settings

4. Run the bot:
   \`\`\`bash
   python bot.py
   \`\`\`

## ⚙️ Configuration

### config.env

The `config.env` file contains the following settings:

- `OS_USERNAME`: Your OpenStack username
- `OS_PASSWORD`: Your OpenStack password
- `OS_PROJECT_NAME`: Your OpenStack project name
- `OS_AUTH_URL`: Your OpenStack authentication URL
- `OS_REGION_NAME`: Your OpenStack region name
- `BOT_TOKEN`: Your bot token
- `BOT_PREFIX`: Your bot prefix
- `ADMIN_USER_ID`: Your admin user ID

## 💻 Usage

### Commands

- `!help`: Show available commands
- `!instance-create <name> <flavor> <image>`: Create an instance
- `!instance-delete <name>`: Delete an instance
- `!volume-create <name> <size>`: Create a volume
- `!volume-attach <name> <instance>`: Attach a volume to an instance
- `!volume-detach <name> <instance>`: Detach a volume from an instance
- `!network-create <name>`: Create a network
- `!network-delete <name>`: Delete a network
- `!security-group-create <name>`: Create a security group
- `!security-group-delete <name>`: Delete a security group
- `!image-upload <name> <url>`: Upload an image
- `!image-delete <name>`: Delete an image
- `!flavor-create <name> <ram> <vcpus> <disk>`: Create a flavor
- `!flavor-delete <name>`: Delete a flavor
- `!keypair-create <name>`: Create a keypair
- `!keypair-delete <name>`: Delete a keypair
- `!floating-ip-allocate`: Allocate a floating IP
- `!floating-ip-associate <ip> <instance>`: Associate a floating IP with an instance
- `!snapshot-create <name> <volume>`: Create a snapshot
- `!snapshot-delete <name>`: Delete a snapshot
- `!stack-create <name> <template>`: Create a stack
- `!stack-delete <name>`: Delete a stack
- `!monitor-resource <resource> <metric>`: Monitor a resource
- `!report-generate <type>`: Generate a report

## 🔧 Management

### Starting the Bot
\`\`\`bash
python bot.py
\`\`\`

### Stopping the Bot
\`\`\`bash
# Ctrl+C in the terminal where the bot is running
\`\`\`

### Restarting the Bot
\`\`\`bash
# Stop the bot and then start it again
python bot.py
\`\`\`

## 🔄 Automatic Updates

The bot includes comprehensive update mechanisms to keep your installation current with the latest features and security updates.

### Update Scripts

#### Manual Update
\`\`\`bash
# Update to latest version from GitHub
/opt/openstack-bot/update.sh
\`\`\`

#### Auto-Update with Scheduling
\`\`\`bash
# Check for updates without applying them
/opt/openstack-bot/auto-update.sh --check-only

# Force update even if no changes detected
/opt/openstack-bot/auto-update.sh --force

# Setup automatic updates with cron
/opt/openstack-bot/setup-cron.sh
\`\`\`

### Setting Up Automatic Updates

1. **Configure automatic updates:**
   \`\`\`bash
   sudo /opt/openstack-bot/setup-cron.sh
   \`\`\`

2. **Choose update frequency:**
   - Daily at 3 AM
   - Weekly on Sunday at 3 AM  
   - Custom schedule
   - Remove automatic updates

3. **Monitor update logs:**
   \`\`\`bash
   tail -f /opt/openstack-bot/auto-update.log
   \`\`\`

### Update Process

The update system:

1. **Backs up configuration** - Your `config.env` is always preserved
2. **Stops the service** - Ensures clean update process
3. **Pulls latest code** - Gets updates from GitHub repository
4. **Restores configuration** - Your settings remain intact
5. **Updates dependencies** - Installs any new Python packages
6. **Restarts service** - Bot comes back online with new features

### Safety Features

- **Configuration preservation** - `config.env` is never overwritten
- **Automatic backups** - Creates timestamped backups before updates
- **Rollback capability** - Can restore previous version if update fails
- **Service monitoring** - Verifies bot starts successfully after update
- **Detailed logging** - All update activities are logged

### Update Logs

Monitor update activities:

\`\`\`bash
# View auto-update logs
tail -f /opt/openstack-bot/auto-update.log

# View service logs during update
journalctl -u openstack-bot -f

# Check last update status
/opt/openstack-bot/status.sh
\`\`\`
