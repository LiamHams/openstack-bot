#!/usr/bin/env python3
"""
OpenStack Telegram Bot
A Telegram bot for monitoring and managing OpenStack VPS instances
"""

import os
import logging
import json
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('openstack_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenStackAPI:
    def __init__(self):
        self.auth_url = os.getenv('OS_AUTH_URL', 'http://cloud.sc1.awdaz.com:5000')
        self.username = os.getenv('OS_USERNAME', 'hs2')
        self.password = os.getenv('OS_PASSWORD', 'yECSb')
        self.project_id = os.getenv('OS_PROJECT_ID', '69552d73cbe27df079ef7a0c9e')
        self.project_name = os.getenv('OS_PROJECT_NAME', 'Acct #1776')
        self.user_domain_name = os.getenv('OS_USER_DOMAIN_NAME', 'Default')
        self.project_domain_id = os.getenv('OS_PROJECT_DOMAIN_ID', 'default')
        
        self.token = None
        self.token_expires = None
        self.service_catalog = {}
        
    def authenticate(self):
        """Authenticate with OpenStack and get token"""
        try:
            auth_data = {
                "auth": {
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {
                                "name": self.username,
                                "domain": {"name": self.user_domain_name},
                                "password": self.password
                            }
                        }
                    },
                    "scope": {
                        "project": {
                            "id": self.project_id,
                            "domain": {"id": self.project_domain_id}
                        }
                    }
                }
            }
            
            response = requests.post(
                f"{self.auth_url}/v3/auth/tokens",
                json=auth_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                self.token = response.headers.get('X-Subject-Token')
                token_data = response.json()
                
                # Parse token expiration - ensure timezone awareness
                expires_at = token_data['token']['expires_at']
                # Convert to timezone-aware datetime
                self.token_expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                # Store service catalog
                for service in token_data['token']['catalog']:
                    service_type = service['type']
                    for endpoint in service['endpoints']:
                        if endpoint['interface'] == 'public':
                            self.service_catalog[service_type] = endpoint['url']
                            break
                
                logger.info("Successfully authenticated with OpenStack")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def is_token_valid(self):
        """Check if current token is still valid"""
        if not self.token or not self.token_expires:
            return False
        
        # Ensure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)
        return now < self.token_expires - timedelta(minutes=5)
    
    def get_headers(self):
        """Get headers with valid token"""
        if not self.is_token_valid():
            if not self.authenticate():
                return None
        return {"X-Auth-Token": self.token, "Content-Type": "application/json"}
    
    def get_servers(self):
        """Get list of all servers"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return None
                
            response = requests.get(
                f"{compute_url}/servers/detail",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['servers']
            else:
                logger.error(f"Failed to get servers: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting servers: {str(e)}")
            return None
    
    def get_server_details(self, server_id):
        """Get detailed information about a specific server"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            response = requests.get(
                f"{compute_url}/servers/{server_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['server']
            else:
                logger.error(f"Failed to get server details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting server details: {str(e)}")
            return None
    
    def get_networks(self):
        """Get list of all networks"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
                
            response = requests.get(
                f"{network_url}/v2.0/networks",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['networks']
            else:
                logger.error(f"Failed to get networks: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting networks: {str(e)}")
            return None
    
    def get_floating_ips(self):
        """Get list of floating IPs"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            response = requests.get(
                f"{network_url}/v2.0/floatingips",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['floatingips']
            else:
                logger.error(f"Failed to get floating IPs: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting floating IPs: {str(e)}")
            return None

# Initialize OpenStack API
openstack = OpenStackAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    keyboard = [
        [InlineKeyboardButton("📊 List Servers", callback_data='list_servers')],
        [InlineKeyboardButton("🌐 List Networks", callback_data='list_networks')],
        [InlineKeyboardButton("🔗 Floating IPs", callback_data='list_floating_ips')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 *OpenStack Management Bot*

Welcome! I can help you monitor and manage your OpenStack VPS instances.

Choose an option from the menu below:
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'list_servers':
        await list_servers(query)
    elif query.data == 'list_networks':
        await list_networks(query)
    elif query.data == 'list_floating_ips':
        await list_floating_ips(query)
    elif query.data == 'help':
        await show_help(query)
    elif query.data.startswith('server_'):
        server_id = query.data.split('_')[1]
        await show_server_details(query, server_id)
    elif query.data == 'back_to_main':
        await back_to_main(query)

async def list_servers(query):
    """List all servers"""
    try:
        servers = openstack.get_servers()
        if not servers:
            await query.edit_message_text("❌ Failed to retrieve servers. Please check the logs.")
            return
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        text = "🖥️ *Your Servers:*\n\n"
        keyboard = []
        
        for server in servers:
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            text += f"{status_emoji} *{server['name']}*\n"
            text += f"   Status: `{server['status']}`\n"
            text += f"   ID: `{server['id'][:8]}...`\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"📋 {server['name']}", 
                callback_data=f'server_{server["id"]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in list_servers: {str(e)}")
        await query.edit_message_text("❌ An error occurred while fetching servers.")

async def show_server_details(query, server_id):
    """Show detailed information about a server"""
    try:
        server = openstack.get_server_details(server_id)
        if not server:
            await query.edit_message_text("❌ Failed to retrieve server details.")
            return
        
        # Format server details
        text = f"🖥️ *Server Details: {server['name']}*\n\n"
        text += f"📊 *Status:* `{server['status']}`\n"
        text += f"🆔 *ID:* `{server['id']}`\n"
        text += f"🏷️ *Flavor:* `{server['flavor']['id']}`\n"
        text += f"💿 *Image:* `{server.get('image', {}).get('id', 'N/A')}`\n"
        text += f"📅 *Created:* `{server['created'][:19]}`\n"
        text += f"🔄 *Updated:* `{server['updated'][:19]}`\n\n"
        
        # Network information
        text += "🌐 *Networks:*\n"
        for network_name, addresses in server.get('addresses', {}).items():
            text += f"   • *{network_name}:*\n"
            for addr in addresses:
                addr_type = addr.get('OS-EXT-IPS:type', 'unknown')
                text += f"     - {addr['addr']} ({addr_type})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Servers", callback_data='list_servers')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in show_server_details: {str(e)}")
        await query.edit_message_text("❌ An error occurred while fetching server details.")

async def list_networks(query):
    """List all networks"""
    try:
        networks = openstack.get_networks()
        if not networks:
            await query.edit_message_text("❌ Failed to retrieve networks.")
            return
        
        text = "🌐 *Your Networks:*\n\n"
        
        for network in networks:
            status_emoji = "🟢" if network['status'] == 'ACTIVE' else "🔴"
            external = "🌍" if network.get('router:external', False) else "🏠"
            
            text += f"{status_emoji} {external} *{network['name']}*\n"
            text += f"   Status: `{network['status']}`\n"
            text += f"   ID: `{network['id'][:8]}...`\n"
            text += f"   Shared: `{network.get('shared', False)}`\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in list_networks: {str(e)}")
        await query.edit_message_text("❌ An error occurred while fetching networks.")

async def list_floating_ips(query):
    """List all floating IPs"""
    try:
        floating_ips = openstack.get_floating_ips()
        if not floating_ips:
            await query.edit_message_text("❌ Failed to retrieve floating IPs.")
            return
        
        if not floating_ips:
            await query.edit_message_text("📭 No floating IPs found in your project.")
            return
        
        text = "🔗 *Your Floating IPs:*\n\n"
        
        for fip in floating_ips:
            status_emoji = "🟢" if fip['status'] == 'ACTIVE' else "🔴" if fip['status'] == 'ERROR' else "🟡"
            attached = "📎" if fip.get('fixed_ip_address') else "🔓"
            
            text += f"{status_emoji} {attached} `{fip['floating_ip_address']}`\n"
            text += f"   Status: `{fip['status']}`\n"
            if fip.get('fixed_ip_address'):
                text += f"   Attached to: `{fip['fixed_ip_address']}`\n"
            text += f"   Network: `{fip.get('floating_network_id', 'N/A')[:8]}...`\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in list_floating_ips: {str(e)}")
        await query.edit_message_text("❌ An error occurred while fetching floating IPs.")

async def show_help(query):
    """Show help information"""
    help_text = """
ℹ️ *OpenStack Bot Help*

*Available Commands:*
• `/start` - Show main menu
• `/status` - Check bot status

*Features:*
• 📊 View all your VPS servers
• 🌐 List available networks
• 🔗 Monitor floating IP addresses
• 📋 Get detailed server information

*Status Indicators:*
• 🟢 Active/Available
• 🔴 Error/Down
• 🟡 Building/Transitioning
• 🌍 External network
• 🏠 Internal network
• 📎 Attached floating IP
• 🔓 Unattached floating IP

*Need help?* Contact your system administrator.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def back_to_main(query):
    """Return to main menu"""
    keyboard = [
        [InlineKeyboardButton("📊 List Servers", callback_data='list_servers')],
        [InlineKeyboardButton("🌐 List Networks", callback_data='list_networks')],
        [InlineKeyboardButton("🔗 Floating IPs", callback_data='list_floating_ips')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 *OpenStack Management Bot*

Welcome! I can help you monitor and manage your OpenStack VPS instances.

Choose an option from the menu below:
    """
    
    await query.edit_message_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot and OpenStack connection status"""
    try:
        # Test OpenStack connection
        if openstack.authenticate():
            status_text = "✅ *Bot Status: Online*\n✅ *OpenStack API: Connected*"
        else:
            status_text = "✅ *Bot Status: Online*\n❌ *OpenStack API: Connection Failed*"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")
        await update.message.reply_text("❌ Error checking status.")

def main():
    """Main function to run the bot"""
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Test OpenStack connection on startup
    logger.info("Testing OpenStack connection...")
    if openstack.authenticate():
        logger.info("✅ OpenStack connection successful!")
    else:
        logger.error("❌ OpenStack connection failed!")
    
    # Start the bot
    logger.info("Starting OpenStack Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
