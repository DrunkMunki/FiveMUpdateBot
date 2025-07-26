#!/usr/bin/env python3
"""
FiveM Update Bot Setup Environment
Configures the bot with user-provided settings for the latest version
"""

import os
import sys
import configparser
from pathlib import Path
import getpass

def print_header():
    """Print setup header"""
    print("=" * 70)
    print("🚀 FiveM Update Bot - Environment Setup v2.0")
    print("=" * 70)
    print("Setting up enterprise-level FiveM server management bot")
    print("with backup, rollback, and multi-platform support!")
    print()

def get_user_input(prompt, default=None, required=True):
    """Get user input with optional default"""
    if default:
        prompt += f" (default: {default})"
    
    prompt += ": "
    
    while True:
        value = input(prompt).strip()
        
        if not value and default:
            return default
        
        if not value and required:
            print("This field is required. Please enter a value.")
            continue
        
        return value

def get_boolean_input(prompt, default=True):
    """Get boolean input from user"""
    default_str = "Y/n" if default else "y/N"
    prompt += f" ({default_str}): "
    
    while True:
        value = input(prompt).strip().lower()
        
        if not value:
            return default
        
        if value in ['y', 'yes', 'true', '1']:
            return True
        elif value in ['n', 'no', 'false', '0']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def get_integer_input(prompt, default=None, min_value=None, max_value=None):
    """Get integer input from user"""
    if default is not None:
        prompt += f" (default: {default})"
    
    prompt += ": "
    
    while True:
        value = input(prompt).strip()
        
        if not value and default is not None:
            return default
        
        try:
            int_value = int(value)
            
            if min_value is not None and int_value < min_value:
                print(f"Value must be at least {min_value}")
                continue
            
            if max_value is not None and int_value > max_value:
                print(f"Value must be at most {max_value}")
                continue
            
            return int_value
        
        except ValueError:
            print("Please enter a valid number.")

def setup_discord_config():
    """Setup Discord configuration"""
    print("📱 Discord Configuration")
    print("-" * 40)
    
    # Bot Token
    print("1. Discord Bot Token:")
    print("   - Create a bot at https://discord.com/developers/applications")
    print("   - Copy the bot token from the 'Bot' section")
    print("   - Use this invite URL (replace YOUR_APPLICATION_ID):")
    print("     https://discord.com/api/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=379904&scope=bot")
    token = getpass.getpass("Enter your Discord bot token: ").strip()
    
    if not token:
        print("⚠️  Bot token is required!")
        return None
    
    # Response Channel ID
    print("\n2. Response Channel ID (optional):")
    print("   - Right-click on a Discord channel and select 'Copy ID'")
    print("   - Leave empty to allow all channels")
    channel_id = get_user_input("Enter channel ID", default="", required=False)
    
    # Allowed Roles
    print("\n3. Allowed Roles (optional):")
    print("   - Right-click on Discord roles and select 'Copy ID'")
    print("   - Separate multiple role IDs with commas")
    print("   - Leave empty to allow all users")
    allowed_roles = get_user_input("Enter role IDs", default="", required=False)
    
    # Allowed Users
    print("\n4. Allowed Users (optional):")
    print("   - Right-click on Discord users and select 'Copy ID'")
    print("   - Separate multiple user IDs with commas")
    print("   - These users can use the bot even without the allowed roles")
    allowed_users = get_user_input("Enter user IDs", default="", required=False)
    
    # Command Prefix
    print("\n5. Command Prefix:")
    command_prefix = get_user_input("Enter command prefix", default="!")
    
    # Command Names
    print("\n6. Command Names (customize bot commands):")
    print("   - You can customize all command names")
    update_cmd = get_user_input("Update command", default="update")
    download_cmd = get_user_input("Download command", default="download")
    start_cmd = get_user_input("Start server command", default="start")
    stop_cmd = get_user_input("Stop server command", default="stop")
    status_cmd = get_user_input("Status command", default="status")
    version_cmd = get_user_input("Version command", default="version")
    backups_cmd = get_user_input("Backups management command", default="backups")
    rollback_cmd = get_user_input("Rollback command", default="rollback")
    cleanup_cmd = get_user_input("Cleanup command", default="cleanup")
    config_cmd = get_user_input("Config command", default="config")
    help_cmd = get_user_input("Help command", default="help")
    
    return {
        'discord_token': token,
        'response_channel': channel_id,
        'allowed_roles': allowed_roles,
        'allowed_discord_users': allowed_users,
        'command_prefix': command_prefix,
        'update_command': update_cmd,
        'download_command': download_cmd,
        'start_command': start_cmd,
        'stop_command': stop_cmd,
        'status_command': status_cmd,
        'version_command': version_cmd,
        'backups_command': backups_cmd,
        'rollback_command': rollback_cmd,
        'cleanup_command': cleanup_cmd,
        'config_command': config_cmd,
        'help_command': help_cmd
    }

def setup_file_config():
    """Setup file management configuration"""
    print("\n📁 File Management Configuration")
    print("-" * 40)
    
    print("Configure how the bot handles downloaded files and caching.")
    
    # Base Directory
    print("\n1. Base Directory:")
    print("   - Main directory for all bot file storage")
    print("   - All subdirectories will be created here")
    print("   - Example: ./bot_files/ or G:/FiveMBot/")
    base_dir = get_user_input("Enter base directory", default="./bot_files/")
    
    # Download Directory
    print("\n2. Download Subdirectory:")
    print("   - Subdirectory name for downloaded 7z files (artifact cache)")
    print(f"   - Full path will be: {base_dir}[subdirectory]/")
    download_dir = get_user_input("Enter download subdirectory name", default="downloads")
    
    # Temp Directory
    print("\n3. Temporary Subdirectory:")
    print("   - Subdirectory name for file extraction during processing")
    print(f"   - Full path will be: {base_dir}[subdirectory]/")
    temp_dir = get_user_input("Enter temp subdirectory name", default="temp")
    
    # Keep Downloaded Files
    print("\n4. Keep Downloaded Files:")
    print("   - Keep 7z files after update for faster future updates")
    print("   - Recommended: Yes (saves bandwidth and time)")
    keep_files = get_boolean_input("Keep downloaded files after update?", default=True)
    
    # Auto Cleanup Days
    print("\n5. Auto Cleanup:")
    print("   - Automatically delete old files after specified days")
    print("   - Set to 0 to disable auto cleanup")
    cleanup_days = get_integer_input("Days to keep old files", default=30, min_value=0, max_value=365)
    
    return {
        'base_directory': base_dir,
        'download_directory': download_dir,
        'temp_directory': temp_dir,
        'keep_downloaded_files': keep_files,
        'auto_cleanup_days': cleanup_days
    }

def setup_server_config(server_name):
    """Setup configuration for a single server (dev/live)"""
    print(f"\n🖥️  {server_name.title()} Server Configuration")
    print("-" * 40)
    
    # Server Files Path
    print(f"1. {server_name.title()} Server Files Path:")
    print("   - Path to your FiveM server files directory")
    print(f"   - Example: G:/GTAV/{server_name}/server")
    server_files = get_user_input(f"Enter {server_name} server files path")
    
    # ServerData Path (optional)
    print(f"\n2. {server_name.title()} ServerData Path (optional):")
    print("   - Path to server data/configuration files")
    print("   - Leave empty if ServerData is inside the server folder")
    print(f"   - Example: G:/GTAV/{server_name}/server-data")
    server_data = get_user_input(f"Enter {server_name} ServerData path", default="", required=False)
    
    # Management Method
    print(f"\n3. {server_name.title()} Server Management Method:")
    print("   - Choose how to start/stop this server")
    print("   - [1] TCAdmin (command-line, most reliable)")
    print("   - [2] Windows Service (direct service control)")
    print("   - [3] File operations only (no server management)")
    
    while True:
        choice = get_user_input("Choose management method [1-3]", default="1")
        if choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    config = {
        'ServerFiles': f'"{server_files}"',
        'TCADMIN_Enabled': 'False',
        'Service_Enabled': 'False'
    }
    
    if server_data:
        config['ServerData'] = f'"{server_data}"'
    
    if choice == '1':  # TCAdmin
        config['TCADMIN_Enabled'] = 'True'
        
        print(f"\n   TCAdmin Configuration for {server_name}:")
        print("   - Path to TCAdminServiceBrowser.exe")
        print("   - Usually: C:\\TCAdmin2\\Monitor\\TCAdminServiceBrowser.exe")
        tcadmin_exe = get_user_input("Enter TCAdminServiceBrowser.exe path", 
                                   default="C:\\TCAdmin2\\Monitor\\TCAdminServiceBrowser.exe")
        
        print("   - Service ID from TCAdmin panel")
        print("   - Found in URL: /Service/Details/12345 → ID is 12345")
        service_id = get_user_input(f"Enter {server_name} service ID")
        
        config['tcadmin_executable'] = tcadmin_exe
        config['tcadmin_service_id'] = service_id
        
    elif choice == '2':  # Windows Service
        config['Service_Enabled'] = 'True'
        
        print(f"\n   Windows Service Configuration for {server_name}:")
        print("   - Name of the Windows service")
        print("   - Check 'services.msc' for exact name")
        print("   - Example: FXServer")
        service_name = get_user_input(f"Enter {server_name} service name")
        
        config['Service_Name'] = f'"{service_name}"'
    
    # choice == '3' (File operations only) - no additional config needed
    
    return config

def create_config_file(discord_config, file_config, dev_config, live_config):
    """Create the configuration file"""
    config = configparser.ConfigParser()
    
    # Discord section
    config['discord'] = {}
    for key, value in discord_config.items():
        config['discord'][key] = value
    
    # File management section
    config['files'] = {}
    for key, value in file_config.items():
        if isinstance(value, bool):
            config['files'][key] = str(value).lower()
        else:
            config['files'][key] = str(value)
    
    # Server sections
    config['dev'] = dev_config
    config['live'] = live_config
    
    # Write config file
    config_path = Path('config.ini')
    with open(config_path, 'w') as f:
        config.write(f)
    
    print(f"\n✅ Configuration file created: {config_path.absolute()}")

def test_configuration():
    """Test the configuration"""
    print("\n🧪 Testing Configuration")
    print("-" * 40)
    
    try:
        # Test config file loading
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Check required sections
        required_sections = ['discord', 'files', 'dev', 'live']
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            print(f"❌ Missing sections: {', '.join(missing_sections)}")
            return False
        
        # Check Discord token
        if not config.get('discord', 'discord_token') or config.get('discord', 'discord_token') == 'your_discord_bot_token_here':
            print("❌ Discord token not set properly")
            return False
        
        # Check file directories and create them
        base_dir = config.get('files', 'base_directory')
        download_dir = config.get('files', 'download_directory')
        temp_dir = config.get('files', 'temp_directory')
        
        base_path = Path(base_dir)
        download_path = base_path / download_dir
        temp_path = base_path / temp_dir
        
        try:
            base_path.mkdir(parents=True, exist_ok=True)
            download_path.mkdir(parents=True, exist_ok=True)
            temp_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directories:")
            print(f"   - Base: {base_path.absolute()}")
            print(f"   - Downloads: {download_path.absolute()}")
            print(f"   - Temp: {temp_path.absolute()}")
        except Exception as e:
            print(f"❌ Failed to create directories: {e}")
            return False
        
        # Validate server configurations
        for server_type in ['dev', 'live']:
            if server_type in config:
                server_files = config.get(server_type, 'ServerFiles', fallback='').strip('"')
                if not server_files:
                    print(f"❌ {server_type}: ServerFiles path not set")
                    return False
                
                tcadmin_enabled = config.getboolean(server_type, 'TCADMIN_Enabled', fallback=False)
                service_enabled = config.getboolean(server_type, 'Service_Enabled', fallback=False)
                
                if tcadmin_enabled:
                    tcadmin_exe = config.get(server_type, 'tcadmin_executable', fallback='')
                    service_id = config.get(server_type, 'tcadmin_service_id', fallback='')
                    if not tcadmin_exe or not service_id:
                        print(f"❌ {server_type}: TCAdmin configuration incomplete")
                        return False
                
                if service_enabled:
                    service_name = config.get(server_type, 'Service_Name', fallback='').strip('"')
                    if not service_name:
                        print(f"❌ {server_type}: Service name not set")
                        return False
        
        print("✅ Configuration validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def show_setup_summary(discord_config, file_config, dev_config, live_config):
    """Show setup summary"""
    print("\n📋 Setup Summary")
    print("-" * 40)
    
    print(f"🤖 Bot Commands:")
    print(f"   Prefix: {discord_config['command_prefix']}")
    print(f"   Update: {discord_config['command_prefix']}{discord_config['update_command']}")
    print(f"   Download: {discord_config['command_prefix']}{discord_config['download_command']}")
    print(f"   Status: {discord_config['command_prefix']}{discord_config['status_command']}")
    print(f"   Backups: {discord_config['command_prefix']}{discord_config['backups_command']}")
    print(f"   Start/Stop: {discord_config['command_prefix']}{discord_config['start_command']}/{discord_config['command_prefix']}{discord_config['stop_command']}")
    
    print(f"\n📁 File Management:")
    base_path = Path(file_config['base_directory'])
    print(f"   Base: {base_path.absolute()}")
    print(f"   Downloads: {(base_path / file_config['download_directory']).absolute()}")
    print(f"   Keep files: {'Yes' if file_config['keep_downloaded_files'] else 'No'}")
    print(f"   Auto cleanup: {file_config['auto_cleanup_days']} days")
    
    print(f"\n🖥️  Server Management:")
    for server_type, config in [('Dev', dev_config), ('Live', live_config)]:
        server_files = config['ServerFiles'].strip('"')
        tcadmin_enabled = config['TCADMIN_Enabled'] == 'True'
        service_enabled = config['Service_Enabled'] == 'True'
        
        if tcadmin_enabled:
            mgmt_type = f"TCAdmin (Service ID: {config['tcadmin_service_id']})"
        elif service_enabled:
            mgmt_type = f"Windows Service ({config['Service_Name'].strip('\"')})"
        else:
            mgmt_type = "File operations only"
        
        print(f"   {server_type}: {server_files}")
        print(f"   └─ Management: {mgmt_type}")

def main():
    """Main setup function"""
    print_header()
    
    # Check if config already exists
    if os.path.exists('config.ini'):
        print("⚠️  Configuration file already exists!")
        overwrite = get_boolean_input("Do you want to overwrite the existing config?", default=False)
        if not overwrite:
            print("Setup cancelled.")
            return
        print()
    
    try:
        # Setup configurations step by step
        discord_config = setup_discord_config()
        if not discord_config:
            print("❌ Discord configuration failed!")
            return
        
        file_config = setup_file_config()
        dev_config = setup_server_config('dev')
        live_config = setup_server_config('live')
        
        # Create config file
        create_config_file(discord_config, file_config, dev_config, live_config)
        
        # Test configuration
        if test_configuration():
            show_setup_summary(discord_config, file_config, dev_config, live_config)
            
            print("\n🎉 Setup completed successfully!")
            print("\n📝 Next steps:")
            print("1. Start the bot: python main.py")
            print("2. Invite your bot to Discord using the URL shown above")
            print("3. Test with a command like: !status")
            print("4. Try updating a server: !update 17346 dev")
            
            print("\n💡 Pro Tips:")
            print("- Use !help to see all available commands")
            print("- Backups are created automatically before each update")
            print("- Use !backups list dev to see available backups")
            print("- Use !rollback dev backup_name to restore from backup")
            print("- Each server can use different management methods")
            
        else:
            print("❌ Setup completed but configuration test failed!")
            print("Please check config.ini manually or run setup again.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check your inputs and try again.")

if __name__ == "__main__":
    main() 