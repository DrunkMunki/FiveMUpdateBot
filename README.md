# FiveM Update Bot

A comprehensive Discord bot for automating FiveM server management, updates, and backups with support for both TCAdmin and Windows Service integration.

## 🚀 Features

### 📥 **Artifact Management**
- 🔄 **Automated FiveM Updates**: Download and install server artifacts from FiveM repository
- 💾 **Smart Caching**: Reuse downloaded files for faster operations
- ⚡ **Pre-Download**: Download artifacts without updating servers
- 🧹 **Automatic Cleanup**: Configurable cleanup of old downloaded files

### 🔧 **Server Management**
- 🖥️ **TCAdmin Integration**: Command-line based server control (reliable, no web auth issues)
- ⚙️ **Windows Service Support**: Direct Windows service management
- 🌐 **Mixed Environments**: Different management methods per server (dev/live)
- ▶️ **Independent Control**: Start/stop servers without updating
- 📊 **Status Monitoring**: Real-time server status checking

### 💾 **Backup & Restore System**
- 🛡️ **Automatic Backups**: Server files backed up before every update
- 📝 **Version Tracking**: Smart backup naming based on current server version
- 📊 **ServerData Protection**: Separate backup/restore of server configurations and data
- 🔄 **Complete Rollback**: Restore servers to any previous backup
- 🗂️ **Backup Management**: List, delete, and organize server backups

### 🔒 **Security & Access Control**
- 🎭 **Role-Based Access**: Discord role restrictions
- 👤 **Individual Permissions**: Granular user-specific access control
- 📢 **Channel Restrictions**: Limit bot responses to designated channels
- 🔐 **Per-Server Security**: Different access levels for different servers

### ⚙️ **Flexible Configuration**
- 🎯 **Per-Server Settings**: Independent configuration for each server type
- 📝 **Customizable Commands**: Configure all command names and prefixes
- 🔧 **Multiple Management Types**: TCAdmin, Windows Service, or File-only per server
- 📍 **Custom Paths**: Configurable file locations and ServerData paths

## 📋 Commands

All commands respect your configured prefix (default `!`) and can be customized.

### 📥 **Download & Update**
```
!download <artifact_number> [force]
```
Download artifact without updating server
- `!download 17346` - Download artifact 17346
- `!download 17346 force` - Re-download even if cached

```
!update <artifact_number> <server_type>
```
Update server with new artifact (includes automatic backup)
- `!update 17346 dev` - Update dev server
- `!update 17346 live` - Update live server

### 🔧 **Server Management**
```
!start <server_type>
```
Start server (TCAdmin or Windows Service)
- `!start dev` - Start development server
- `!start live` - Start live server

```
!stop <server_type>
```
Stop server (TCAdmin or Windows Service)
- `!stop dev` - Stop development server
- `!stop live` - Stop live server

```
!status [server_type]
```
Check server status and version
- `!status` - Check all servers
- `!status dev` - Check specific server

### 💾 **Backup & Restore**
```
!backups <action> <server_type> [backup_name]
```
Manage server backups
- `!backups list dev` - List all dev server backups
- `!backups delete dev server_backup_17346` - Delete specific backup
- `!backups delete dev all` - Delete all dev backups

```
!rollback <server_type> <backup_name>
```
Restore server from backup
- `!rollback dev server_backup_17346` - Restore dev server from backup

### 📋 **Information**
```
!version [server_type]
```
Check current server versions
- `!version` - Check all server versions
- `!version live` - Check specific server version

```
!config
```
Display current bot configuration

```
!help
```
Show all available commands with examples

### 🧹 **Maintenance**
```
!cleanup [days]
```
Clean up old downloaded files
- `!cleanup` - Use default cleanup period
- `!cleanup 7` - Delete files older than 7 days

## ⚙️ Configuration

The bot uses `config.ini` for all settings. Copy `config.ini.example` and customize for your setup.

### 📢 **Discord Configuration**
```ini
[discord]
discord_token = your_discord_bot_token_here
command_prefix = !
response_channel = 1234567890123456789  # Optional: restrict to specific channel
allowed_roles = 1234567890123456789     # Optional: comma-separated role IDs
allowed_discord_users = 987654321098765432  # Optional: comma-separated user IDs

# Customize command names (optional)
update_command = update
download_command = download
start_command = start
stop_command = stop
status_command = status
version_command = version
backups_command = backups
rollback_command = rollback
cleanup_command = cleanup
config_command = config
help_command = help
```

### 📁 **File Management**
```ini
[files]
base_directory = ./bot_files/          # Base directory for all bot files
download_directory = downloads         # Subdirectory for artifact cache
temp_directory = temp                  # Subdirectory for temporary files
keep_downloaded_files = true           # Keep downloaded artifacts for reuse
auto_cleanup_days = 30                 # Auto-delete files older than X days (0 = disabled)
```

### 🖥️ **Server Configuration**

Configure each server type independently with different management methods:

#### **Option 1: TCAdmin (Command Line)**
```ini
[dev]
ServerFiles = "G:/GTAV/dev/server"
ServerData = "G:/GTAV/dev/server-data"  # Optional: separate server data location
TCADMIN_Enabled = True
Service_Enabled = False
tcadmin_executable = C:\TCAdmin2\Monitor\TCAdminServiceBrowser.exe
tcadmin_service_id = 23
```

#### **Option 2: Windows Service**
```ini
[live]
ServerFiles = "G:/GTAV/live/server"
TCADMIN_Enabled = False
Service_Enabled = True
Service_Name = "FXServer"
```

#### **Option 3: File Operations Only**
```ini
[staging]
ServerFiles = "G:/GTAV/staging/server"
TCADMIN_Enabled = False
Service_Enabled = False
# No server management - file updates only
```

#### **Mixed Environment Example**
```ini
[dev]
# Development uses TCAdmin
ServerFiles = "G:/GTAV/dev/server"
TCADMIN_Enabled = True
Service_Enabled = False
tcadmin_executable = C:\TCAdmin2\Monitor\TCAdminServiceBrowser.exe
tcadmin_service_id = 23

[live]
# Production uses Windows Service
ServerFiles = "G:/GTAV/live/server"
ServerData = "G:/GTAV/live/server-data"
TCADMIN_Enabled = False
Service_Enabled = True
Service_Name = "FXServer"
```

## 🔧 Setup Instructions

### 1. **Prerequisites**
- Python 3.8+
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- FiveM Server (Windows)
- TCAdmin (optional) or Windows Service setup

### 2. **Discord Bot Setup**
1. **Create Discord Application**: Go to [Discord Developer Portal](https://discord.com/developers/applications) and create new application
2. **Create Bot**: In your application, go to "Bot" section and create a bot
3. **Copy Token**: Save your bot token for the configuration file
4. **Invite Bot**: Use this URL template to invite your bot (replace `YOUR_APPLICATION_ID` with your actual application ID):

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=379904&scope=bot
```

**Required Permissions** (included in the URL above):
- ✅ Send Messages
- ✅ Read Messages
- ✅ Read Message History
- ✅ Use External Emojis
- ✅ Embed Links
- ✅ Attach Files

**Finding Your Application ID:**
- Go to your Discord Developer Portal
- Select your application
- Copy the "Application ID" from the General Information page

**Example Invite URL:**
```
https://discord.com/api/oauth2/authorize?client_id=123456789012345678&permissions=379904&scope=bot
```

### 3. **Installation**
```bash
# Clone or download the repository
git clone https://github.com/DrunkMunki/FiveMUpdateBot.git
cd FiveMUpdateBot

# Install Python dependencies
pip install -r requirements.txt

# Copy example configuration
copy config.ini.example config.ini
```

### 4. **Configuration**
Edit `config.ini` with your settings:

1. **Discord Token**: Add your bot token from Discord Developer Portal
2. **Server Paths**: Set your FiveM server file locations
3. **Management Method**: Choose TCAdmin, Windows Service, or File-only for each server
4. **Permissions**: Configure Discord roles/users who can use the bot

### 5. **TCAdmin Setup** (if using TCAdmin)
1. **Find TCAdminServiceBrowser.exe**: Usually in `C:\TCAdmin2\Monitor\`
2. **Get Service IDs**: Check TCAdmin panel URLs (`/Service/Details/12345` → ID is `12345`)
3. **Test Command**: Run `C:\TCAdmin2\Monitor\TCAdminServiceBrowser.exe -service=YOUR_ID -command=stop`

### 6. **Run the Bot**
```bash
# Start the bot
python main.py

# Or use the batch file (Windows)
start_bot.bat
```

## 🔄 Update Process Flow

1. **🔍 Artifact Lookup**: Bot checks FiveM repository for requested artifact
2. **💾 Cache Check**: Uses cached file if available (unless `force` specified)
3. **📥 Download**: Downloads artifact if not cached
4. **💾 Backup Creation**: Creates version-aware backup of current server files
5. **📊 ServerData Backup**: Backs up server data separately (if configured)
6. **⏹️ Server Stop**: Stops server using configured method (TCAdmin/Service)
7. **🔒 File Lock Check**: Ensures no processes are locking server files
8. **📦 Extraction**: Extracts new artifact to temporary location
9. **📁 File Copy**: Updates server files with new content
10. **📊 ServerData Restore**: Restores server data from backup
11. **📝 Version Tracking**: Creates `version.txt` with current artifact number
12. **▶️ Server Start**: Starts server using configured method
13. **🧹 Cleanup**: Removes temporary files (keeps cache if configured)

## 💾 Backup System

### **Intelligent Backup Naming**
- **Version-aware**: `server_backup_17346` (uses current version from `version.txt`)
- **Incremental**: `server_bak1`, `server_bak2` (if no version info)
- **Collision avoidance**: Automatically adds numbers to prevent overwrites

### **Backup Types**
- **🖥️ Server Files**: Complete server directory backup
- **📊 ServerData**: Separate backup of configurations, databases, resources
- **🖥️💾 Combined**: Server backups that include ServerData inside

### **Backup Locations**
Backups are created in the parent directory of your server files:
```
G:/GTAV/
├── dev/
│   ├── server/              # Current server files
│   ├── server_backup_17346/ # Previous version backup
│   └── server_backup_17200/ # Older version backup
└── live/
    ├── server/              # Current server files
    └── server_backup_17400/ # Previous version backup
```

## 🛡️ Security Features

### **Access Control**
- **Role-based**: Restrict commands to specific Discord roles
- **User-specific**: Grant access to individual users regardless of roles
- **Channel restriction**: Limit bot responses to designated channels
- **Per-command control**: Same security applies to all commands

### **Example Permissions**
```ini
[discord]
# Allow these roles to use the bot
allowed_roles = 123456789,987654321

# Also allow these specific users (even if they don't have the role)
allowed_discord_users = 111222333444555666,777888999000111222

# Optional: Only respond in this channel
response_channel = 555666777888999000
```

## 📊 Status Information

### **Server Status Display**
```discord
!status
Dev: ✅ Running - Version: 17346 (TCAdmin)
Live: ✅ Running - Version: 17400 (Service (FXServer))

!status dev
✅ Dev Server: Running (Version: 17346)
🔧 Management: TCAdmin
```

### **Version Tracking**
Each server maintains a `version.txt` file with the current artifact version:
```
G:/GTAV/dev/server/version.txt  → Contains: 17346
G:/GTAV/live/server/version.txt → Contains: 17400
```

## 🧹 File Management

### **Directory Structure**
```
{base_directory}/           # Configured base directory
├── downloads/              # Artifact cache
│   ├── 17346.7z           # Cached artifacts
│   └── 17400.7z
└── temp/                  # Temporary extraction
    └── extract_17346_*/   # Temporary folders (auto-deleted)
```

### **Cleanup Options**
- **Automatic**: Delete files older than configured days
- **Manual**: Use `!cleanup` command
- **Startup**: Clean old files when bot starts
- **Disable**: Set `auto_cleanup_days = 0` to disable

## 🔧 Advanced Features

### **Mixed Server Management**
Run different servers with different management methods:
- **Dev Server**: TCAdmin for full control panel integration
- **Live Server**: Windows Service for simple, reliable operation
- **Test Server**: File-only for development environments

### **ServerData Management**
- **Automatic Detection**: Finds ServerData in existing server backups
- **Flexible Paths**: Configure separate ServerData locations
- **Preservation**: ServerData is backed up and restored during updates
- **Fallback Handling**: Copies ServerData from artifacts for initial setup

### **Error Recovery**
- **Automatic Restart**: Tries to restart servers if update fails
- **Backup Restoration**: Easy rollback if updates cause issues
- **File Lock Detection**: Identifies and waits for locked files
- **Detailed Logging**: Comprehensive error information

## 🚨 Troubleshooting

### **Common Issues**

#### **"tcadmin_executable is required when TCADMIN_Enabled=True"**
- Add `tcadmin_executable = C:\TCAdmin2\Monitor\TCAdminServiceBrowser.exe`
- Verify the path exists and is accessible

#### **"Service 'FXServer' not found"**
- Check Windows Service name is correct
- Use `services.msc` to verify service exists
- Ensure bot has permission to control services

#### **"Download failed: Artifact not found"**
- Verify artifact number exists on FiveM repository
- Check internet connection
- Try a different artifact number

#### **"No server management configured"**
- Set either `TCADMIN_Enabled = True` or `Service_Enabled = True`
- Configure the required fields for your chosen method

### **Testing Configuration**
```bash
# Test TCAdmin command (replace with your service ID)
C:\TCAdmin2\Monitor\TCAdminServiceBrowser.exe -service=23 -command=stop

# Test Windows Service
sc query "FXServer"
sc stop "FXServer"
sc start "FXServer"
```

## 📁 File Structure

```
FiveMUpdateBot/
├── main.py                 # Main bot application
├── config.ini             # Your configuration (create from example)
├── config.ini.example     # Example configuration with comments
├── requirements.txt       # Python dependencies
├── README.md              # This documentation
├── artifacts.txt          # Artifact URL cache (auto-generated)
└── setup_environment.py   # Interactive setup script (optional)
```

## 🆕 What's New

This bot has been extensively enhanced with enterprise-level features:

### **Version 2.0 Features**
- ✅ **Per-server configuration** - Mixed TCAdmin/Service environments
- ✅ **Command-line TCAdmin** - Reliable, no web authentication issues
- ✅ **Windows Service integration** - Direct service control
- ✅ **Intelligent backup system** - Version-aware naming and management
- ✅ **ServerData protection** - Separate backup/restore of server configurations
- ✅ **Independent server control** - Start/stop without updating
- ✅ **Rollback functionality** - Restore from any backup
- ✅ **Enhanced permissions** - Individual user access control
- ✅ **Version tracking** - Automatic version.txt management
- ✅ **Mixed management types** - Different methods per server

## 📄 License

This project is provided as-is for educational and personal use. Please ensure compliance with:
- FiveM's Terms of Service
- Discord's Developer Terms of Service
- Your server hosting provider's policies

## 🤝 Support

For issues and questions:
1. **Check this README** - Most common issues are covered
2. **Review your configuration** - Use `!config` command to verify settings
3. **Test components individually** - Try TCAdmin/Service commands manually
4. **Check file permissions** - Ensure bot can read/write to configured paths
5. **Verify Discord permissions** - Ensure bot has necessary Discord permissions
