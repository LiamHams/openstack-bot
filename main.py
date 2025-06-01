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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import asyncio

# Authorized user IDs - only these users can use the bot
AUTHORIZED_USERS = [YourTelID]  # Add more user IDs as needed

def is_authorized(user_id):
    """Check if user is authorized to use the bot"""
    return user_id in AUTHORIZED_USERS

async def check_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is authorized and send unauthorized message if not"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(
            "❌ You are not authorized to use this bot.\n\n"
            "Please contact @MmdHsn21 for access."
        )
        return False
    return True

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

# Conversation states
SELECT_SERVER, CONFIRM_ACTION = range(2)

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
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
                
            response = requests.get(
                f"{network_url}/v2.0/floatingips",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['floatingips']
            else:
                logger.error(f"Failed to get floating IPs: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting floating IPs: {str(e)}")
            return None
    
    def get_ports(self):
        """Get list of all ports"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
                
            response = requests.get(
                f"{network_url}/v2.0/ports",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['ports']
            else:
                logger.error(f"Failed to get ports: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting ports: {str(e)}")
            return None
    
    def get_public_network_id(self):
        """Get the ID of the public network"""
        try:
            networks = self.get_networks()
            if not networks:
                return None
            
            # Look for a network with router:external=True
            for network in networks:
                if network.get('router:external', False):
                    return network['id']
            
            # If no external network found, return None
            logger.warning("No public network found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting public network ID: {str(e)}")
            return None
    
    def create_port(self, network_id, device_id=None):
        """Create a new port on the specified network"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            port_data = {
                "port": {
                    "network_id": network_id
                }
            }
            
            # If device_id is provided, associate port with the device
            if device_id:
                port_data["port"]["device_id"] = device_id
                port_data["port"]["device_owner"] = "compute:nova"
            
            response = requests.post(
                f"{network_url}/v2.0/ports",
                headers=headers,
                json=port_data
            )
            
            if response.status_code in [201, 200]:
                return response.json()['port']
            else:
                logger.error(f"Failed to create port: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating port: {str(e)}")
            return None
    
    def allocate_floating_ip(self, floating_network_id=None):
        """Allocate a new floating IP"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            # If no network ID provided, try to get the public network
            if not floating_network_id:
                floating_network_id = self.get_public_network_id()
                if not floating_network_id:
                    logger.error("No public network found for floating IP allocation")
                    return None
            
            floatingip_data = {
                "floatingip": {
                    "floating_network_id": floating_network_id
                }
            }
            
            response = requests.post(
                f"{network_url}/v2.0/floatingips",
                headers=headers,
                json=floatingip_data
            )
            
            if response.status_code in [201, 200]:
                return response.json()['floatingip']
            else:
                logger.error(f"Failed to allocate floating IP: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error allocating floating IP: {str(e)}")
            return None
    
    def associate_floating_ip(self, floating_ip_id, port_id):
        """Associate a floating IP with a port"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            update_data = {
                "floatingip": {
                    "port_id": port_id
                }
            }
            
            response = requests.put(
                f"{network_url}/v2.0/floatingips/{floating_ip_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code in [200, 202]:
                return response.json()['floatingip']
            else:
                logger.error(f"Failed to associate floating IP: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error associating floating IP: {str(e)}")
            return None
    
    def disassociate_floating_ip(self, floating_ip_id):
        """Disassociate a floating IP from any port"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            update_data = {
                "floatingip": {
                    "port_id": None
                }
            }
            
            response = requests.put(
                f"{network_url}/v2.0/floatingips/{floating_ip_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code in [200, 202]:
                return response.json()['floatingip']
            else:
                logger.error(f"Failed to disassociate floating IP: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error disassociating floating IP: {str(e)}")
            return None
    
    def delete_floating_ip(self, floating_ip_id):
        """Delete a floating IP"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return False
            
            response = requests.delete(
                f"{network_url}/v2.0/floatingips/{floating_ip_id}",
                headers=headers
            )
            
            if response.status_code in [204, 202]:
                return True
            else:
                logger.error(f"Failed to delete floating IP: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting floating IP: {str(e)}")
            return False
    
    def get_server_ports(self, server_id):
        """Get all ports associated with a server"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            response = requests.get(
                f"{network_url}/v2.0/ports?device_id={server_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['ports']
            else:
                logger.error(f"Failed to get server ports: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting server ports: {str(e)}")
            return None
            
    # New methods for managing fixed IPs
    def add_fixed_ip(self, server_id, network_id):
        """Add a fixed IP to a server from a specific network"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return None
            
            action_data = {
                "addFixedIp": {
                    "networkId": network_id
                }
            }
            
            response = requests.post(
                f"{compute_url}/servers/{server_id}/action",
                headers=headers,
                json=action_data
            )
            
            if response.status_code in [202, 204]:
                return True
            else:
                logger.error(f"Failed to add fixed IP: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding fixed IP: {str(e)}")
            return False
    
    def remove_fixed_ip(self, server_id, ip_address):
        """Remove a fixed IP from a server"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return None
            
            action_data = {
                "removeFixedIp": {
                    "address": ip_address
                }
            }
            
            response = requests.post(
                f"{compute_url}/servers/{server_id}/action",
                headers=headers,
                json=action_data
            )
            
            if response.status_code in [202, 204]:
                return True
            else:
                logger.error(f"Failed to remove fixed IP: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing fixed IP: {str(e)}")
            return False

# Initialize OpenStack API
openstack = OpenStackAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    # Check authorization
    if not await check_authorization(update, context):
        return
    
    # Clear any stored data
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("📊 List Servers", callback_data='list_servers')],
        [InlineKeyboardButton("🌐 List Networks", callback_data='list_networks')],
        [InlineKeyboardButton("🔗 Floating IPs", callback_data='list_floating_ips')],
        [InlineKeyboardButton("➕ Add Floating IP", callback_data='add_floating_ip')],
        [InlineKeyboardButton("🔧 Manage Fixed IPs", callback_data='manage_fixed_ips')],
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
    # Check authorization
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "❌ You are not authorized to use this bot.\n\n"
            "Please contact @MmdHsn21 for access."
        )
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        # Fix: Handle potential invalid callback data
        callback_data = query.data
        
        if callback_data == 'list_servers':
            await list_servers(query, context, page=0)
        elif callback_data.startswith('list_servers_page_'):
            page = int(callback_data.split('_')[-1])
            await list_servers(query, context, page=page)
        elif callback_data == 'list_networks':
            await list_networks(query)
        elif callback_data == 'list_floating_ips':
            await list_floating_ips(query)
        elif callback_data == 'add_floating_ip':
            await add_floating_ip_menu(query, context)
        elif callback_data == 'allocate_floating_ip':
            await allocate_floating_ip(query)
        elif callback_data == 'associate_floating_ip':
            await select_server_for_ip(query, context)
        elif callback_data.startswith('select_server_'):
            server_id = callback_data.split('_')[2]
            await select_floating_ip(query, context, server_id)
        elif callback_data.startswith('select_ip_'):
            parts = callback_data.split('_')
            ip_id = parts[2]
            server_id = parts[3]
            await confirm_associate_ip(query, context, ip_id, server_id)
        elif callback_data.startswith('confirm_associate_'):
            parts = callback_data.split('_')
            ip_id = parts[2]
            server_id = parts[3]
            await do_associate_ip(query, ip_id, server_id)
        elif callback_data.startswith('disassociate_ip_'):
            ip_id = callback_data.split('_')[2]
            await confirm_disassociate_ip(query, context, ip_id)
        elif callback_data.startswith('confirm_disassociate_'):
            ip_id = callback_data.split('_')[2]
            await do_disassociate_ip(query, ip_id)
        elif callback_data.startswith('delete_ip_'):
            ip_id = callback_data.split('_')[2]
            await confirm_delete_ip(query, context, ip_id)
        elif callback_data.startswith('confirm_delete_'):
            ip_id = callback_data.split('_')[2]
            await do_delete_ip(query, ip_id)
        # New handlers for fixed IP management
        elif callback_data == 'manage_fixed_ips':
            await manage_fixed_ips(query, context)
        elif callback_data.startswith('select_server_for_fixed_ip_'):
            server_id = callback_data.split('_')[-1]
            await manage_server_fixed_ips(query, context, server_id)
        elif callback_data.startswith('add_fixed_ip_'):
            server_id = callback_data.split('_')[-1]
            await select_network_for_fixed_ip(query, context, server_id)
        elif callback_data.startswith('select_network_'):
            parts = callback_data.split('_')
            network_id = parts[2]
            server_id = parts[3]
            await confirm_add_fixed_ip(query, context, server_id, network_id)
        elif callback_data.startswith('confirm_add_fixed_ip_'):
            parts = callback_data.split('_')
            server_id = parts[3]
            network_id = parts[4]
            await do_add_fixed_ip(query, server_id, network_id)
        elif callback_data.startswith('remove_fixed_ip_'):
            parts = callback_data.split('_')
            server_id = parts[3]
            safe_ip = parts[4]
            ip_address = safe_ip.replace('_', '.')
            await confirm_remove_fixed_ip(query, context, server_id, ip_address)
        elif callback_data.startswith('confirm_remove_fixed_ip_'):
            parts = callback_data.split('_')
            server_id = parts[4]
            safe_ip = parts[5]
            ip_address = safe_ip.replace('_', '.')
            await do_remove_fixed_ip(query, server_id, ip_address)
        elif callback_data == 'help':
            await show_help(query)
        elif callback_data.startswith('server_'):
            server_id = callback_data.split('_')[1]
            await show_server_details(query, server_id)
        elif callback_data == 'back_to_main':
            await back_to_main(query)
        elif callback_data == 'back_to_servers':
            await list_servers(query, context, page=0)
        elif callback_data == 'back_to_floating_ips':
            await list_floating_ips(query)
        elif callback_data == 'back_to_fixed_ips':
            await manage_fixed_ips(query, context)
        elif callback_data == 'cancel_operation':
            await query.edit_message_text("❌ Operation cancelled.")
            await asyncio.sleep(2)
            await back_to_main(query)
        else:
            logger.warning(f"Unknown callback data: {callback_data}")
            await query.edit_message_text("❌ Invalid operation. Please try again.")
            await asyncio.sleep(2)
            await back_to_main(query)
            
    except Exception as e:
        logger.error(f"Error in button_handler: {str(e)}")
        await query.edit_message_text("❌ An error occurred. Please try again later.")
        await asyncio.sleep(2)
        await back_to_main(query)

async def list_servers(query, context, page=0):
    """List all servers with pagination"""
    try:
        # Clear previous server data to ensure fresh data
        if 'servers' in context.user_data:
            del context.user_data['servers']
            
        # Get servers
        servers = openstack.get_servers()
        if servers is None:  # Fix: Check for None specifically
            await query.edit_message_text(
                "❌ Failed to retrieve servers.\n\n"
                "This could be due to:\n"
                "• API connection issues\n"
                "• Authentication problems\n"
                "• Service unavailability\n\n"
                "Please check the logs for more details."
            )
            return
            
        context.user_data['servers'] = servers
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        # Pagination settings
        servers_per_page = 5
        total_pages = (len(servers) + servers_per_page - 1) // servers_per_page
        
        # Ensure page is within bounds
        page = max(0, min(page, total_pages - 1))
        
        # Get current page servers
        start_idx = page * servers_per_page
        end_idx = min(start_idx + servers_per_page, len(servers))
        current_page_servers = servers[start_idx:end_idx]
        
        text = f"🖥️ *Your Servers:* (Page {page+1}/{total_pages})\n\n"
        keyboard = []
        
        for server in current_page_servers:
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            text += f"{status_emoji} *{server['name']}* - `{server['status']}`\n"
            
            keyboard.append([InlineKeyboardButton(
                f"📋 {server['name']}", 
                callback_data=f'server_{server["id"]}'
            )])
        
        # Add pagination buttons
        pagination_row = []
        if page > 0:
            pagination_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f'list_servers_page_{page-1}'))
        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton("Next ➡️", callback_data=f'list_servers_page_{page+1}'))
        
        if pagination_row:
            keyboard.append(pagination_row)
        
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
        text += f"🆔 *ID:* `{server['id'][:8]}...`\n"
        text += f"🏷️ *Flavor:* `{server['flavor']['id']}`\n"
        text += f"📅 *Created:* `{server['created'][:10]}`\n\n"
        
        # Network information
        text += "🌐 *Networks:*\n"
        for network_name, addresses in server.get('addresses', {}).items():
            text += f"   • *{network_name}:*\n"
            for addr in addresses:
                addr_type = addr.get('OS-EXT-IPS:type', 'unknown')
                text += f"     - `{addr['addr']}` ({addr_type})\n"
        
        # Add buttons for IP management
        keyboard = [
            [InlineKeyboardButton("➕ Add Floating IP", callback_data=f'select_server_{server_id}')],
            [InlineKeyboardButton("🔧 Manage Fixed IPs", callback_data=f'select_server_for_fixed_ip_{server_id}')],
            [InlineKeyboardButton("🔙 Back to Servers", callback_data='back_to_servers')]
        ]
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
            text += f"   ID: `{network['id'][:8]}...`\n\n"
        
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
        
        # If API returns None, show diagnostic message
        if floating_ips is None:
            text = "❌ *Failed to retrieve floating IPs*\n\n"
            text += "This could be due to:\n"
            text += "• API permission issues\n"
            text += "• Network service unavailability\n"
            text += "• API endpoint configuration\n\n"
            text += "Check logs for more details."
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # If API returns empty list
        if not floating_ips:
            text = "📭 *No floating IPs found in your project*\n\n"
            text += "You can allocate a new floating IP using the button below."
            
            keyboard = [
                [InlineKeyboardButton("➕ Allocate New Floating IP", callback_data='allocate_floating_ip')],
                [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # Display floating IPs
        text = "🔗 *Your Floating IPs:*\n\n"
        
        keyboard = []
        
        for fip in floating_ips:
            status_emoji = "🟢" if fip['status'] == 'ACTIVE' else "🔴" if fip['status'] == 'ERROR' else "🟡"
            attached = "📎" if fip.get('fixed_ip_address') else "🔓"
            
            text += f"{status_emoji} {attached} `{fip['floating_ip_address']}`\n"
            
            # Show different information based on attachment status
            if fip.get('fixed_ip_address'):
                text += f"   Attached to: `{fip['fixed_ip_address']}`\n"
                # Add button to disassociate
                keyboard.append([InlineKeyboardButton(
                    f"🔄 Disassociate {fip['floating_ip_address']}",
                    callback_data=f"disassociate_ip_{fip['id']}"
                )])
            else:
                text += f"   Status: `{fip['status']}`\n"
                # Add button to associate
                keyboard.append([InlineKeyboardButton(
                    f"🔄 Associate {fip['floating_ip_address']}",
                    callback_data=f"associate_floating_ip"  # Fix: Changed to general associate menu
                )])
            
            # Add button to delete this IP
            keyboard.append([InlineKeyboardButton(
                f"🗑️ Delete {fip['floating_ip_address']}",
                callback_data=f"delete_ip_{fip['id']}"
            )])
            
            text += "\n"
        
        # Add general management buttons
        keyboard.append([InlineKeyboardButton("➕ Allocate New IP", callback_data='allocate_floating_ip')])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in list_floating_ips: {str(e)}")
        await query.edit_message_text("❌ An error occurred while fetching floating IPs.")

async def add_floating_ip_menu(query, context):
    """Show floating IP management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Allocate New IP", callback_data='allocate_floating_ip')],
        [InlineKeyboardButton("🔄 Associate IP with Server", callback_data='associate_floating_ip')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 *Floating IP Management*\n\n"
        "Choose an action from the options below:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def allocate_floating_ip(query):
    """Allocate a new floating IP"""
    try:
        # Get public network ID
        public_network_id = openstack.get_public_network_id()
        if not public_network_id:
            await query.edit_message_text(
                "❌ Failed to find public network for floating IP allocation.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Allocate floating IP
        result = openstack.allocate_floating_ip(public_network_id)
        if not result:
            await query.edit_message_text(
                "❌ Failed to allocate floating IP.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Floating IP Allocated Successfully*\n\n"
        text += f"IP Address: `{result['floating_ip_address']}`\n"
        text += f"Status: `{result['status']}`\n"
        text += f"ID: `{result['id'][:8]}...`\n\n"
        text += "You can now associate this IP with a server."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Associate with Server", callback_data='associate_floating_ip')],
            [InlineKeyboardButton("🔙 Back to Floating IPs", callback_data='list_floating_ips')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in allocate_floating_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while allocating floating IP.")

async def select_server_for_ip(query, context):
    """Select a server to associate with a floating IP"""
    try:
        # Clear previous server data to ensure fresh data
        if 'servers' in context.user_data:
            del context.user_data['servers']
            
        # Get servers
        servers = openstack.get_servers()
        if servers is None:  # Fix: Check for None specifically
            await query.edit_message_text(
                "❌ Failed to retrieve servers.\n\n"
                "This could be due to:\n"
                "• API connection issues\n"
                "• Authentication problems\n"
                "• Service unavailability\n\n"
                "Please check the logs for more details."
            )
            return
        
        # Store servers in context
        context.user_data['servers'] = servers
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        text = "🖥️ *Select a Server*\n\n"
        text += "Choose a server to associate with a floating IP:"
        
        keyboard = []
        for server in servers:
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {server['name']}",
                callback_data=f"select_server_{server['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data='back_to_floating_ips')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in select_server_for_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving servers.")

async def select_floating_ip(query, context, server_id):
    """Select a floating IP to associate with the server"""
    try:
        # Get floating IPs
        floating_ips = openstack.get_floating_ips()
        if floating_ips is None:
            await query.edit_message_text("❌ Failed to retrieve floating IPs.")
            return
        
        # Filter for unassociated IPs
        unassociated_ips = [ip for ip in floating_ips if not ip.get('port_id')]
        
        if not unassociated_ips:
            text = "📭 *No Available Floating IPs*\n\n"
            text += "You don't have any unassociated floating IPs.\n"
            text += "Would you like to allocate a new one?"
            
            keyboard = [
                [InlineKeyboardButton("➕ Allocate New IP", callback_data='allocate_floating_ip')],
                [InlineKeyboardButton("🔙 Back", callback_data='back_to_floating_ips')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # Get server details for display
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        text = f"🔗 *Select Floating IP for {server['name']}*\n\n"
        text += "Choose a floating IP to associate with this server:"
        
        keyboard = []
        for ip in unassociated_ips:
            keyboard.append([InlineKeyboardButton(
                f"🔓 {ip['floating_ip_address']}",
                callback_data=f"select_ip_{ip['id']}_{server_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data='back_to_floating_ips')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in select_floating_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving floating IPs.")

async def confirm_associate_ip(query, context, ip_id, server_id):
    """Confirm association of floating IP with server"""
    try:
        # Get floating IP details
        floating_ips = openstack.get_floating_ips()
        if floating_ips is None:
            await query.edit_message_text("❌ Failed to retrieve floating IPs.")
            return
        
        floating_ip = None
        for ip in floating_ips:
            if ip['id'] == ip_id:
                floating_ip = ip
                break
        
        if not floating_ip:
            await query.edit_message_text("❌ Floating IP not found.")
            return
        
        # Get server details
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        text = "⚠️ *Confirm Association*\n\n"
        text += f"Are you sure you want to associate floating IP:\n"
        text += f"`{floating_ip['floating_ip_address']}`\n\n"
        text += f"with server:\n"
        text += f"`{server['name']}`?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Associate", callback_data=f"confirm_associate_{ip_id}_{server_id}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data='cancel_operation')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_associate_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while preparing confirmation.")

async def do_associate_ip(query, ip_id, server_id):
    """Associate floating IP with server"""
    try:
        # Get server ports
        ports = openstack.get_server_ports(server_id)
        if not ports:
            # Try to create a port
            public_network_id = openstack.get_public_network_id()
            if not public_network_id:
                await query.edit_message_text("❌ Failed to find public network.")
                return
            
            port = openstack.create_port(public_network_id, server_id)
            if not port:
                await query.edit_message_text(
                    "❌ Failed to create port for server.\n\n"
                    "Please check logs for more details."
                )
                return
            
            port_id = port['id']
        else:
            # Use existing port
            port_id = ports[0]['id']
        
        # Associate floating IP with port
        result = openstack.associate_floating_ip(ip_id, port_id)
        if not result:
            await query.edit_message_text(
                "❌ Failed to associate floating IP with server.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Floating IP Associated Successfully*\n\n"
        text += f"IP Address: `{result['floating_ip_address']}`\n"
        text += f"Fixed IP: `{result.get('fixed_ip_address', 'N/A')}`\n"
        text += f"Status: `{result['status']}`\n\n"
        text += "The IP has been successfully associated with the server."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Floating IPs", callback_data='list_floating_ips')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in do_associate_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while associating floating IP.")

async def confirm_disassociate_ip(query, context, ip_id):
    """Confirm disassociation of floating IP"""
    try:
        # Get floating IP details
        floating_ips = openstack.get_floating_ips()
        if floating_ips is None:
            await query.edit_message_text("❌ Failed to retrieve floating IPs.")
            return
        
        floating_ip = None
        for ip in floating_ips:
            if ip['id'] == ip_id:
                floating_ip = ip
                break
        
        if not floating_ip:
            await query.edit_message_text("❌ Floating IP not found.")
            return
        
        text = "⚠️ *Confirm Disassociation*\n\n"
        text += f"Are you sure you want to disassociate floating IP:\n"
        text += f"`{floating_ip['floating_ip_address']}`\n\n"
        text += f"from its current port?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Disassociate", callback_data=f"confirm_disassociate_{ip_id}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data='cancel_operation')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_disassociate_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while preparing confirmation.")

async def do_disassociate_ip(query, ip_id):
    """Disassociate floating IP"""
    try:
        # Disassociate floating IP
        result = openstack.disassociate_floating_ip(ip_id)
        if not result:
            await query.edit_message_text(
                "❌ Failed to disassociate floating IP.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Floating IP Disassociated Successfully*\n\n"
        text += f"IP Address: `{result['floating_ip_address']}`\n"
        text += f"Status: `{result['status']}`\n\n"
        text += "The IP has been successfully disassociated and is now available."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Floating IPs", callback_data='list_floating_ips')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in do_disassociate_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while disassociating floating IP.")

async def confirm_delete_ip(query, context, ip_id):
    """Confirm deletion of floating IP"""
    try:
        # Get floating IP details
        floating_ips = openstack.get_floating_ips()
        if floating_ips is None:
            await query.edit_message_text("❌ Failed to retrieve floating IPs.")
            return
        
        floating_ip = None
        for ip in floating_ips:
            if ip['id'] == ip_id:
                floating_ip = ip
                break
        
        if not floating_ip:
            await query.edit_message_text("❌ Floating IP not found.")
            return
        
        text = "⚠️ *Confirm Deletion*\n\n"
        text += f"Are you sure you want to delete floating IP:\n"
        text += f"`{floating_ip['floating_ip_address']}`?\n\n"
        text += "This action cannot be undone."
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{ip_id}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data='cancel_operation')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_delete_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while preparing confirmation.")

async def do_delete_ip(query, ip_id):
    """Delete floating IP"""
    try:
        # Delete floating IP
        success = openstack.delete_floating_ip(ip_id)
        if not success:
            await query.edit_message_text(
                "❌ Failed to delete floating IP.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Floating IP Deleted Successfully*\n\n"
        text += "The floating IP has been successfully deleted."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Floating IPs", callback_data='list_floating_ips')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in do_delete_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while deleting floating IP.")

# New functions for fixed IP management
async def manage_fixed_ips(query, context):
    """Show fixed IP management menu"""
    try:
        # Clear previous server data to ensure fresh data
        if 'servers' in context.user_data:
            del context.user_data['servers']
            
        # Get servers
        servers = openstack.get_servers()
        if servers is None:
            await query.edit_message_text("❌ Failed to retrieve servers.")
            return
        
        # Store servers in context
        context.user_data['servers'] = servers
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        text = "🔧 *Fixed IP Management*\n\n"
        text += "Select a server to manage its fixed IPs:"
        
        keyboard = []
        for server in servers:
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {server['name']}",
                callback_data=f"select_server_for_fixed_ip_{server['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in manage_fixed_ips: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving servers.")

async def manage_server_fixed_ips(query, context, server_id):
    """Manage fixed IPs for a specific server"""
    try:
        # Get server details
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        text = f"🔧 *Fixed IPs for {server['name']}*\n\n"
        
        # List current fixed IPs
        text += "Current Fixed IPs:\n"
        has_ips = False
        
        for network_name, addresses in server.get('addresses', {}).items():
            for addr in addresses:
                if addr.get('OS-EXT-IPS:type') == 'fixed':
                    has_ips = True
                    text += f"• `{addr['addr']}` on network *{network_name}*\n"
        
        if not has_ips:
            text += "No fixed IPs found for this server.\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Fixed IP", callback_data=f"add_fixed_ip_{server_id}")],
            [InlineKeyboardButton("🔙 Back to Server List", callback_data='manage_fixed_ips')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]
        
        # Add remove buttons for each IP
        for network_name, addresses in server.get('addresses', {}).items():
            for addr in addresses:
                if addr.get('OS-EXT-IPS:type') == 'fixed':
                    ip_address = addr['addr']
                    # URL-safe encoding for the IP address
                    safe_ip = ip_address.replace('.', '_')
                    keyboard.insert(0, [InlineKeyboardButton(
                        f"🗑️ Remove {ip_address}",
                        callback_data=f"remove_fixed_ip_{server_id}_{safe_ip}"
                    )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in manage_server_fixed_ips: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving server details.")

async def select_network_for_fixed_ip(query, context, server_id):
    """Select a network to add a fixed IP from"""
    try:
        # Get networks
        networks = openstack.get_networks()
        if not networks:
            await query.edit_message_text("❌ Failed to retrieve networks.")
            return
        
        # Filter for internal networks (not external)
        internal_networks = [net for net in networks if not net.get('router:external', False)]
        
        if not internal_networks:
            await query.edit_message_text("❌ No internal networks found for adding fixed IPs.")
            return
        
        # Get server details for display
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        text = f"🌐 *Select Network for {server['name']}*\n\n"
        text += "Choose a network to add a fixed IP from:"
        
        keyboard = []
        for network in internal_networks:
            status_emoji = "🟢" if network['status'] == 'ACTIVE' else "🔴"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {network['name']}",
                callback_data=f"select_network_{network['id']}_{server_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data=f'select_server_for_fixed_ip_{server_id}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in select_network_for_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving networks.")

async def confirm_add_fixed_ip(query, context, server_id, network_id):
    """Confirm adding a fixed IP to a server"""
    try:
        # Get server details
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        # Get network details
        networks = openstack.get_networks()
        network = None
        for n in networks:
            if n['id'] == network_id:
                network = n
                break
        
        if not network:
            await query.edit_message_text("❌ Network not found.")
            return
        
        text = "⚠️ *Confirm Add Fixed IP*\n\n"
        text += f"Are you sure you want to add a fixed IP from network:\n"
        text += f"`{network['name']}`\n\n"
        text += f"to server:\n"
        text += f"`{server['name']}`?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Add IP", callback_data=f"confirm_add_fixed_ip_{server_id}_{network_id}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f'select_server_for_fixed_ip_{server_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_add_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while preparing confirmation.")

async def do_add_fixed_ip(query, server_id, network_id):
    """Add a fixed IP to a server"""
    try:
        # Add fixed IP
        success = openstack.add_fixed_ip(server_id, network_id)
        if not success:
            await query.edit_message_text(
                "❌ Failed to add fixed IP to server.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Fixed IP Added Successfully*\n\n"
        text += "A new fixed IP has been successfully added to the server.\n\n"
        text += "The server will now have an additional IP address from the selected network."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Server IPs", callback_data=f'select_server_for_fixed_ip_{server_id}')],
            [InlineKeyboardButton("🔙 Back to Fixed IP Management", callback_data='manage_fixed_ips')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in do_add_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while adding fixed IP.")

async def confirm_remove_fixed_ip(query, context, server_id, ip_address):
    """Confirm removing a fixed IP from a server"""
    try:
        # Get server details
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            server = openstack.get_server_details(server_id)
            if not server:
                await query.edit_message_text("❌ Failed to retrieve server details.")
                return
        
        text = "⚠️ *Confirm Remove Fixed IP*\n\n"
        text += f"Are you sure you want to remove fixed IP:\n"
        text += f"`{ip_address}`\n\n"
        text += f"from server:\n"
        text += f"`{server['name']}`?\n\n"
        text += "This action cannot be undone."
        
        safe_ip = ip_address.replace('.', '_')
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Remove IP", callback_data=f"confirm_remove_fixed_ip_{server_id}_{safe_ip}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f'select_server_for_fixed_ip_{server_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_remove_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while preparing confirmation.")

async def do_remove_fixed_ip(query, server_id, ip_address):
    """Remove a fixed IP from a server"""
    try:
        # Remove fixed IP
        success = openstack.remove_fixed_ip(server_id, ip_address)
        if not success:
            await query.edit_message_text(
                "❌ Failed to remove fixed IP from server.\n\n"
                "Please check logs for more details."
            )
            return
        
        # Success message
        text = "✅ *Fixed IP Removed Successfully*\n\n"
        text += f"Fixed IP `{ip_address}` has been successfully removed from the server."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Server IPs", callback_data=f'select_server_for_fixed_ip_{server_id}')],
            [InlineKeyboardButton("🔙 Back to Fixed IP Management", callback_data='manage_fixed_ips')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in do_remove_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while removing fixed IP.")

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
• ➕ Add floating IPs to servers
• 🔧 Manage fixed IPs on servers
• 📋 Get detailed server information

*Floating IP Management:*
• Allocate new floating IPs
• Associate IPs with servers
• Disassociate IPs from servers
• Delete floating IPs

*Fixed IP Management:*
• Add fixed IPs to servers from networks
• Remove fixed IPs from servers
• View current IP assignments

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
        [InlineKeyboardButton("➕ Add Floating IP", callback_data='add_floating_ip')],
        [InlineKeyboardButton("🔧 Manage Fixed IPs", callback_data='manage_fixed_ips')],
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
    # Check authorization
    if not await check_authorization(update, context):
        return
    
    try:
        # Test OpenStack connection
        if openstack.authenticate():
            status_text = "✅ *Bot Status: Online*\n✅ *OpenStack API: Connected*"
            
            # Check services
            services_text = "\n\n*Available Services:*\n"
            for service_type, url in openstack.service_catalog.items():
                services_text += f"• `{service_type}`: ✅\n"
            
            status_text += services_text
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
        logger.info(f"Available services: {list(openstack.service_catalog.keys())}")
    else:
        logger.error("❌ OpenStack connection failed!")
    
    # Start the bot
    logger.info("Starting OpenStack Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
