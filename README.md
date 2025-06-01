# OpenStack Telegram Bot

A comprehensive Telegram bot for monitoring and managing OpenStack VPS instances. This bot provides an easy-to-use interface for viewing server details, network information, and floating IP addresses directly from Telegram.

## 🚀 Features

- **Server Management**: View all VPS instances with real-time status and pagination
- **Network Monitoring**: List and monitor network configurations
- **Floating IP Management**: Complete lifecycle management of floating IPs
  - Allocate new floating IPs
  - Associate IPs with servers
  - Disassociate IPs from servers
  - Delete floating IPs
- **Real-time Status**: Live status updates with emoji indicators
- **Detailed Information**: Get comprehensive details about any server
- **Secure Authentication**: Uses OpenStack Identity API v3
- **User Authorization**: Restricts access to authorized Telegram users only
- **Logging System**: Comprehensive logging for debugging and monitoring
- **Easy Deployment**: One-script installation on Ubuntu 22.04
- **Auto-Updates**: Automatic updates from GitHub repository
- **CLI Management**: Command-line interface for bot management

## 📋 Prerequisites

- Ubuntu 22.04 LTS server
- Root access to the server
- OpenStack credentials and API access
- Telegram Bot Token (from @BotFather)
- Authorized Telegram user ID

## 🛠️ Installation

### Quick Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LiamHams/openstack-bot.git
   cd openstack-bot
