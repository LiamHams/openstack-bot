#!/bin/bash

# OpenStack Telegram Bot CLI Menu
# This script provides a command-line interface for the bot

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Bot directory
BOT_DIR="/opt/openstack-bot"

# Check if bot is installed
if [ ! -d "$BOT_DIR" ]; then
    echo -e "${RED}${BOLD}Error:${NC} OpenStack Telegram Bot is not installed."
    echo "Please run the installation script first."
    exit 1
fi

# Function to display the header
show_header() {
    clear
    echo -e "${BLUE}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}${BOLD}║                                                        ║${NC}"
    echo -e "${BLUE}${BOLD}║             OpenStack Telegram Bot CLI                 ║${NC}"
    echo -e "${BLUE}${BOLD}║                                                        ║${NC}"
    echo -e "${BLUE}${BOLD}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to display the main menu
show_main_menu() {
    show_header
    echo -e "${BOLD}Select an option:${NC}"
    echo ""
    echo -e "  ${CYAN}1)${NC} Start Bot"
    echo -e "  ${CYAN}2)${NC} Stop Bot"
    echo -e "  ${CYAN}3)${NC} Restart Bot"
    echo -e "  ${CYAN}4)${NC} Check Status"
    echo -e "  ${CYAN}5)${NC} View Logs"
    echo -e "  ${CYAN}6)${NC} Update Bot"
    echo -e "  ${CYAN}7)${NC} Configure Auto-Updates"
    echo -e "  ${CYAN}8)${NC} Edit Configuration"
    echo -e "  ${CYAN}9)${NC} Backup Configuration"
    echo -e "  ${CYAN}0)${NC} Exit"
    echo ""
    echo -e "${YELLOW}Enter your choice:${NC} "
    read -r choice
    
    case $choice in
        1) start_bot ;;
        2) stop_bot ;;
        3) restart_bot ;;
        4) check_status ;;
        5) view_logs ;;
        6) update_bot ;;
        7) configure_auto_updates ;;
        8) edit_configuration ;;
        9) backup_configuration ;;
        0) exit 0 ;;
        *) 
            echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
            read
            show_main_menu
            ;;
    esac
}

# Function to start the bot
start_bot() {
    show_header
    echo -e "${BOLD}Starting OpenStack Telegram Bot...${NC}"
    echo ""
    
    if sudo systemctl is-active --quiet openstack-bot; then
        echo -e "${YELLOW}Bot is already running.${NC}"
    else
        sudo systemctl start openstack-bot
        sleep 2
        if sudo systemctl is-active --quiet openstack-bot; then
            echo -e "${GREEN}Bot started successfully!${NC}"
        else
            echo -e "${RED}Failed to start bot. Check logs for details.${NC}"
        fi
    fi
    
    echo ""
    echo -e "${BOLD}Service Status:${NC}"
    sudo systemctl status openstack-bot --no-pager -n 5
    
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Function to stop the bot
stop_bot() {
    show_header
    echo -e "${BOLD}Stopping OpenStack Telegram Bot...${NC}"
    echo ""
    
    if ! sudo systemctl is-active --quiet openstack-bot; then
        echo -e "${YELLOW}Bot is not running.${NC}"
    else
        sudo systemctl stop openstack-bot
        sleep 2
        if ! sudo systemctl is-active --quiet openstack-bot; then
            echo -e "${GREEN}Bot stopped successfully!${NC}"
        else
            echo -e "${RED}Failed to stop bot.${NC}"
        fi
    fi
    
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Function to restart the bot
restart_bot() {
    show_header
    echo -e "${BOLD}Restarting OpenStack Telegram Bot...${NC}"
    echo ""
    
    sudo systemctl restart openstack-bot
    sleep 2
    if sudo systemctl is-active --quiet openstack-bot; then
        echo -e "${GREEN}Bot restarted successfully!${NC}"
    else
        echo -e "${RED}Failed to restart bot. Check logs for details.${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Service Status:${NC}"
    sudo systemctl status openstack-bot --no-pager -n 5
    
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Function to check status
check_status() {
    show_header
    echo -e "${BOLD}OpenStack Telegram Bot Status${NC}"
    echo ""
    
    # Check if service is running
    if sudo systemctl is-active --quiet openstack-bot; then
        echo -e "${GREEN}● Bot Service: Running${NC}"
    else
        echo -e "${RED}● Bot Service: Stopped${NC}"
    fi
    
    # Check if service is enabled
    if sudo systemctl is-enabled --quiet openstack-bot; then
        echo -e "${GREEN}● Auto-start: Enabled${NC}"
    else
        echo -e "${RED}● Auto-start: Disabled${NC}"
    fi
    
    # Check for auto-updates
    if crontab -l 2>/dev/null | grep -q "openstack-bot/auto-update.sh"; then
        echo -e "${GREEN}● Auto-updates: Configured${NC}"
        echo -e "  Schedule: $(crontab -l | grep "openstack-bot/auto-update.sh" | awk '{print $1, $2, $3, $4, $5}')"
    else
        echo -e "${YELLOW}● Auto-updates: Not configured${NC}"
    fi
    
    # Check configuration
    if [ -f "$BOT_DIR/config.env" ]; then
        if grep -q "your_telegram_bot_token_here" "$BOT_DIR/config.env"; then
            echo -e "${RED}● Configuration: Incomplete (Bot token not set)${NC}"
        else
            echo -e "${GREEN}● Configuration: Complete${NC}"
        fi
    else
        echo -e "${RED}● Configuration: Missing${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}System Information:${NC}"
    echo -e "● Disk Usage: $(df -h /opt | awk 'NR==2 {print $5 " used (" $3 "/" $2 ")"}')"
    echo -e "● Memory Usage: $(free -h | awk '/^Mem:/ {print $3 "/" $2 " (" int($3/$2*100) "%)"}')"
    echo -e "● Bot Uptime: $(sudo systemctl show openstack-bot --property=ActiveState,ActiveEnterTimestamp | grep ActiveEnterTimestamp | sed 's/ActiveEnterTimestamp=//g')"
    
    echo ""
    echo -e "${BOLD}Service Details:${NC}"
    sudo systemctl status openstack-bot --no-pager -n 5
    
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Function to view logs
view_logs() {
    show_header
    echo -e "${BOLD}Log Viewer${NC}"
    echo ""
    echo -e "Select log type:"
    echo -e "  ${CYAN}1)${NC} Application Logs"
    echo -e "  ${CYAN}2)${NC} Service Logs"
    echo -e "  ${CYAN}3)${NC} Update Logs"
    echo -e "  ${CYAN}4)${NC} Back to Main Menu"
    echo ""
    echo -e "${YELLOW}Enter your choice:${NC} "
    read -r log_choice
    
    case $log_choice in
        1)
            show_header
            echo -e "${BOLD}Application Logs${NC}"
            echo ""
            if [ -f "$BOT_DIR/openstack_bot.log" ]; then
                echo -e "${CYAN}Last 20 lines of application log:${NC}"
                echo ""
                tail -n 20 "$BOT_DIR/openstack_bot.log"
                echo ""
                echo -e "${BOLD}Options:${NC}"
                echo -e "  ${CYAN}1)${NC} View more lines"
                echo -e "  ${CYAN}2)${NC} Follow log (live updates)"
                echo -e "  ${CYAN}3)${NC} Back to Log Menu"
                echo ""
                echo -e "${YELLOW}Enter your choice:${NC} "
                read -r app_log_choice
                
                case $app_log_choice in
                    1)
                        echo -e "${YELLOW}Enter number of lines to view:${NC} "
                        read -r lines
                        if [[ "$lines" =~ ^[0-9]+$ ]]; then
                            show_header
                            echo -e "${BOLD}Application Logs (Last $lines lines)${NC}"
                            echo ""
                            tail -n "$lines" "$BOT_DIR/openstack_bot.log"
                            echo ""
                            echo -e "Press Enter to return to the log menu..."
                            read
                            view_logs
                        else
                            echo -e "${RED}Invalid input. Press Enter to continue...${NC}"
                            read
                            view_logs
                        fi
                        ;;
                    2)
                        show_header
                        echo -e "${BOLD}Following Application Logs (Press Ctrl+C to stop)${NC}"
                        echo ""
                        tail -f "$BOT_DIR/openstack_bot.log"
                        view_logs
                        ;;
                    3)
                        view_logs
                        ;;
                    *)
                        echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
                        read
                        view_logs
                        ;;
                esac
            else
                echo -e "${RED}Application log file not found.${NC}"
                echo ""
                echo -e "Press Enter to return to the log menu..."
                read
                view_logs
            fi
            ;;
        2)
            show_header
            echo -e "${BOLD}Service Logs${NC}"
            echo ""
            echo -e "${CYAN}Last 20 lines of service log:${NC}"
            echo ""
            sudo journalctl -u openstack-bot -n 20 --no-pager
            echo ""
            echo -e "${BOLD}Options:${NC}"
            echo -e "  ${CYAN}1)${NC} View more lines"
            echo -e "  ${CYAN}2)${NC} Follow log (live updates)"
            echo -e "  ${CYAN}3)${NC} Back to Log Menu"
            echo ""
            echo -e "${YELLOW}Enter your choice:${NC} "
            read -r service_log_choice
            
            case $service_log_choice in
                1)
                    echo -e "${YELLOW}Enter number of lines to view:${NC} "
                    read -r lines
                    if [[ "$lines" =~ ^[0-9]+$ ]]; then
                        show_header
                        echo -e "${BOLD}Service Logs (Last $lines lines)${NC}"
                        echo ""
                        sudo journalctl -u openstack-bot -n "$lines" --no-pager
                        echo ""
                        echo -e "Press Enter to return to the log menu..."
                        read
                        view_logs
                    else
                        echo -e "${RED}Invalid input. Press Enter to continue...${NC}"
                        read
                        view_logs
                    fi
                    ;;
                2)
                    show_header
                    echo -e "${BOLD}Following Service Logs (Press Ctrl+C to stop)${NC}"
                    echo ""
                    sudo journalctl -u openstack-bot -f
                    view_logs
                    ;;
                3)
                    view_logs
                    ;;
                *)
                    echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
                    read
                    view_logs
                    ;;
            esac
            ;;
        3)
            show_header
            echo -e "${BOLD}Update Logs${NC}"
            echo ""
            if [ -f "$BOT_DIR/auto-update.log" ]; then
                echo -e "${CYAN}Last 20 lines of update log:${NC}"
                echo ""
                tail -n 20 "$BOT_DIR/auto-update.log"
                echo ""
                echo -e "${BOLD}Options:${NC}"
                echo -e "  ${CYAN}1)${NC} View more lines"
                echo -e "  ${CYAN}2)${NC} Follow log (live updates)"
                echo -e "  ${CYAN}3)${NC} Back to Log Menu"
                echo ""
                echo -e "${YELLOW}Enter your choice:${NC} "
                read -r update_log_choice
                
                case $update_log_choice in
                    1)
                        echo -e "${YELLOW}Enter number of lines to view:${NC} "
                        read -r lines
                        if [[ "$lines" =~ ^[0-9]+$ ]]; then
                            show_header
                            echo -e "${BOLD}Update Logs (Last $lines lines)${NC}"
                            echo ""
                            tail -n "$lines" "$BOT_DIR/auto-update.log"
                            echo ""
                            echo -e "Press Enter to return to the log menu..."
                            read
                            view_logs
                        else
                            echo -e "${RED}Invalid input. Press Enter to continue...${NC}"
                            read
                            view_logs
                        fi
                        ;;
                    2)
                        show_header
                        echo -e "${BOLD}Following Update Logs (Press Ctrl+C to stop)${NC}"
                        echo ""
                        tail -f "$BOT_DIR/auto-update.log"
                        view_logs
                        ;;
                    3)
                        view_logs
                        ;;
                    *)
                        echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
                        read
                        view_logs
                        ;;
                esac
            else
                echo -e "${RED}Update log file not found.${NC}"
                echo ""
                echo -e "Press Enter to return to the log menu..."
                read
                view_logs
            fi
            ;;
        4)
            show_main_menu
            ;;
        *)
            echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
            read
            view_logs
            ;;
    esac
}

# Function to update bot
update_bot() {
    show_header
    echo -e "${BOLD}Update OpenStack Telegram Bot${NC}"
    echo ""
    echo -e "Select update option:"
    echo -e "  ${CYAN}1)${NC} Check for updates"
    echo -e "  ${CYAN}2)${NC} Update now"
    echo -e "  ${CYAN}3)${NC} Force update"
    echo -e "  ${CYAN}4)${NC} Back to Main Menu"
    echo ""
    echo -e "${YELLOW}Enter your choice:${NC} "
    read -r update_choice
    
    case $update_choice in
        1)
            show_header
            echo -e "${BOLD}Checking for updates...${NC}"
            echo ""
            sudo "$BOT_DIR/auto-update.sh" --check-only
            echo ""
            echo -e "Press Enter to return to the update menu..."
            read
            update_bot
            ;;
        2)
            show_header
            echo -e "${BOLD}Updating OpenStack Telegram Bot...${NC}"
            echo ""
            sudo "$BOT_DIR/update.sh"
            echo ""
            echo -e "Press Enter to return to the main menu..."
            read
            show_main_menu
            ;;
        3)
            show_header
            echo -e "${BOLD}Force updating OpenStack Telegram Bot...${NC}"
            echo ""
            sudo "$BOT_DIR/auto-update.sh" --force
            echo ""
            echo -e "Press Enter to return to the main menu..."
            read
            show_main_menu
            ;;
        4)
            show_main_menu
            ;;
        *)
            echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
            read
            update_bot
            ;;
    esac
}

# Function to configure auto-updates
configure_auto_updates() {
    show_header
    echo -e "${BOLD}Configure Auto-Updates${NC}"
    echo ""
    sudo "$BOT_DIR/setup-cron.sh"
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Function to edit configuration
edit_configuration() {
    show_header
    echo -e "${BOLD}Edit Configuration${NC}"
    echo ""
    
    if [ ! -f "$BOT_DIR/config.env" ]; then
        echo -e "${RED}Configuration file not found.${NC}"
        echo ""
        echo -e "Press Enter to return to the main menu..."
        read
        show_main_menu
        return
    fi
    
    echo -e "Select editor:"
    echo -e "  ${CYAN}1)${NC} nano (beginner-friendly)"
    echo -e "  ${CYAN}2)${NC} vim (advanced)"
    echo -e "  ${CYAN}3)${NC} Back to Main Menu"
    echo ""
    echo -e "${YELLOW}Enter your choice:${NC} "
    read -r editor_choice
    
    case $editor_choice in
        1)
            sudo nano "$BOT_DIR/config.env"
            echo ""
            echo -e "${GREEN}Configuration updated. Restarting bot to apply changes...${NC}"
            sudo systemctl restart openstack-bot
            echo ""
            echo -e "Press Enter to return to the main menu..."
            read
            show_main_menu
            ;;
        2)
            sudo vim "$BOT_DIR/config.env"
            echo ""
            echo -e "${GREEN}Configuration updated. Restarting bot to apply changes...${NC}"
            sudo systemctl restart openstack-bot
            echo ""
            echo -e "Press Enter to return to the main menu..."
            read
            show_main_menu
            ;;
        3)
            show_main_menu
            ;;
        *)
            echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
            read
            edit_configuration
            ;;
    esac
}

# Function to backup configuration
backup_configuration() {
    show_header
    echo -e "${BOLD}Backup Configuration${NC}"
    echo ""
    
    BACKUP_DIR="$HOME/openstack-bot-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "$BOT_DIR/config.env" ]; then
        cp "$BOT_DIR/config.env" "$BACKUP_DIR/"
        echo -e "${GREEN}✓ Configuration backed up${NC}"
    else
        echo -e "${RED}✗ Configuration file not found${NC}"
    fi
    
    if [ -f "$BOT_DIR/openstack_bot.log" ]; then
        cp "$BOT_DIR/openstack_bot.log" "$BACKUP_DIR/"
        echo -e "${GREEN}✓ Logs backed up${NC}"
    else
        echo -e "${YELLOW}✗ Log file not found${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo -e "Backup location: ${BOLD}$BACKUP_DIR${NC}"
    echo ""
    echo -e "Press Enter to return to the main menu..."
    read
    show_main_menu
}

# Start the main menu
show_main_menu
