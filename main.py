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
    
    def get_subnets(self):
        """Get list of all subnets"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
                
            response = requests.get(
                f"{network_url}/v2.0/subnets",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['subnets']
            else:
                logger.error(f"Failed to get subnets: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting subnets: {str(e)}")
            return None
    
    def get_routers(self):
        """Get list of all routers"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
                
            response = requests.get(
                f"{network_url}/v2.0/routers",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['routers']
            else:
                logger.error(f"Failed to get routers: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting routers: {str(e)}")
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
    
    def get_public_networks(self):
        """Get all public/external networks (including public-167 and public-431)"""
        try:
            networks = self.get_networks()
            if not networks:
                return []
            
            # Look for networks with router:external=True or names containing 'public'
            public_networks = []
            for network in networks:
                if (network.get('router:external', False) or 
                    'public' in network.get('name', '').lower()):
                    public_networks.append(network)
                    logger.info(f"Found public network: {network['name']} ({network['id']})")
            
            return public_networks
            
        except Exception as e:
            logger.error(f"Error getting public networks: {str(e)}")
            return []
    
    def get_public_network_id(self):
        """Get the ID of a public network (prefer public-167 or public-431)"""
        try:
            public_networks = self.get_public_networks()
            if not public_networks:
                logger.warning("No public networks found")
                return None
            
            # Prefer networks with specific names
            for network in public_networks:
                name = network.get('name', '').lower()
                if 'public-167' in name or 'public-431' in name:
                    logger.info(f"Using preferred public network: {network['name']}")
                    return network['id']
            
            # Use the first available public network
            network = public_networks[0]
            logger.info(f"Using public network: {network['name']}")
            return network['id']
            
        except Exception as e:
            logger.error(f"Error getting public network ID: {str(e)}")
            return None
    
    def find_networks_with_external_gateway(self):
        """Find networks that have external gateway access through routers"""
        try:
            routers = self.get_routers()
            subnets = self.get_subnets()
            
            if not routers or not subnets:
                logger.warning("Could not get routers or subnets")
                return []
            
            # Find routers with external gateways
            external_routers = []
            for router in routers:
                if router.get('external_gateway_info') and router['external_gateway_info'].get('network_id'):
                    external_routers.append(router['id'])
                    logger.info(f"Found router with external gateway: {router['name']} ({router['id']})")
            
            if not external_routers:
                logger.warning("No routers with external gateways found")
                return []
            
            # Find networks connected to these routers through subnets
            connected_networks = set()
            for subnet in subnets:
                if subnet.get('gateway_ip'):
                    # Check if this subnet is connected to any external router
                    # We need to check router interfaces for this
                    network_id = subnet['network_id']
                    if network_id not in connected_networks:
                        # For now, assume subnets with gateways are connected to routers
                        connected_networks.add(network_id)
                        logger.info(f"Found network with potential external access: {network_id}")
            
            return list(connected_networks)
            
        except Exception as e:
            logger.error(f"Error finding networks with external gateway: {str(e)}")
            return []
    
    def create_network(self, name, cidr="192.168.100.0/24"):
        """Create a new private network with subnet"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return None
            
            # Create network
            network_data = {
                "network": {
                    "name": name,
                    "admin_state_up": True
                }
            }
            
            response = requests.post(
                f"{network_url}/v2.0/networks",
                headers=headers,
                json=network_data
            )
            
            if response.status_code not in [201, 200]:
                logger.error(f"Failed to create network: {response.status_code} - {response.text}")
                return None
            
            network = response.json()['network']
            logger.info(f"Created network: {network['name']} ({network['id']})")
            
            # Create subnet
            subnet_data = {
                "subnet": {
                    "name": f"{name}-subnet",
                    "network_id": network['id'],
                    "ip_version": 4,
                    "cidr": cidr,
                    "enable_dhcp": True
                }
            }
            
            response = requests.post(
                f"{network_url}/v2.0/subnets",
                headers=headers,
                json=subnet_data
            )
            
            if response.status_code not in [201, 200]:
                logger.error(f"Failed to create subnet: {response.status_code} - {response.text}")
                return network  # Return network even if subnet creation fails
            
            subnet = response.json()['subnet']
            logger.info(f"Created subnet: {subnet['name']} ({subnet['id']})")
            
            return network
            
        except Exception as e:
            logger.error(f"Error creating network: {str(e)}")
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
            
            # If no network ID provided, try to get a public network
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
                result = response.json()['floatingip']
                logger.info(f"Allocated floating IP: {result['floating_ip_address']}")
                return result
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
                result = response.json()['floatingip']
                logger.info(f"Associated floating IP {result['floating_ip_address']} with port {port_id}")
                return result
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
    
    def get_server_interfaces(self, server_id):
        """Get all network interfaces attached to a server"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return None
            
            response = requests.get(
                f"{compute_url}/servers/{server_id}/os-interface",
                headers=headers
            )
            
            if response.status_code == 200:
                interfaces = response.json()['interfaceAttachments']
                logger.info(f"Found {len(interfaces)} interfaces for server {server_id}")
                for interface in interfaces:
                    logger.info(f"Interface {interface['port_id']}: fixed_ips={interface.get('fixed_ips', [])}")
                return interfaces
            else:
                logger.error(f"Failed to get server interfaces: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting server interfaces: {str(e)}")
            return None
    
    def get_suitable_interface_for_floating_ip(self, server_id):
        """Get a suitable interface for floating IP association (must have external gateway access)"""
        try:
            # Get server interfaces
            interfaces = self.get_server_interfaces(server_id)
            if not interfaces:
                logger.warning(f"No interfaces found for server {server_id}")
                return None
            
            # Get networks with external gateway access
            external_networks = self.find_networks_with_external_gateway()
            logger.info(f"Found {len(external_networks)} networks with external gateway access")
            
            # Find an interface on a network with external access and IPv4 addresses
            for interface in interfaces:
                fixed_ips = interface.get('fixed_ips', [])
                if not fixed_ips:
                    continue
                
                # Check if any fixed IP is IPv4
                has_ipv4 = False
                for fixed_ip in fixed_ips:
                    ip_address = fixed_ip.get('ip_address', '')
                    if '.' in ip_address and ':' not in ip_address:
                        has_ipv4 = True
                        break
                
                if has_ipv4:
                    # Check if this interface's network has external access
                    network_id = interface.get('net_id')
                    if network_id in external_networks:
                        logger.info(f"Found suitable interface {interface['port_id']} on external network {network_id}")
                        return interface
                    else:
                        logger.info(f"Interface {interface['port_id']} has IPv4 but no external access")
            
            # If no interface with external access found, return any interface with IPv4
            for interface in interfaces:
                fixed_ips = interface.get('fixed_ips', [])
                for fixed_ip in fixed_ips:
                    ip_address = fixed_ip.get('ip_address', '')
                    if '.' in ip_address and ':' not in ip_address:
                        logger.warning(f"Using interface {interface['port_id']} without confirmed external access")
                        return interface
            
            logger.warning(f"No suitable interfaces found for server {server_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding suitable interface: {str(e)}")
            return None
    
    def attach_interface(self, server_id, network_id, port_id=None, fixed_ips=None):
        """Attach a network interface to a server"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return None
            
            interface_data = {
                "interfaceAttachment": {
                    "net_id": network_id
                }
            }
            
            if port_id:
                interface_data["interfaceAttachment"]["port_id"] = port_id
            
            if fixed_ips:
                interface_data["interfaceAttachment"]["fixed_ips"] = fixed_ips
            
            logger.info(f"Attaching interface to server {server_id} on network {network_id}")
            
            response = requests.post(
                f"{compute_url}/servers/{server_id}/os-interface",
                headers=headers,
                json=interface_data
            )
            
            if response.status_code in [200, 202]:
                result = response.json()['interfaceAttachment']
                logger.info(f"Successfully attached interface {result['port_id']} to server {server_id}")
                return result
            else:
                logger.error(f"Failed to attach interface: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error attaching interface: {str(e)}")
            return None
    
    def detach_interface(self, server_id, port_id):
        """Detach a network interface from a server"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            compute_url = self.service_catalog.get('compute')
            if not compute_url:
                logger.error("Compute service not found in catalog")
                return False
            
            response = requests.delete(
                f"{compute_url}/servers/{server_id}/os-interface/{port_id}",
                headers=headers
            )
            
            if response.status_code in [202, 204]:
                logger.info(f"Successfully detached interface {port_id} from server {server_id}")
                return True
            else:
                logger.error(f"Failed to detach interface: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error detaching interface: {str(e)}")
            return False
    
    def add_fixed_ip_to_interface(self, server_id, port_id, subnet_id):
        """Add a fixed IP to an existing interface (same MAC address)"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return False
            
            # Get current port details
            response = requests.get(
                f"{network_url}/v2.0/ports/{port_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get port details: {response.status_code} - {response.text}")
                return False
            
            port = response.json()['port']
            current_fixed_ips = port.get('fixed_ips', [])
            
            # Add new fixed IP to the same port
            new_fixed_ips = current_fixed_ips + [{"subnet_id": subnet_id}]
            
            update_data = {
                "port": {
                    "fixed_ips": new_fixed_ips
                }
            }
            
            logger.info(f"Adding fixed IP to port {port_id} on subnet {subnet_id}")
            
            response = requests.put(
                f"{network_url}/v2.0/ports/{port_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"Successfully added fixed IP to port {port_id}")
                return True
            else:
                logger.error(f"Failed to add fixed IP to port: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding fixed IP to interface: {str(e)}")
            return False
    
    def remove_fixed_ip_from_interface(self, server_id, port_id, ip_address):
        """Remove a specific fixed IP from an interface"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            network_url = self.service_catalog.get('network')
            if not network_url:
                logger.error("Network service not found in catalog")
                return False
            
            # Get current port details
            response = requests.get(
                f"{network_url}/v2.0/ports/{port_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get port details: {response.status_code} - {response.text}")
                return False
            
            port = response.json()['port']
            current_fixed_ips = port.get('fixed_ips', [])
            
            # Remove the specific IP address
            new_fixed_ips = [ip for ip in current_fixed_ips if ip.get('ip_address') != ip_address]
            
            if len(new_fixed_ips) == len(current_fixed_ips):
                logger.warning(f"IP address {ip_address} not found on port {port_id}")
                return False
            
            update_data = {
                "port": {
                    "fixed_ips": new_fixed_ips
                }
            }
            
            logger.info(f"Removing fixed IP {ip_address} from port {port_id}")
            
            response = requests.put(
                f"{network_url}/v2.0/ports/{port_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"Successfully removed fixed IP {ip_address} from port {port_id}")
                return True
            else:
                logger.error(f"Failed to remove fixed IP from port: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing fixed IP from interface: {str(e)}")
            return False
    
    def get_networks_for_fixed_ip(self):
        """Get all networks that can be used for adding fixed IPs"""
        try:
            networks = self.get_networks()
            if not networks:
                logger.error("Failed to retrieve networks")
                return []
            
            # Show all networks except external ones
            available_networks = []
            for network in networks:
                # Skip external networks for fixed IPs
                if network.get('router:external', False):
                    logger.info(f"Skipping external network: {network['name']}")
                    continue
                
                # Include all other networks
                available_networks.append(network)
                logger.info(f"Available network for fixed IP: {network['name']} ({network['id']})")
            
            if not available_networks:
                # If no networks found, show all networks
                logger.warning("No non-external networks found, showing all networks")
                available_networks = networks
            
            return available_networks
            
        except Exception as e:
            logger.error(f"Error getting networks for fixed IP: {str(e)}")
            return []

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
        [InlineKeyboardButton("🛠️ Create Private Network", callback_data='create_network')],
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
        logger.info(f"Processing callback data: {callback_data}")
        
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
        elif callback_data == 'create_network':
            await create_network_menu(query, context)
        elif callback_data.startswith('select_server|') and not callback_data.startswith('select_server_for_fixed_ip|'):
            # Handle floating IP server selection - using index
            server_index = callback_data.replace('select_server|', '')
            await select_floating_ip(query, context, server_index)
        elif callback_data.startswith('select_ip|'):
            # Format: select_ip|{ip_index}
            ip_index = callback_data.replace('select_ip|', '')
            await confirm_associate_ip(query, context, ip_index)
        elif callback_data.startswith('confirm_associate|'):
            # Format: confirm_associate|{ip_index}
            ip_index = callback_data.replace('confirm_associate|', '')
            await do_associate_ip(query, context, ip_index)
        elif callback_data.startswith('disassociate_ip|'):
            ip_id = callback_data.replace('disassociate_ip|', '')
            await confirm_disassociate_ip(query, context, ip_id)
        elif callback_data.startswith('confirm_disassociate|'):
            ip_id = callback_data.replace('confirm_disassociate|', '')
            await do_disassociate_ip(query, ip_id)
        elif callback_data.startswith('delete_ip|'):
            ip_id = callback_data.replace('delete_ip|', '')
            await confirm_delete_ip(query, context, ip_id)
        elif callback_data.startswith('confirm_delete|'):
            ip_id = callback_data.replace('confirm_delete|', '')
            await do_delete_ip(query, ip_id)
        # Fixed IP management handlers
        elif callback_data == 'manage_fixed_ips':
            await manage_fixed_ips(query, context)
        elif callback_data.startswith('select_server_for_fixed_ip|'):
            server_index = callback_data.replace('select_server_for_fixed_ip|', '')
            await manage_server_fixed_ips(query, context, server_index)
        elif callback_data.startswith('add_fixed_ip|'):
            server_index = callback_data.replace('add_fixed_ip|', '')
            await select_interface_for_fixed_ip(query, context, server_index)
        elif callback_data.startswith('select_interface|'):
            # Format: select_interface|{interface_index}
            interface_index = callback_data.replace('select_interface|', '')
            await select_network_for_fixed_ip(query, context, interface_index)
        elif callback_data.startswith('select_network|'):
            # Format: select_network|{network_index}
            network_index = callback_data.replace('select_network|', '')
            await confirm_add_fixed_ip(query, context, network_index)
        elif callback_data.startswith('confirm_add_fixed_ip|'):
            # Format: confirm_add_fixed_ip|{network_index}
            network_index = callback_data.replace('confirm_add_fixed_ip|', '')
            await do_add_fixed_ip(query, context, network_index)
        elif callback_data.startswith('remove_fixed_ip|'):
            # Format: remove_fixed_ip|{ip_index}
            ip_index = callback_data.replace('remove_fixed_ip|', '')
            # Get the IP address from the stored fixed IPs
            fixed_ips = context.user_data.get('fixed_ips', [])
            if ip_index.isdigit() and int(ip_index) < len(fixed_ips):
                ip_data = fixed_ips[int(ip_index)]
                # Store for confirmation
                context.user_data['confirm_remove_ip'] = ip_data
                await confirm_remove_fixed_ip(query, context, ip_data)
            else:
                await query.edit_message_text("❌ Invalid IP selection. Please try again.")
        elif callback_data.startswith('confirm_remove_fixed_ip|'):
            # Format: confirm_remove_fixed_ip|{ip_index}
            ip_index = callback_data.replace('confirm_remove_fixed_ip|', '')
            await do_remove_fixed_ip(query, context, ip_index)
        elif callback_data == 'help':
            await show_help(query)
        elif callback_data.startswith('server|'):
            server_id = callback_data.replace('server|', '')
            await show_server_details(query, context, server_id)
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
                callback_data=f'server|{server["id"]}'
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

async def show_server_details(query, context, server_id):
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
        
        # Store server info for button actions
        context.user_data['detail_server'] = server
        
        # Initialize server_map if it doesn't exist
        if 'server_map' not in context.user_data:
            context.user_data['server_map'] = {}
        
        # Find server index for callback data
        server_index = None
        for idx, srv_id in context.user_data.get('server_map', {}).items():
            if srv_id == server_id:
                server_index = idx
                break
        
        if server_index is None:
            # If not found in map, add it
            servers = context.user_data.get('servers', [])
            if not servers:
                servers = [server]
                context.user_data['servers'] = servers
                server_index = "0"
                context.user_data['server_map'] = {"0": server_id}
            else:
                server_index = str(len(servers) - 1) # Use the last index
                context.user_data['server_map'][server_index] = server_id
        
        # Add buttons for IP management
        keyboard = [
            [InlineKeyboardButton("➕ Add Floating IP", callback_data=f'select_server|{server_index}')],
            [InlineKeyboardButton("🔧 Manage Fixed IPs", callback_data=f'select_server_for_fixed_ip|{server_index}')],
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

async def create_network_menu(query, context):
    """Show create network menu"""
    text = """
🛠️ *Create Private Network*

This will create a new private network with:
• Network name: `bot-private-network`
• CIDR: `192.168.100.0/24`
• DHCP enabled
• Isolated from other networks

This network can be used for:
• Adding fixed IPs to servers
• Creating isolated environments
• Preparing for floating IP association

Would you like to create this network?
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Create Network", callback_data='confirm_create_network')],
        [InlineKeyboardButton("❌ Cancel", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

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
                    callback_data=f"disassociate_ip|{fip['id']}"
                )])
            else:
                text += f"   Status: `{fip['status']}`\n"
                # Add button to associate
                keyboard.append([InlineKeyboardButton(
                    f"🔄 Associate {fip['floating_ip_address']}",
                    callback_data=f"associate_floating_ip"
                )])
            
            # Add button to delete this IP
            keyboard.append([InlineKeyboardButton(
                f"🗑️ Delete {fip['floating_ip_address']}",
                callback_data=f"delete_ip|{fip['id']}"
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
        # Get public network ID (will prefer public-167 or public-431)
        public_network_id = openstack.get_public_network_id()
        if not public_network_id:
            await query.edit_message_text(
                "❌ Failed to find public network for floating IP allocation.\n\n"
                "Available public networks: public-167, public-431\n"
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
        
        # Store servers in context with indices
        context.user_data['servers'] = servers
        context.user_data['server_map'] = {str(i): server['id'] for i, server in enumerate(servers)}
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        text = "🖥️ *Select a Server*\n\n"
        text += "Choose a server to associate with a floating IP:"
        
        keyboard = []
        for i, server in enumerate(servers):
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {server['name']}",
                callback_data=f"select_server|{i}"
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

async def select_floating_ip(query, context, server_index):
    """Select a floating IP to associate with the server"""
    try:
        # Get server ID from stored mapping
        server_id = context.user_data.get('server_map', {}).get(server_index)
        if not server_id:
            await query.edit_message_text("❌ Server not found. Please try again.")
            return
        
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
        
        # Store floating IPs with indices
        context.user_data['floating_ips'] = unassociated_ips
        context.user_data['ip_map'] = {str(i): ip['id'] for i, ip in enumerate(unassociated_ips)}
        context.user_data['selected_server_id'] = server_id
        
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
        for i, ip in enumerate(unassociated_ips):
            keyboard.append([InlineKeyboardButton(
                f"🔓 {ip['floating_ip_address']}",
                callback_data=f"select_ip|{i}"
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

async def confirm_associate_ip(query, context, ip_index):
    """Confirm association of floating IP with server"""
    try:
        # Get IP ID from stored mapping
        ip_id = context.user_data.get('ip_map', {}).get(ip_index)
        server_id = context.user_data.get('selected_server_id')
        
        if not ip_id or not server_id:
            await query.edit_message_text("❌ Invalid selection. Please try again.")
            return
        
        # Get floating IP details
        floating_ip = None
        for ip in context.user_data.get('floating_ips', []):
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
        
        # Store for confirmation
        context.user_data['confirm_ip_id'] = ip_id
        context.user_data['confirm_server_id'] = server_id
        
        text = "⚠️ *Confirm Association*\n\n"
        text += f"Are you sure you want to associate floating IP:\n"
        text += f"`{floating_ip['floating_ip_address']}`\n\n"
        text += f"with server:\n"
        text += f"`{server['name']}`?\n\n"
        text += "**Note:** The server must have an interface on a network with external gateway access."
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Associate", callback_data=f"confirm_associate|{ip_index}")],
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

async def do_associate_ip(query, context, ip_index):
    """Associate floating IP with server"""
    try:
        # Get stored IDs
        ip_id = context.user_data.get('confirm_ip_id')
        server_id = context.user_data.get('confirm_server_id')
        
        if not ip_id or not server_id:
            await query.edit_message_text("❌ Invalid operation. Please try again.")
            return
        
        # Get a suitable interface for floating IP association
        suitable_interface = openstack.get_suitable_interface_for_floating_ip(server_id)
        
        if not suitable_interface:
            # Try to find networks with external gateway and attach interface
            external_networks = openstack.find_networks_with_external_gateway()
            
            if external_networks:
                # Try to attach interface to a network with external access
                for network_id in external_networks:
                    interface = openstack.attach_interface(server_id, network_id)
                    if interface:
                        suitable_interface = interface
                        logger.info(f"Attached new interface {interface['port_id']} to network {network_id}")
                        break
            
            if not suitable_interface:
                await query.edit_message_text(
                    "❌ *No Suitable Network Interface Found*\n\n"
                    "This server doesn't have any interfaces on networks with external gateway access.\n\n"
                    "**Solutions:**\n"
                    "1. Create a private network with external gateway\n"
                    "2. Attach the server to a network with router access\n"
                    "3. Add a fixed IP from a network with external connectivity\n\n"
                    "**Technical:** External network is not reachable from server's subnet.\n"
                    "The server needs to be on a network that has a router with external gateway."
                )
                return
        
        port_id = suitable_interface['port_id']
        logger.info(f"Using interface port {port_id} for floating IP association")
        
        # Associate floating IP with port
        result = openstack.associate_floating_ip(ip_id, port_id)
        if not result:
            await query.edit_message_text(
                "❌ *Failed to Associate Floating IP*\n\n"
                "This could be due to:\n"
                "• External network not reachable from server's subnet\n"
                "• No router with external gateway configured\n"
                "• Network routing issues\n"
                "• Port configuration problems\n\n"
                "**Solution:** Ensure the server is connected to a network with external gateway access.\n"
                "Check logs for detailed error information."
            )
            return
        
        # Success message
        text = "✅ *Floating IP Associated Successfully*\n\n"
        text += f"IP Address: `{result['floating_ip_address']}`\n"
        text += f"Fixed IP: `{result.get('fixed_ip_address', 'N/A')}`\n"
        text += f"Status: `{result['status']}`\n\n"
        text += "The floating IP has been successfully associated with the server's interface."
        
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
            [InlineKeyboardButton("✅ Yes, Disassociate", callback_data=f"confirm_disassociate|{ip_id}")],
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
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete|{ip_id}")],
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

# Fixed IP management functions
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
        
        # Store servers in context with indices
        context.user_data['servers'] = servers
        context.user_data['server_map'] = {str(i): server['id'] for i, server in enumerate(servers)}
        
        if not servers:
            await query.edit_message_text("📭 No servers found in your project.")
            return
        
        text = "🔧 *Fixed IP Management*\n\n"
        text += "Select a server to manage its fixed IPs:\n"
        text += "Fixed IPs are added to existing interfaces (same MAC address)."
        
        keyboard = []
        for i, server in enumerate(servers):
            status_emoji = "🟢" if server['status'] == 'ACTIVE' else "🔴" if server['status'] == 'ERROR' else "🟡"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {server['name']}",
                callback_data=f"select_server_for_fixed_ip|{i}"
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

async def manage_server_fixed_ips(query, context, server_index):
    """Manage fixed IPs for a specific server"""
    try:
        # Get server ID from stored mapping
        server_id = context.user_data.get('server_map', {}).get(server_index)
        if not server_id:
            await query.edit_message_text("❌ Server not found. Please try again.")
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
        
        # Get server interfaces
        interfaces = openstack.get_server_interfaces(server_id)
        if not interfaces:
            await query.edit_message_text("❌ No interfaces found for this server.")
            return
        
        # Store current server for later use
        context.user_data['current_server_id'] = server_id
        context.user_data['current_server_index'] = server_index
        context.user_data['server_interfaces'] = interfaces
        
        text = f"🔧 *Fixed IPs for {server['name']}*\n\n"
        
        # List current fixed IPs by interface
        text += "Current Interfaces and Fixed IPs:\n"
        fixed_ips = []
        
        for i, interface in enumerate(interfaces):
            port_id = interface['port_id']
            net_id = interface['net_id']
            text += f"\n**Interface {i+1}** (Port: `{port_id[:8]}...`)\n"
            text += f"Network: `{net_id[:8]}...`\n"
            
            interface_fixed_ips = interface.get('fixed_ips', [])
            if interface_fixed_ips:
                for fixed_ip in interface_fixed_ips:
                    ip_address = fixed_ip['ip_address']
                    subnet_id = fixed_ip['subnet_id']
                    text += f"• `{ip_address}` (subnet: `{subnet_id[:8]}...`)\n"
                    # Store IP data for removal
                    fixed_ips.append({
                        'ip_address': ip_address,
                        'port_id': port_id,
                        'subnet_id': subnet_id,
                        'interface_index': i
                    })
            else:
                text += "• No fixed IPs\n"
        
        # Store fixed IPs for removal operations
        context.user_data['fixed_ips'] = fixed_ips
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Fixed IP", callback_data=f"add_fixed_ip|{server_index}")],
            [InlineKeyboardButton("🔙 Back to Server List", callback_data='manage_fixed_ips')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]
        
        # Add remove buttons for each IP using indices
        for i, ip_data in enumerate(fixed_ips):
            keyboard.insert(0, [InlineKeyboardButton(
                f"🗑️ Remove {ip_data['ip_address']}",
                callback_data=f"remove_fixed_ip|{i}"
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

async def select_interface_for_fixed_ip(query, context, server_index):
    """Select an interface to add a fixed IP to"""
    try:
        # Get server interfaces from stored data
        interfaces = context.user_data.get('server_interfaces', [])
        if not interfaces:
            await query.edit_message_text("❌ No interfaces found for this server.")
            return
        
        # Get server details for display
        server_id = context.user_data.get('server_map', {}).get(server_index)
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            await query.edit_message_text("❌ Server not found.")
            return
        
        text = f"🔌 *Select Interface for {server['name']}*\n\n"
        text += "Choose an interface to add a fixed IP to:\n"
        text += "(Fixed IPs are added to existing interfaces)\n\n"
        
        keyboard = []
        for i, interface in enumerate(interfaces):
            port_id = interface['port_id']
            net_id = interface['net_id']
            fixed_ips_count = len(interface.get('fixed_ips', []))
            
            keyboard.append([InlineKeyboardButton(
                f"Interface {i+1} ({fixed_ips_count} IPs) - {port_id[:8]}...",
                callback_data=f"select_interface|{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data=f'select_server_for_fixed_ip|{server_index}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in select_interface_for_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while selecting interface.")

async def select_network_for_fixed_ip(query, context, interface_index):
    """Select a network/subnet to add a fixed IP from"""
    try:
        # Get selected interface
        interfaces = context.user_data.get('server_interfaces', [])
        if not interfaces or int(interface_index) >= len(interfaces):
            await query.edit_message_text("❌ Invalid interface selection.")
            return
        
        selected_interface = interfaces[int(interface_index)]
        context.user_data['selected_interface'] = selected_interface
        context.user_data['selected_interface_index'] = interface_index
        
        # Get all networks and their subnets
        networks = openstack.get_networks_for_fixed_ip()
        subnets = openstack.get_subnets()
        
        if not networks or not subnets:
            await query.edit_message_text("❌ Failed to retrieve networks or subnets.")
            return
        
        # Create a list of available subnets
        available_subnets = []
        for network in networks:
            network_subnets = [s for s in subnets if s['network_id'] == network['id']]
            for subnet in network_subnets:
                available_subnets.append({
                    'subnet': subnet,
                    'network': network
                })
        
        if not available_subnets:
            await query.edit_message_text("❌ No subnets available for adding fixed IPs.")
            return
        
        # Store subnets with indices
        context.user_data['available_subnets'] = available_subnets
        context.user_data['subnet_map'] = {str(i): subnet_data['subnet']['id'] for i, subnet_data in enumerate(available_subnets)}
        
        text = f"🌐 *Select Network/Subnet*\n\n"
        text += f"Choose a subnet to add a fixed IP from:\n"
        text += f"Interface: `{selected_interface['port_id'][:8]}...`\n\n"
        
        keyboard = []
        for i, subnet_data in enumerate(available_subnets):
            subnet = subnet_data['subnet']
            network = subnet_data['network']
            
            status_emoji = "🟢" if network['status'] == 'ACTIVE' else "🔴"
            keyboard.append([InlineKeyboardButton(
                f"{status_emoji} {network['name']} - {subnet['cidr']}",
                callback_data=f"select_network|{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data=f'select_server_for_fixed_ip|{context.user_data.get("current_server_index", "0")}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in select_network_for_fixed_ip: {str(e)}")
        await query.edit_message_text("❌ An error occurred while retrieving networks.")

async def confirm_add_fixed_ip(query, context, network_index):
    """Confirm adding a fixed IP to an interface"""
    try:
        # Get subnet from stored mapping
        subnet_id = context.user_data.get('subnet_map', {}).get(network_index)
        selected_interface = context.user_data.get('selected_interface')
        server_index = context.user_data.get('current_server_index')
        
        if not subnet_id or not selected_interface:
            await query.edit_message_text("❌ Invalid selection. Please try again.")
            return
        
        # Get subnet and network details
        available_subnets = context.user_data.get('available_subnets', [])
        if int(network_index) >= len(available_subnets):
            await query.edit_message_text("❌ Invalid network selection.")
            return
        
        subnet_data = available_subnets[int(network_index)]
        subnet = subnet_data['subnet']
        network = subnet_data['network']
        
        # Get server details
        server_id = context.user_data.get('current_server_id')
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            await query.edit_message_text("❌ Server not found.")
            return
        
        # Store for confirmation
        context.user_data['confirm_subnet_id'] = subnet_id
        context.user_data['confirm_port_id'] = selected_interface['port_id']
        
        text = "⚠️ *Confirm Add Fixed IP*\n\n"
        text += f"Add a fixed IP to:\n"
        text += f"**Server:** `{server['name']}`\n"
        text += f"**Interface:** `{selected_interface['port_id'][:8]}...`\n"
        text += f"**Network:** `{network['name']}`\n"
        text += f"**Subnet:** `{subnet['cidr']}`\n\n"
        text += "This will add an additional IP address to the existing interface."
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Add IP", callback_data=f"confirm_add_fixed_ip|{network_index}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f'select_server_for_fixed_ip|{server_index}')]
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

async def do_add_fixed_ip(query, context, network_index):
    """Add a fixed IP to an interface"""
    try:
        # Get stored IDs
        subnet_id = context.user_data.get('confirm_subnet_id')
        port_id = context.user_data.get('confirm_port_id')
        server_id = context.user_data.get('current_server_id')
        server_index = context.user_data.get('current_server_index')
        
        if not subnet_id or not port_id or not server_id:
            await query.edit_message_text("❌ Invalid operation. Please try again.")
            return
        
        logger.info(f"Adding fixed IP: server_id={server_id}, port_id={port_id}, subnet_id={subnet_id}")
        
        # Add fixed IP to the interface
        success = openstack.add_fixed_ip_to_interface(server_id, port_id, subnet_id)
        if not success:
            await query.edit_message_text(
                "❌ *Failed to Add Fixed IP*\n\n"
                "This could be due to:\n"
                "• Subnet capacity limitations\n"
                "• Network configuration issues\n"
                "• Port already has maximum IPs\n"
                "• Permission restrictions\n\n"
                "Please check the logs for detailed error information."
            )
            return
        
        # Success message
        text = "✅ *Fixed IP Added Successfully*\n\n"
        text += "A new fixed IP has been successfully added to the interface.\n\n"
        text += "The interface now has an additional IP address from the selected subnet.\n\n"
        text += "**Note:** This IP can now be used for floating IP association."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Server IPs", callback_data=f'select_server_for_fixed_ip|{server_index}')],
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

async def confirm_remove_fixed_ip(query, context, ip_data):
    """Confirm removing a fixed IP from an interface"""
    try:
        # Get stored server ID
        server_id = context.user_data.get('current_server_id')
        if not server_id:
            await query.edit_message_text("❌ Server not found. Please try again.")
            return
            
        # Get server details
        server = None
        for s in context.user_data.get('servers', []):
            if s['id'] == server_id:
                server = s
                break
        
        if not server:
            await query.edit_message_text("❌ Failed to retrieve server details.")
            return
        
        ip_address = ip_data['ip_address']
        port_id = ip_data['port_id']
        
        text = "⚠️ *Confirm Remove Fixed IP*\n\n"
        text += f"Remove fixed IP:\n"
        text += f"**IP Address:** `{ip_address}`\n"
        text += f"**Server:** `{server['name']}`\n"
        text += f"**Interface:** `{port_id[:8]}...`\n\n"
        text += "**Warning:** This action cannot be undone and may affect:\n"
        text += "• Associated floating IPs\n"
        text += "• Network connectivity\n"
        text += "• Running services"
        
        # Store IP data for removal
        context.user_data['confirm_remove_ip'] = ip_data
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Remove IP", callback_data=f"confirm_remove_fixed_ip|{ip_address}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f'select_server_for_fixed_ip|{context.user_data.get("current_server_index", "0")}')]
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

async def do_remove_fixed_ip(query, context, ip_index):
    """Remove a fixed IP from an interface"""
    try:
        # Get stored data
        ip_data = context.user_data.get('confirm_remove_ip')
        server_id = context.user_data.get('current_server_id')
        server_index = context.user_data.get('current_server_index')
        
        if not ip_data or not server_id:
            await query.edit_message_text("❌ Invalid operation. Please try again.")
            return
        
        ip_address = ip_data['ip_address']
        port_id = ip_data['port_id']
        
        logger.info(f"Removing fixed IP: server_id={server_id}, port_id={port_id}, ip_address={ip_address}")
        
        # Remove fixed IP from the interface
        success = openstack.remove_fixed_ip_from_interface(server_id, port_id, ip_address)
        if not success:
            await query.edit_message_text(
                "❌ *Failed to Remove Fixed IP*\n\n"
                "This could be due to:\n"
                "• IP address is still in use by floating IP\n"
                "• Cannot remove the last IP from interface\n"
                "• Network configuration restrictions\n"
                "• Permission limitations\n\n"
                "Please check the logs for detailed error information."
            )
            return
        
        # Success message
        text = "✅ *Fixed IP Removed Successfully*\n\n"
        text += f"Fixed IP `{ip_address}` has been successfully removed from the interface.\n\n"
        text += "The interface no longer has this IP address assigned."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Server IPs", callback_data=f'select_server_for_fixed_ip|{server_index}')],
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
• 🛠️ Create private networks
• 📋 Get detailed server information

*Floating IP Management:*
• Allocate new floating IPs from public-167/public-431
• Associate IPs with servers (requires external gateway access)
• Disassociate IPs from servers
• Delete floating IPs

*Fixed IP Management:*
• Add fixed IPs to existing interfaces (same MAC address)
• Remove fixed IPs from interfaces
• View current IP assignments by interface

*Network Requirements:*
• Floating IPs require servers on networks with external gateway
• Fixed IPs are added to existing interfaces, not new ones
• Private networks can be created for isolation

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
        [InlineKeyboardButton("🛠️ Create Private Network", callback_data='create_network')],
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
            
            # Check public networks
            public_networks = openstack.get_public_networks()
            if public_networks:
                services_text += f"\n*Public Networks Found:* {len(public_networks)}\n"
                for net in public_networks[:3]:  # Show first 3
                    services_text += f"• `{net['name']}`\n"
            
            # Check external gateway networks
            external_networks = openstack.find_networks_with_external_gateway()
            if external_networks:
                services_text += f"\n*Networks with External Gateway:* {len(external_networks)}\n"
            
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
        
        # Test public networks
        public_networks = openstack.get_public_networks()
        if public_networks:
            logger.info(f"Found {len(public_networks)} public networks:")
            for net in public_networks:
                logger.info(f"  - {net['name']} ({net['id']})")
        else:
            logger.warning("No public networks found!")
            
        # Test external gateway networks
        external_networks = openstack.find_networks_with_external_gateway()
        logger.info(f"Found {len(external_networks)} networks with external gateway access")
    else:
        logger.error("❌ OpenStack connection failed!")
    
    # Start the bot
    logger.info("Starting OpenStack Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
