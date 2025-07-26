import discord
from discord.ext import commands
import configparser
import aiohttp
import asyncio
import os
import subprocess
import shutil
import tempfile
import py7zr
from pathlib import Path
import logging
import time
import psutil

from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FiveMUpdateBot(commands.Bot):
    def __init__(self):
        # Load config first to get command prefix
        self.config = configparser.ConfigParser()
        self.load_config()
        
        # Get command prefix from config
        command_prefix = self.config.get('discord', 'command_prefix', fallback='!')
        
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=command_prefix, intents=intents, help_command=None)
        
        # Discord configuration
        self.response_channel_id = None
        self.allowed_roles = []
        self.allowed_users = []
        self.command_prefix = command_prefix
        self.command_names = {}
        
        # File management configuration
        self.file_config = {}
        
        self.setup_discord_config()
        self.setup_file_config()
        self.setup_commands()
    
    def load_config(self):
        """Load configuration from config.ini"""
        try:
            self.config.read('config.ini')
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def setup_discord_config(self):
        """Setup Discord-specific configuration"""
        try:
            if 'discord' in self.config:
                # Get response channel ID
                if 'response_channel' in self.config['discord']:
                    self.response_channel_id = int(self.config['discord']['response_channel'])
                
                # Get allowed roles
                if 'allowed_roles' in self.config['discord']:
                    roles_str = self.config['discord']['allowed_roles']
                    if roles_str.strip():
                        self.allowed_roles = [int(role.strip()) for role in roles_str.split(',')]
                
                # Get allowed users
                if 'allowed_discord_users' in self.config['discord']:
                    users_str = self.config['discord']['allowed_discord_users']
                    if users_str.strip():
                        self.allowed_users = [int(user.strip()) for user in users_str.split(',')]
                
                # Get command prefix
                self.command_prefix = self.config.get('discord', 'command_prefix', fallback='!')
                
                # Get command names
                self.command_names = {
                    'update': self.config.get('discord', 'update_command', fallback='update'),
                    'download': self.config.get('discord', 'download_command', fallback='download'),
                    'status': self.config.get('discord', 'status_command', fallback='status'),
                    'version': self.config.get('discord', 'version_command', fallback='version'),
                    'config': self.config.get('discord', 'config_command', fallback='config'),
                    'help': self.config.get('discord', 'help_command', fallback='help'),
                    'cleanup': self.config.get('discord', 'cleanup_command', fallback='cleanup'),
                    'backups': self.config.get('discord', 'backups_command', fallback='backups'),
                    'rollback': self.config.get('discord', 'rollback_command', fallback='rollback'),
                    'stop': self.config.get('discord', 'stop_command', fallback='stop'),
                    'start': self.config.get('discord', 'start_command', fallback='start')
                }
                
                logger.info(f"Discord config loaded - Channel: {self.response_channel_id}, Roles: {self.allowed_roles}, Users: {self.allowed_users}, Prefix: {self.command_prefix}")
                logger.info(f"Command names: {self.command_names}")
        except Exception as e:
            logger.error(f"Error loading Discord config: {e}")
    
    def get_server_config(self, server_type):
        """Get server-specific configuration for TCAdmin or Windows Service"""
        if server_type not in self.config:
            return None
        
        server_config = {
            'tcadmin_enabled': self.config.getboolean(server_type, 'TCADMIN_Enabled', fallback=False),
            'service_enabled': self.config.getboolean(server_type, 'Service_Enabled', fallback=False),
            'service_name': self.config.get(server_type, 'Service_Name', fallback=''),
            'server_files': self.config.get(server_type, 'ServerFiles', fallback='').strip('"'),
            'server_data': self.config.get(server_type, 'ServerData', fallback='').strip('"') or None
        }
        
        # Add TCAdmin specific config if enabled
        if server_config['tcadmin_enabled']:
            server_config.update({
                'tcadmin_executable': self.config.get(server_type, 'tcadmin_executable', fallback=''),
                'tcadmin_service_id': self.config.get(server_type, 'tcadmin_service_id', fallback='')
            })
            
            # Validate TCAdmin required fields
            required_fields = ['tcadmin_executable', 'tcadmin_service_id']
            for field in required_fields:
                if not server_config.get(field):
                    logger.error(f"{server_type}: {field} is required when TCADMIN_Enabled=True")
                    raise Exception(f"{server_type}: {field} is required when TCADMIN_Enabled=True")
        
        # Validate Service config if enabled
        if server_config['service_enabled']:
            if not server_config['service_name']:
                logger.error(f"{server_type}: Service_Name is required when Service_Enabled=True")
                raise Exception(f"{server_type}: Service_Name is required when Service_Enabled=True")
        
        # Must have either TCAdmin or Service enabled (or neither for file-only mode)
        if not server_config['tcadmin_enabled'] and not server_config['service_enabled']:
            logger.info(f"{server_type}: Neither TCAdmin nor Service management enabled - file operations only")
        
        return server_config
    
    def setup_file_config(self):
        """Setup file management configuration"""
        try:
            if 'files' not in self.config:
                # Use defaults if section doesn't exist
                self.file_config = {
                    'base_directory': './bot_files/',
                    'download_directory': 'downloads',
                    'temp_directory': 'temp',
                    'keep_downloaded_files': True,
                    'auto_cleanup_days': 30
                }
                logger.info("Using default file management settings")
            else:
                self.file_config = {
                    'base_directory': self.config.get('files', 'base_directory', fallback='./bot_files/'),
                    'download_directory': self.config.get('files', 'download_directory', fallback='downloads'),
                    'temp_directory': self.config.get('files', 'temp_directory', fallback='temp'),
                    'keep_downloaded_files': self.config.getboolean('files', 'keep_downloaded_files', fallback=True),
                    'auto_cleanup_days': self.config.getint('files', 'auto_cleanup_days', fallback=30)
                }
            
            # Create full paths by combining base directory with subdirectories
            base_path = Path(self.file_config['base_directory'])
            
            # Ensure base directory path ends with separator for clean joining
            if not str(base_path).endswith(('/', '\\')):
                base_path = Path(str(base_path) + '/')
            
            # Create full paths for download and temp directories
            self.file_config['full_download_path'] = base_path / self.file_config['download_directory']
            self.file_config['full_temp_path'] = base_path / self.file_config['temp_directory']
            
            # Create directories if they don't exist
            self.file_config['full_download_path'].mkdir(parents=True, exist_ok=True)
            self.file_config['full_temp_path'].mkdir(parents=True, exist_ok=True)
            
            logger.info(f"File management configured:")
            logger.info(f"  Base directory: {base_path.absolute()}")
            logger.info(f"  Download directory: {self.file_config['full_download_path'].absolute()}")
            logger.info(f"  Temp directory: {self.file_config['full_temp_path'].absolute()}")
            logger.info(f"  Keep files: {self.file_config['keep_downloaded_files']}")
            logger.info(f"  Auto cleanup: {self.file_config['auto_cleanup_days']} days")
            
        except Exception as e:
            logger.error(f"Error setting up file management: {e}")
            raise
    
    def get_artifact_filename(self, artifact_number, artifact_hash=None):
        """Generate filename for artifact"""
        return f"{artifact_number}.7z"
    
    def cleanup_old_files(self, days_old=None):
        """Clean up old downloaded files"""
        if days_old is None:
            days_old = self.file_config['auto_cleanup_days']
        
        if days_old <= 0:
            return 0  # Don't cleanup if set to 0 or negative
        
        download_path = Path(self.file_config['full_download_path'])
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        
        try:
            for file_path in download_path.glob('*.7z'):
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Cleaned up old file: {file_path.name}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def check_file_locks(self, directory_path, max_retries=3, retry_delay=2):
        """Check if files in directory are locked and wait for them to be released"""
        logger.info(f"Checking for file locks in: {directory_path}")
        
        for attempt in range(max_retries):
            locked_files = []
            
            try:
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.is_file_locked(file_path):
                            locked_files.append(file_path)
                
                if not locked_files:
                    logger.info("No file locks detected")
                    return True
                
                logger.warning(f"Attempt {attempt + 1}: Found {len(locked_files)} locked files")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                
            except Exception as e:
                logger.error(f"Error checking file locks: {e}")
                return False
        
        logger.error(f"Files still locked after {max_retries} attempts")
        return False
    
    def is_file_locked(self, file_path):
        """Check if a specific file is locked"""
        try:
            # Try to open file in write mode to check if it's locked
            with open(file_path, 'r+b'):
                pass
            return False
        except (IOError, OSError):
            # Check if any process has the file open
            try:
                for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                    try:
                        if proc.info['open_files']:
                            for file_info in proc.info['open_files']:
                                if file_info.path == file_path:
                                    logger.warning(f"File {file_path} is locked by process {proc.info['name']} (PID: {proc.info['pid']})")
                                    return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass
            return True
    
    async def tcadmin_command(self, server_config, command):
        """Execute TCAdmin command using TCAdminServiceBrowser.exe"""
        try:
            import subprocess
            
            executable = server_config['tcadmin_executable']
            service_id = server_config['tcadmin_service_id']
            
            # Build command arguments
            cmd_args = [executable, f"-service={service_id}", f"-command={command}"]
            
            logger.info(f"Executing TCAdmin command: {' '.join(cmd_args)}")
            
            # Execute the command
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"TCAdmin command successful: {result.stdout.strip()}")
                return result.stdout.strip()
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                logger.error(f"TCAdmin command failed: {error_msg}")
                raise Exception(f"TCAdmin command failed: {error_msg}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"TCAdmin command timed out")
            raise Exception("TCAdmin command timed out")
        except Exception as e:
            logger.error(f"Error executing TCAdmin command: {e}")
            raise
    
    async def start_windows_service(self, service_name):
        """Start Windows service"""
        try:
            import subprocess
            result = subprocess.run(['sc', 'start', service_name], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Windows service {service_name} start command sent")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                # Check if service is already running
                if "already running" in error_msg.lower() or "running" in error_msg.lower():
                    logger.info(f"Windows service {service_name} is already running")
                    return True
                else:
                    raise Exception(f"Service start failed: {error_msg}")
        except Exception as e:
            logger.error(f"Error starting Windows service {service_name}: {e}")
            raise
    
    async def stop_windows_service(self, service_name):
        """Stop Windows service"""
        try:
            import subprocess
            result = subprocess.run(['sc', 'stop', service_name], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Windows service {service_name} stop command sent")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                # Check if service is already stopped
                if "not started" in error_msg.lower() or "stopped" in error_msg.lower():
                    logger.info(f"Windows service {service_name} is already stopped")
                    return True
                else:
                    raise Exception(f"Service stop failed: {error_msg}")
        except Exception as e:
            logger.error(f"Error stopping Windows service {service_name}: {e}")
            raise
    
    async def get_windows_service_status(self, service_name):
        """Get Windows service status"""
        try:
            import subprocess
            result = subprocess.run(['sc', 'query', service_name], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "RUNNING" in output:
                    return "running"
                elif "STOPPED" in output:
                    return "stopped"
                else:
                    return "unknown"
            else:
                return "not_found"
        except Exception as e:
            logger.error(f"Error getting Windows service status for {service_name}: {e}")
            return "error"
    

    
    async def stop_server(self, server_config):
        """Stop server using configured method (TCAdmin or Windows Service)"""
        try:
            if server_config['tcadmin_enabled']:
                response = await self.tcadmin_command(server_config, 'stop')
                logger.info(f"TCAdmin service {server_config['tcadmin_service_id']} stopped: {response}")
                await asyncio.sleep(2)
                return True
            elif server_config['service_enabled']:
                await self.stop_windows_service(server_config['service_name'])
                await asyncio.sleep(3)
                return True
            else:
                logger.info("No server management configured - skipping stop")
                return True
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            raise
    
    async def start_server(self, server_config):
        """Start server using configured method (TCAdmin or Windows Service)"""
        try:
            if server_config['tcadmin_enabled']:
                response = await self.tcadmin_command(server_config, 'start')
                logger.info(f"TCAdmin service {server_config['tcadmin_service_id']} started: {response}")
                return True
            elif server_config['service_enabled']:
                await self.start_windows_service(server_config['service_name'])
                return True
            else:
                logger.info("No server management configured - skipping start")
                return True
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            raise
    
    async def get_server_status(self, server_config):
        """Get server status using configured method (TCAdmin or Windows Service)"""
        try:
            if server_config['tcadmin_enabled']:
                # TCAdmin command line doesn't have a direct status command
                # We'll try to infer status from attempting a restart command or return unknown
                # For now, return unknown since command line tool doesn't support status checking
                logger.info("TCAdmin command line tool doesn't support status checking")
                return "unknown"
            elif server_config['service_enabled']:
                return await self.get_windows_service_status(server_config['service_name'])
            else:
                return "no_management"
        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return "error"
    
    def setup_commands(self):
        """Setup bot commands with configured names"""
        
        # Create download command
        @commands.command(name=self.command_names['download'])
        async def download_artifact(ctx, artifact_number: str = None, force: str = None):
            """Download FiveM artifact without updating server"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            # Check if artifact number is provided
            if not artifact_number:
                await ctx.send(f"""❌ **Missing artifact number!**

**Usage:** `{self.command_prefix}{self.command_names['download']} <artifact_number> [force]`

**Parameters:**
• `artifact_number` - The FiveM artifact number (e.g., 16636, 17346)
• `force` - Optional: use 'force' to re-download even if file exists

**Examples:**
• `{self.command_prefix}{self.command_names['download']} 17346`
• `{self.command_prefix}{self.command_names['download']} 17346 force`""")
                return
            
            # Check if force download was requested
            force_download = force and force.lower() == 'force'
            
            await ctx.send(f"📥 Starting download for artifact {artifact_number}" + (" (forced)" if force_download else ""))
            
            try:
                async with aiohttp.ClientSession() as session:
                    artifact_file, _ = await self.download_or_find_artifact(artifact_number, session, ctx, force_download)
                
                # Get file info
                file_path = Path(artifact_file)
                file_size = file_path.stat().st_size
                file_size_mb = file_size / 1024 / 1024
                
                await ctx.send(f"""✅ **Download completed successfully!**
📁 **File:** `{file_path.name}`
📊 **Size:** {file_size_mb:.1f} MB
📍 **Location:** `{file_path.parent}`

ℹ️ Use `{self.command_prefix}{self.command_names['update']} {artifact_number} <server_type>` to update a server with this artifact.""")
                
            except Exception as e:
                logger.error(f"Download failed: {e}")
                await ctx.send(f"❌ Download failed: {str(e)}")
        
        # Create update command
        @commands.command(name=self.command_names['update'])
        async def update_server(ctx, artifact_number: str = None, server_type: str = None):
            """Update FiveM server files"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            # Check if required parameters are provided
            if not artifact_number or not server_type:
                await ctx.send(f"""❌ **Missing required parameters!**

**Usage:** `{self.command_prefix}{self.command_names['update']} <artifact_number> <server_type>`

**Parameters:**
• `artifact_number` - The FiveM artifact number (e.g., 16636, 16654)
• `server_type` - Server environment: `dev` or `live`

**Examples:**
• `{self.command_prefix}{self.command_names['update']} 16636 dev`
• `{self.command_prefix}{self.command_names['update']} 16654 live`

**Available server types:** dev, live""")
                return
            
            # Validate server type
            if server_type not in ['dev', 'live']:
                await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                return
            
            # Check if server type exists in config
            if server_type not in self.config:
                await ctx.send(f"❌ Server type '{server_type}' not found in configuration")
                return
            
            # Get server configuration
            server_config = self.get_server_config(server_type)
            if not server_config:
                await ctx.send(f"❌ Server configuration not found for {server_type}")
                return
            
            server_files_path = server_config['server_files']
            server_data_path = server_config['server_data']
            
            # Check server management configuration
            if not server_config['tcadmin_enabled'] and not server_config['service_enabled']:
                await ctx.send(f"ℹ️ No server management configured for {server_type} - will only update files (no server restart)")
            
            await ctx.send(f"🔄 Starting update for {server_type} server (Artifact: {artifact_number})")
            
            temp_dir = None
            artifact_file = None
            
            try:
                # Download or locate artifact
                await ctx.send("📥 Checking for existing artifact...")
                async with aiohttp.ClientSession() as session:
                    artifact_file, _ = await self.download_or_find_artifact(artifact_number, session, ctx)
                
                # Extract files
                await ctx.send("📂 Extracting files...")
                temp_dir = os.path.join(self.file_config['full_temp_path'], f"extract_{artifact_number}_{int(time.time())}")
                os.makedirs(temp_dir, exist_ok=True)
                self.extract_7z(artifact_file, temp_dir)
                
                # Stop server if management is configured
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    await ctx.send("⏹️ Stopping server...")
                    await self.stop_server(server_config)
                    
                    # Wait for service to fully stop
                    await asyncio.sleep(2)
                else:
                    await ctx.send("ℹ️ Skipping server stop (no management configured)")
                
                # Check for file locks
                await ctx.send("🔒 Checking for file locks...")
                if not self.check_file_locks(server_files_path):
                    await ctx.send("⚠️ Warning: Some files may be locked, proceeding anyway...")
                
                # Copy files with backup
                await ctx.send("📁 Copying server files...")
                extracted_server_path = os.path.join(temp_dir, 'server')
                if not os.path.exists(extracted_server_path):
                    # Check if files are in the root of temp_dir
                    extracted_server_path = temp_dir
                
                copy_result = self.copy_server_files(extracted_server_path, server_files_path, server_data_path, artifact_number)
                
                # Send backup and copy status messages
                if copy_result['backup_created']:
                    await ctx.send(f"💾 Server backup created: `{copy_result['backup_created']}`")
                
                if copy_result['data_backup_created']:
                    await ctx.send(f"💾 Server data backup created: `{copy_result['data_backup_created']}`")
                
                # Send copy status messages
                await ctx.send(f"📁 Copied {copy_result['copied_files']} files and {copy_result['copied_dirs']} directories to server")
                
                if copy_result['data_restored_files'] > 0 or copy_result['data_restored_dirs'] > 0:
                    if server_data_path:
                        await ctx.send(f"📊 Restored {copy_result['data_restored_files']} files and {copy_result['data_restored_dirs']} directories to server data location")
                    else:
                        await ctx.send(f"📊 Restored {copy_result['data_restored_files']} files and {copy_result['data_restored_dirs']} directories to server/ServerData")
                
                # Start server if management is configured
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    await ctx.send("▶️ Starting server...")
                    await self.start_server(server_config)
                    await ctx.send("✅ Server started successfully")
                else:
                    await ctx.send("ℹ️ Skipping server start (no management configured)")
                
                # Show file management info
                file_info = ""
                if self.file_config['keep_downloaded_files']:
                    file_info = f"\n📦 Artifact saved: `{os.path.basename(artifact_file)}`"
                else:
                    file_info = "\n🗑️ Artifact file deleted"
                
                await ctx.send(f"✅ Update completed successfully! Server files updated to artifact {artifact_number}{file_info}")
                await ctx.send(f"📋 Current server version: {artifact_number}")
                
            except Exception as e:
                logger.error(f"Update failed: {e}")
                await ctx.send(f"❌ Update failed: {str(e)}")
                
                # Try to start server if it was stopped (if management is configured)
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    try:
                        await ctx.send("🔄 Attempting to restart server...")
                        await self.start_server(server_config)
                        await ctx.send("✅ Server restarted")
                    except Exception as restart_e:
                        await ctx.send(f"❌ Failed to restart server: {restart_e}")
                else:
                    await ctx.send("ℹ️ Server restart skipped (no management configured)")
            
            finally:
                # Cleanup temp directory
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                
                # Delete artifact file if not keeping
                if artifact_file and not self.file_config['keep_downloaded_files']:
                    try:
                        if os.path.exists(artifact_file):
                            os.unlink(artifact_file)
                            logger.info(f"Deleted artifact file: {artifact_file}")
                    except Exception as e:
                        logger.error(f"Failed to delete artifact file: {e}")
        
        # Create status command
        @commands.command(name=self.command_names['status'])
        async def check_status(ctx, server_type: str = None):
            """Check server status"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            try:
                if server_type and server_type in ['dev', 'live']:
                    # Check specific server status
                    server_config = self.get_server_config(server_type)
                    if not server_config:
                        await ctx.send(f"❌ Server configuration not found for {server_type}")
                        return
                    
                    # Get server version info
                    current_version = self.get_current_version(server_config['server_files'])
                    version_info = f" (Version: {current_version})" if current_version else " (Version: Unknown)"
                    
                    # Get management type
                    if server_config['tcadmin_enabled']:
                        mgmt_type = "TCAdmin"
                    elif server_config['service_enabled']:
                        mgmt_type = f"Service ({server_config['service_name']})"
                    else:
                        mgmt_type = "No Management"
                    
                    if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                        status = await self.get_server_status(server_config)
                        if status == "running":
                            await ctx.send(f"✅ **{server_type.title()} Server:** Running{version_info}\n🔧 **Management:** {mgmt_type}")
                        elif status == "stopped":
                            await ctx.send(f"⏹️ **{server_type.title()} Server:** Stopped{version_info}\n🔧 **Management:** {mgmt_type}")
                        elif status == "error":
                            await ctx.send(f"❌ **{server_type.title()} Server:** Status check failed{version_info}\n🔧 **Management:** {mgmt_type}")
                        elif status == "not_found":
                            await ctx.send(f"❓ **{server_type.title()} Server:** Service not found{version_info}\n🔧 **Management:** {mgmt_type}")
                        else:
                            await ctx.send(f"❓ **{server_type.title()} Server:** Status unknown{version_info}\n🔧 **Management:** {mgmt_type}")
                    else:
                        await ctx.send(f"📁 **{server_type.title()} Server:** File operations only{version_info}\n🔧 **Management:** {mgmt_type}")
                else:
                    # Check both servers
                    status_text = f"**Server Status:**\n\n"
                    
                    for srv_type in ['dev', 'live']:
                        if srv_type in self.config:
                            server_config = self.get_server_config(srv_type)
                            if server_config:
                                current_version = self.get_current_version(server_config['server_files']) or "Unknown"
                                
                                if server_config['tcadmin_enabled']:
                                    mgmt_type = "TCAdmin"
                                elif server_config['service_enabled']:
                                    mgmt_type = f"Service ({server_config['service_name']})"
                                else:
                                    mgmt_type = "File Only"
                                
                                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                                    status = await self.get_server_status(server_config)
                                    status_text += f"**{srv_type.title()}:** {self.format_status(status)} - Version: {current_version} ({mgmt_type})\n"
                                else:
                                    status_text += f"**{srv_type.title()}:** 📁 File Only - Version: {current_version}\n"
                            else:
                                status_text += f"**{srv_type.title()}:** ⚪ Not configured\n"
                        else:
                            status_text += f"**{srv_type.title()}:** ⚪ Not configured\n"
                    
                    await ctx.send(status_text)
                        
            except Exception as e:
                await ctx.send(f"❌ Error checking service status: {e}")
        
        # Create version command
        @commands.command(name=self.command_names['version'])
        async def check_version(ctx, server_type: str = None):
            """Check current server version"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            try:
                if server_type and server_type in ['dev', 'live']:
                    # Check specific server version
                    server_config = self.get_server_config(server_type)
                    if not server_config:
                        await ctx.send(f"❌ Server configuration not found for {server_type}")
                        return
                    
                    current_version = self.get_current_version(server_config['server_files'])
                    
                    if current_version:
                        await ctx.send(f"📋 **{server_type.title()} Server Version:** {current_version}")
                    else:
                        await ctx.send(f"❓ **{server_type.title()} Server Version:** Unknown (no version.txt found)")
                else:
                    # Check both servers
                    version_text = f"📋 **Server Versions:**\n\n"
                    
                    for srv_type in ['dev', 'live']:
                        if srv_type in self.config:
                            server_config = self.get_server_config(srv_type)
                            if server_config:
                                current_version = self.get_current_version(server_config['server_files']) or "Unknown"
                                version_text += f"**{srv_type.title()}:** {current_version}\n"
                            else:
                                version_text += f"**{srv_type.title()}:** Not configured\n"
                        else:
                            version_text += f"**{srv_type.title()}:** Not configured\n"
                    
                    await ctx.send(version_text)
                        
            except Exception as e:
                await ctx.send(f"❌ Error checking version: {e}")
        
        # Create cleanup command
        @commands.command(name=self.command_names['cleanup'])
        async def cleanup_files(ctx, days: int = None):
            """Clean up old downloaded files"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            try:
                if days is None:
                    days = self.file_config['auto_cleanup_days']
                
                if days <= 0:
                    await ctx.send("❌ Days must be greater than 0")
                    return
                
                await ctx.send(f"🧹 Cleaning up files older than {days} days...")
                deleted_count = self.cleanup_old_files(days)
                
                if deleted_count > 0:
                    await ctx.send(f"✅ Cleaned up {deleted_count} old file(s)")
                else:
                    await ctx.send("ℹ️ No old files found to clean up")
                    
            except Exception as e:
                await ctx.send(f"❌ Error during cleanup: {e}")
        
        # Create backups command
        @commands.command(name=self.command_names['backups'])
        async def manage_backups(ctx, action: str = None, server_type: str = None, backup_name: str = None):
            """Manage server file backups"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            if not action:
                await ctx.send(f"""❌ **Missing action parameter!**

**Usage:** `{self.command_prefix}{self.command_names['backups']} <action> [server_type] [backup_name]`

**Actions:**
• `list` - List all backups for a server type
• `delete` - Delete a specific backup or all backups

**Examples:**
• `{self.command_prefix}{self.command_names['backups']} list dev` - List dev server backups
• `{self.command_prefix}{self.command_names['backups']} delete dev server_backup_17346` - Delete specific backup
• `{self.command_prefix}{self.command_names['backups']} delete dev all` - Delete all dev backups""")
                return
            
            try:
                if action.lower() == 'list':
                    if not server_type:
                        await ctx.send("❌ Server type required for list action (dev/live)")
                        return
                    
                    if server_type not in ['dev', 'live']:
                        await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                        return
                    
                    server_config = self.get_server_config(server_type)
                    if not server_config:
                        await ctx.send(f"❌ Server configuration not found for {server_type}")
                        return
                    
                    server_files_path = server_config['server_files']
                    server_data_path = server_config['server_data']
                    
                    backups = self.find_backup_directories(server_files_path, server_data_path)
                    
                    if not backups:
                        await ctx.send(f"ℹ️ No backups found for {server_type} server")
                        return
                    
                    backup_info = f"📦 **{server_type.title()} Server Backups:**\n\n"
                    for i, backup in enumerate(backups, 1):
                        if backup['type'] == 'server':
                            type_icon = "🖥️"
                        elif backup['type'] == 'server+data':
                            type_icon = "🖥️💾"
                        else:  # server-data
                            type_icon = "📊"
                        
                        backup_info += f"**{i}.** {type_icon} `{backup['name']}` ({backup['type']})\n"
                        backup_info += f"   📅 Created: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                        backup_info += f"   📊 Size: {backup['size_mb']:.1f} MB\n\n"
                    
                    backup_info += f"💡 Use `{self.command_prefix}{self.command_names['backups']} delete {server_type} <backup_name>` to delete a backup"
                    await ctx.send(backup_info)
                
                elif action.lower() == 'delete':
                    if not server_type:
                        await ctx.send("❌ Server type required for delete action (dev/live)")
                        return
                    
                    if server_type not in ['dev', 'live']:
                        await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                        return
                    
                    server_config = self.get_server_config(server_type)
                    if not server_config:
                        await ctx.send(f"❌ Server configuration not found for {server_type}")
                        return
                    
                    server_files_path = server_config['server_files']
                    server_data_path = server_config['server_data']
                    
                    backups = self.find_backup_directories(server_files_path, server_data_path)
                    
                    if not backups:
                        await ctx.send(f"ℹ️ No backups found for {server_type} server")
                        return
                    
                    if not backup_name:
                        await ctx.send("❌ Backup name required for delete action (or 'all' to delete all backups)")
                        return
                    
                    if backup_name.lower() == 'all':
                        # Delete all backups
                        deleted_count = 0
                        for backup in backups:
                            if self.delete_backup_directory(backup['path']):
                                deleted_count += 1
                        
                        await ctx.send(f"✅ Deleted {deleted_count} backup(s) for {server_type} server")
                    else:
                        # Delete specific backup
                        backup_found = None
                        for backup in backups:
                            if backup['name'] == backup_name:
                                backup_found = backup
                                break
                        
                        if not backup_found:
                            await ctx.send(f"❌ Backup '{backup_name}' not found for {server_type} server")
                            return
                        
                        if self.delete_backup_directory(backup_found['path']):
                            await ctx.send(f"✅ Deleted backup: `{backup_name}`")
                        else:
                            await ctx.send(f"❌ Failed to delete backup: `{backup_name}`")
                
                else:
                    await ctx.send(f"❌ Unknown action: {action}. Use 'list' or 'delete'")
                    
            except Exception as e:
                await ctx.send(f"❌ Error managing backups: {e}")
        
        # Create rollback command
        @commands.command(name=self.command_names['rollback'])
        async def rollback_server(ctx, server_type: str = None, backup_name: str = None):
            """Rollback server to a previous backup"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            if not server_type or not backup_name:
                await ctx.send(f"""❌ **Missing parameters!**

**Usage:** `{self.command_prefix}{self.command_names['rollback']} <server_type> <backup_name>`

**Parameters:**
• `server_type` - Server environment: `dev` or `live`
• `backup_name` - Name of backup to restore

**Example:**
• `{self.command_prefix}{self.command_names['rollback']} dev server_backup_17346`

💡 Use `{self.command_prefix}{self.command_names['backups']} list <server_type>` to see available backups""")
                return
            
            if server_type not in ['dev', 'live']:
                await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                return
            
            server_config = self.get_server_config(server_type)
            if not server_config:
                await ctx.send(f"❌ Server configuration not found for {server_type}")
                return
            
            try:
                server_files_path = server_config['server_files']
                server_data_path = server_config['server_data']
                
                backups = self.find_backup_directories(server_files_path, server_data_path)
                
                # Find the specified backup
                backup_found = None
                for backup in backups:
                    if backup['name'] == backup_name:
                        backup_found = backup
                        break
                
                if not backup_found:
                    await ctx.send(f"❌ Backup '{backup_name}' not found for {server_type} server")
                    return
                
                await ctx.send(f"🔄 Starting rollback for {server_type} server to backup: `{backup_name}`")
                
                # Check server management configuration
                if not server_config['tcadmin_enabled'] and not server_config['service_enabled']:
                    await ctx.send(f"ℹ️ No server management configured for {server_type} - will only restore files (no server restart)")
                
                # Stop server if management is configured
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    await ctx.send("⏹️ Stopping server...")
                    await self.stop_server(server_config)
                    await asyncio.sleep(3)
                else:
                    await ctx.send("ℹ️ Skipping server stop (no management configured)")
                
                # Create backup of current files before rollback
                current_backup_name = self.create_backup_name(Path(server_files_path))
                await ctx.send(f"💾 Creating backup of current files: `{current_backup_name.name}`")
                
                shutil.move(server_files_path, str(current_backup_name))
                
                # Restore from backup
                await ctx.send(f"📁 Restoring from backup...")
                shutil.copytree(str(backup_found['path']), server_files_path)
                
                # Start server if management is configured
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    await ctx.send("▶️ Starting server...")
                    await self.start_server(server_config)
                    await ctx.send("✅ Server started successfully")
                else:
                    await ctx.send("ℹ️ Skipping server start (no management configured)")
                
                await ctx.send(f"✅ Rollback completed successfully! Server restored to backup: `{backup_name}`")
                await ctx.send(f"💾 Current files backed up as: `{current_backup_name.name}`")
                
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                await ctx.send(f"❌ Rollback failed: {str(e)}")
                
                # Try to restart server if it was stopped
                if server_config['tcadmin_enabled'] or server_config['service_enabled']:
                    try:
                        await ctx.send("🔄 Attempting to restart server...")
                        await self.start_server(server_config)
                        await ctx.send("✅ Server restarted")
                    except Exception as restart_e:
                        await ctx.send(f"❌ Failed to restart server: {restart_e}")
        
        # Create config command
        @commands.command(name=self.command_names['config'])
        async def show_config(ctx):
            """Show current configuration"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            config_info = "📋 **Current Configuration:**\n"
            
            # Show Discord configuration (without token)
            if 'discord' in self.config:
                config_info += "\n**[discord]**\n"
                config_info += f"  command_prefix: {self.command_prefix}\n"
                config_info += f"  response_channel: {self.response_channel_id}\n"
                config_info += f"  allowed_roles: {', '.join(map(str, self.allowed_roles)) if self.allowed_roles else 'None'}\n"
                config_info += f"  allowed_users: {', '.join(map(str, self.allowed_users)) if self.allowed_users else 'None'}\n"
                config_info += f"  Commands: {self.command_names}\n"
            
            # Show server configurations
            for srv_type in ['dev', 'live']:
                if srv_type in self.config:
                    config_info += f"\n**[{srv_type}]**\n"
                    server_config = self.get_server_config(srv_type)
                    if server_config:
                        config_info += f"  ServerFiles: {server_config['server_files']}\n"
                        config_info += f"  ServerData: {server_config['server_data'] or 'Not configured'}\n"
                        config_info += f"  TCADMIN_Enabled: {server_config['tcadmin_enabled']}\n"
                        if server_config['tcadmin_enabled']:
                            config_info += f"  tcadmin_executable: {server_config['tcadmin_executable']}\n"
                            config_info += f"  tcadmin_service_id: {server_config['tcadmin_service_id']}\n"
                        config_info += f"  Service_Enabled: {server_config['service_enabled']}\n"
                        if server_config['service_enabled']:
                            config_info += f"  Service_Name: {server_config['service_name']}\n"
                    else:
                        config_info += "  Configuration error\n"
            
            # Show file management configuration
            config_info += "\n**[files]**\n"
            config_info += f"  base_directory: {self.file_config['base_directory']}\n"
            config_info += f"  download_directory: {self.file_config['full_download_path'].absolute()}\n"
            config_info += f"  temp_directory: {self.file_config['full_temp_path'].absolute()}\n"
            config_info += f"  keep_downloaded_files: {self.file_config['keep_downloaded_files']}\n"
            config_info += f"  auto_cleanup_days: {self.file_config['auto_cleanup_days']}\n"
            
            # Show download directory stats
            download_path = Path(self.file_config['full_download_path'])
            if download_path.exists():
                file_count = len(list(download_path.glob('*.7z')))
                total_size = sum(f.stat().st_size for f in download_path.glob('*.7z'))
                total_size_mb = total_size / (1024 * 1024)
                config_info += f"  📁 Files stored: {file_count} ({total_size_mb:.1f} MB)\n"
            
            # Show server configurations
            for section in self.config.sections():
                if section not in ['discord', 'tcadmin', 'files']:  # Skip already shown sections
                    config_info += f"\n**[{section}]**\n"
                    for key, value in self.config[section].items():
                        config_info += f"  {key}: {value}\n"
            
            await ctx.send(config_info)
        
        # Create help command
        @commands.command(name=self.command_names['help'])
        async def help_command(ctx):
            """Show available commands"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            help_text = f"""
📚 **FiveM Update Bot Commands**

**📥 Download & Update:**
`{self.command_prefix}{self.command_names['download']} <artifact_number> [force]` - Download artifact (no server update)
  • Example: `{self.command_prefix}{self.command_names['download']} 17346`
  • Example: `{self.command_prefix}{self.command_names['download']} 17346 force` (re-download if exists)

`{self.command_prefix}{self.command_names['update']} <artifact_number> <server_type>` - Update server files
  • Example: `{self.command_prefix}{self.command_names['update']} 16636 dev`
  • Example: `{self.command_prefix}{self.command_names['update']} 16654 live`

**🔧 Server Management:**
`{self.command_prefix}{self.command_names['start']} <server_type>` - Start server
  • Example: `{self.command_prefix}{self.command_names['start']} dev`
  • Example: `{self.command_prefix}{self.command_names['start']} live`

`{self.command_prefix}{self.command_names['stop']} <server_type>` - Stop server
  • Example: `{self.command_prefix}{self.command_names['stop']} dev`
  • Example: `{self.command_prefix}{self.command_names['stop']} live`

`{self.command_prefix}{self.command_names['status']} [server_type]` - Check server status
  • Example: `{self.command_prefix}{self.command_names['status']}` (all servers)
  • Example: `{self.command_prefix}{self.command_names['status']} dev` (specific server)

**💾 Backup & Restore:**
`{self.command_prefix}{self.command_names['backups']} <action> <server_type> [backup_name]` - Manage server backups
  • Example: `{self.command_prefix}{self.command_names['backups']} list dev` (list backups)
  • Example: `{self.command_prefix}{self.command_names['backups']} delete dev server_backup_17346` (delete backup)

`{self.command_prefix}{self.command_names['rollback']} <server_type> <backup_name>` - Rollback to previous backup
  • Example: `{self.command_prefix}{self.command_names['rollback']} dev server_backup_17346`

**📋 Information:**
`{self.command_prefix}{self.command_names['version']} [server_type]` - Check current server version
  • Example: `{self.command_prefix}{self.command_names['version']}` (all servers)
  • Example: `{self.command_prefix}{self.command_names['version']} live` (specific server)

`{self.command_prefix}{self.command_names['config']}` - Show current configuration

**🧹 Maintenance:**
`{self.command_prefix}{self.command_names['cleanup']} [days]` - Clean up old downloaded files
  • Example: `{self.command_prefix}{self.command_names['cleanup']}` (use default cleanup period)
  • Example: `{self.command_prefix}{self.command_names['cleanup']} 7` (files older than 7 days)

`{self.command_prefix}{self.command_names['help']}` - Show this help message

**Server Types:** dev, live
**Management:** Per-server configuration (TCAdmin/Windows Service/File-only)
**File Caching:** {'Enabled' if self.file_config['keep_downloaded_files'] else 'Disabled'}
**Auto Backup:** ✅ Enabled (before each update)
            """
            
            await ctx.send(help_text)
        
        # Create stop command
        @commands.command(name=self.command_names['stop'])
        async def stop_server_cmd(ctx, server_type: str = None):
            """Stop server (TCAdmin or Windows Service)"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            if not server_type:
                await ctx.send(f"""❌ **Missing server type!**

**Usage:** `{self.command_prefix}{self.command_names['stop']} <server_type>`

**Parameters:**
• `server_type` - Server environment: `dev` or `live`

**Examples:**
• `{self.command_prefix}{self.command_names['stop']} dev`
• `{self.command_prefix}{self.command_names['stop']} live`""")
                return
            
            if server_type not in ['dev', 'live']:
                await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                return
            
            # Get server configuration
            server_config = self.get_server_config(server_type)
            if not server_config:
                await ctx.send(f"❌ Server configuration not found for {server_type}")
                return
            
            # Check if server management is configured
            if not server_config['tcadmin_enabled'] and not server_config['service_enabled']:
                await ctx.send(f"❌ No server management configured for {server_type} server")
                return
            
            try:
                # Get management type for display
                if server_config['tcadmin_enabled']:
                    mgmt_type = "TCAdmin"
                elif server_config['service_enabled']:
                    mgmt_type = f"Windows Service ({server_config['service_name']})"
                
                await ctx.send(f"⏹️ Stopping {server_type} server ({mgmt_type})...")
                
                # Stop the server
                await self.stop_server(server_config)
                
                await ctx.send(f"✅ {server_type.title()} server stopped successfully")
                
            except Exception as e:
                logger.error(f"Failed to stop {server_type} server: {e}")
                await ctx.send(f"❌ Failed to stop {server_type} server: {str(e)}")
        
        # Create start command
        @commands.command(name=self.command_names['start'])
        async def start_server_cmd(ctx, server_type: str = None):
            """Start server (TCAdmin or Windows Service)"""
            
            # Check permissions
            if not self.check_permissions(ctx):
                await ctx.send("❌ You don't have permission to use this command")
                return
            
            # Check channel
            if not self.check_channel(ctx):
                if self.response_channel_id:
                    channel = self.get_channel(self.response_channel_id)
                    await ctx.send(f"❌ This command can only be used in {channel.mention}")
                return
            
            if not server_type:
                await ctx.send(f"""❌ **Missing server type!**

**Usage:** `{self.command_prefix}{self.command_names['start']} <server_type>`

**Parameters:**
• `server_type` - Server environment: `dev` or `live`

**Examples:**
• `{self.command_prefix}{self.command_names['start']} dev`
• `{self.command_prefix}{self.command_names['start']} live`""")
                return
            
            if server_type not in ['dev', 'live']:
                await ctx.send("❌ Invalid server type. Use 'dev' or 'live'")
                return
            
            # Get server configuration
            server_config = self.get_server_config(server_type)
            if not server_config:
                await ctx.send(f"❌ Server configuration not found for {server_type}")
                return
            
            # Check if server management is configured
            if not server_config['tcadmin_enabled'] and not server_config['service_enabled']:
                await ctx.send(f"❌ No server management configured for {server_type} server")
                return
            
            try:
                # Get management type for display
                if server_config['tcadmin_enabled']:
                    mgmt_type = "TCAdmin"
                elif server_config['service_enabled']:
                    mgmt_type = f"Windows Service ({server_config['service_name']})"
                
                await ctx.send(f"▶️ Starting {server_type} server ({mgmt_type})...")
                
                # Start the server
                await self.start_server(server_config)
                
                await ctx.send(f"✅ {server_type.title()} server started successfully")
                
            except Exception as e:
                logger.error(f"Failed to start {server_type} server: {e}")
                await ctx.send(f"❌ Failed to start {server_type} server: {str(e)}")
        
        # Add commands to bot
        self.add_command(download_artifact)
        self.add_command(update_server)
        self.add_command(check_status)
        self.add_command(check_version)
        self.add_command(cleanup_files)
        self.add_command(manage_backups)
        self.add_command(rollback_server)
        self.add_command(stop_server_cmd)
        self.add_command(start_server_cmd)
        self.add_command(show_config)
        self.add_command(help_command)
    
    def format_status(self, status):
        """Format status with appropriate emoji"""
        if status == "running":
            return "✅ Running"
        elif status == "stopped":
            return "⏹️ Stopped"
        elif status == "error":
            return "❌ Error"
        elif status == "Not configured":
            return "⚪ Not configured"
        else:
            return "❓ Unknown"
    
    def check_permissions(self, ctx):
        """Check if user has permission to use bot commands"""
        # If no roles and no users are configured, allow everyone
        if not self.allowed_roles and not self.allowed_users:
            return True
        
        # Check if user is in allowed users list
        if self.allowed_users and ctx.author.id in self.allowed_users:
            return True
        
        # Check if user has any of the allowed roles
        if self.allowed_roles:
            user_roles = [role.id for role in ctx.author.roles]
            if any(role_id in user_roles for role_id in self.allowed_roles):
                return True
        
        # If we reach here, user doesn't have permission
        return False
    
    def check_channel(self, ctx):
        """Check if command is being used in the correct channel"""
        # If no channel is configured, allow all channels
        if not self.response_channel_id:
            return True
        
        return ctx.channel.id == self.response_channel_id
    
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is ready and listening for commands with prefix: {self.command_prefix}')
        
        # Log command names
        logger.info(f'Available commands: {list(self.command_names.values())}')
        
        # Log server configurations
        for srv_type in ['dev', 'live']:
            if srv_type in self.config:
                server_config = self.get_server_config(srv_type)
                if server_config:
                    if server_config['tcadmin_enabled']:
                        logger.info(f"{srv_type.title()} server: TCAdmin (Service ID: {server_config['tcadmin_service_id']})")
                    elif server_config['service_enabled']:
                        logger.info(f"{srv_type.title()} server: Windows Service ({server_config['service_name']})")
                    else:
                        logger.info(f"{srv_type.title()} server: File operations only")
        
        # Perform startup cleanup if enabled
        if self.file_config['auto_cleanup_days'] > 0:
            deleted_count = self.cleanup_old_files()
            if deleted_count > 0:
                logger.info(f"Startup cleanup: removed {deleted_count} old file(s)")
        
        # Log channel and role configuration
        if self.response_channel_id:
            channel = self.get_channel(self.response_channel_id)
            if channel:
                logger.info(f"Response channel: #{channel.name} ({channel.id})")
            else:
                logger.warning(f"Response channel ID {self.response_channel_id} not found")
        
        if self.allowed_roles:
            logger.info(f"Allowed roles: {self.allowed_roles}")
        
        if self.allowed_users:
            logger.info(f"Allowed users: {self.allowed_users}")
    
    async def get_artifact_hash_from_directory(self, artifact_number, session):
        """Get the full artifact directory name with hash from FiveM artifacts page"""
        list_url = "https://runtime.fivem.net/artifacts/fivem/build_server_windows/master/"
        
        try:
            logger.info(f"Fetching artifact directory listing from: {list_url}")
            async with session.get(list_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch artifact list: {response.status}")
                
                html_content = await response.text()
                logger.info(f"Received HTML content, length: {len(html_content)} characters")
                
                # Find the artifact download URL directly from the HTML
                import re
                # Look for pattern like: href="./17346-c75a342e872e34d431322d03d45881f664a4098b/server.7z"
                pattern = rf'href="\.\/({artifact_number}-[a-f0-9]+)\/server\.7z"'
                logger.info(f"Searching for pattern: {pattern}")
                
                match = re.search(pattern, html_content)
                
                if match:
                    artifact_dir = match.group(1)
                    logger.info(f"✅ Found artifact directory: {artifact_dir}")
                    return artifact_dir
                
                # If not found, show available artifacts for debugging
                logger.warning(f"Artifact {artifact_number} not found, showing available artifacts...")
                
                # Find all artifact download links
                all_artifacts_pattern = r'href="\.\/(\d+-[a-f0-9]+)\/server\.7z"'
                all_matches = re.findall(all_artifacts_pattern, html_content)
                logger.info(f"Found {len(all_matches)} artifact downloads:")
                for match in all_matches[:10]:  # Show first 10
                    artifact_num = match.split('-')[0]
                    logger.info(f"  Artifact {artifact_num}: {match}")
                if len(all_matches) > 10:
                    logger.info(f"  ... and {len(all_matches) - 10} more")
                
                raise Exception(f"Artifact {artifact_number} not found in directory listing")
                
        except Exception as e:
            logger.error(f"Error fetching artifact directory: {e}")
            raise

    async def download_or_find_artifact(self, artifact_number, session, ctx=None, force_download=False):
        """Download artifact or find existing file - prioritizes local files unless force_download is True"""
        try:
            # Check if we have a cached file (unless forcing download)
            download_path = Path(self.file_config['full_download_path'])
            existing_files = list(download_path.glob(f'{artifact_number}*.7z'))
            
            if existing_files and not force_download:
                # Use existing cached file
                existing_file = existing_files[0]
                if ctx:
                    await ctx.send(f"✅ Using cached artifact: `{existing_file.name}`")
                logger.info(f"Using existing cached artifact: {existing_file}")
                return str(existing_file), None
            elif existing_files and force_download:
                if ctx:
                    await ctx.send(f"🔄 Found cached file but re-downloading as requested...")
                logger.info(f"Found cached file but force_download=True, will re-download")
            
            # Try to get the artifact directory with hash from FiveM listing
            download_url = None
            try:
                if ctx:
                    await ctx.send(f"🔍 Looking up artifact {artifact_number} in FiveM directory...")
                
                artifact_dir = await self.get_artifact_hash_from_directory(artifact_number, session)
                download_url = f"https://runtime.fivem.net/artifacts/fivem/build_server_windows/master/{artifact_dir}/server.7z"
                logger.info(f"✅ Constructed URL from directory listing: {download_url}")
                logger.info(f"📁 Artifact directory found: {artifact_dir}")
                
            except Exception as e:
                # If HTML scraping fails, we can't proceed
                logger.error(f"Failed to get artifact directory from FiveM website: {e}")
                if ctx:
                    await ctx.send(f"❌ Failed to find artifact {artifact_number} on FiveM website")
                raise Exception(f"Artifact {artifact_number} not found in FiveM directory listing")
            
            # Generate filename for artifact
            artifact_filename = f"{artifact_number}.7z"
            local_file_path = download_path / artifact_filename
            
            if ctx:
                await ctx.send(f"📥 Downloading artifact: `{artifact_filename}`")
            logger.info(f"✅ Successfully found download URL: {download_url}")
            logger.info(f"📁 Saving to local path: {local_file_path}")
            
            # Download the 7z file
            logger.info(f"🌐 Starting download from: {download_url}")
            async with session.get(download_url) as download_response:
                logger.info(f"📊 Download response status: {download_response.status}")
                if download_response.status != 200:
                    raise Exception(f"Failed to download artifact: HTTP {download_response.status}")
                
                # Get content length if available
                content_length = download_response.headers.get('content-length')
                if content_length:
                    logger.info(f"📦 Download size: {int(content_length)} bytes ({int(content_length)/1024/1024:.1f} MB)")
                
                # Save to our download directory
                bytes_downloaded = 0
                with open(local_file_path, 'wb') as f:
                    async for chunk in download_response.content.iter_chunked(8192):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                
                file_size = local_file_path.stat().st_size
                logger.info(f"✅ Download completed successfully!")
                logger.info(f"📁 Downloaded to: {local_file_path}")
                logger.info(f"📊 Final file size: {file_size} bytes ({file_size/1024/1024:.1f} MB)")
                return str(local_file_path), None
                    
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def extract_7z(self, file_path, extract_to):
        """Extract 7z file"""
        try:
            with py7zr.SevenZipFile(file_path, mode='r') as archive:
                archive.extractall(path=extract_to)
            logger.info(f"Extracted to: {extract_to}")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
    
    def get_current_version(self, target_path):
        """Read current version from version.txt file if it exists"""
        try:
            version_file = Path(target_path) / 'version.txt'
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version = f.read().strip()
                    if version:
                        logger.info(f"Current server version: {version}")
                        return version
        except Exception as e:
            logger.warning(f"Could not read version file: {e}")
        return None
    
    def create_backup_name(self, target_path, new_artifact_number=None):
        """Generate a unique backup directory name based on current version"""
        target_path = Path(target_path)
        parent_dir = target_path.parent
        base_name = target_path.name
        
        # Try to get current version from version.txt
        current_version = self.get_current_version(target_path)
        
        if current_version:
            # Use current version in backup name
            backup_base = f"{base_name}_backup_{current_version}"
        elif new_artifact_number:
            # Fallback to new artifact number
            backup_base = f"{base_name}_backup_{new_artifact_number}"
        else:
            # Fallback to generic backup with incremental numbers
            backup_base = f"{base_name}_bak"
            counter = 1
            while (parent_dir / f"{backup_base}{counter}").exists():
                counter += 1
            return parent_dir / f"{backup_base}{counter}"
        
        # Find a unique name by adding numbers if needed
        backup_name = backup_base
        counter = 1
        while (parent_dir / backup_name).exists():
            backup_name = f"{backup_base}_{counter}"
            counter += 1
        
        return parent_dir / backup_name
    
    def create_version_file(self, target_dir, artifact_number):
        """Create version.txt file in target directory"""
        try:
            version_file = Path(target_dir) / 'version.txt'
            with open(version_file, 'w') as f:
                f.write(str(artifact_number))
            logger.info(f"Created version.txt with artifact {artifact_number}")
        except Exception as e:
            logger.error(f"Failed to create version.txt: {e}")
    
    def copy_server_files(self, source_dir, target_dir, server_data_dir=None, artifact_number=None):
        """Copy server files to target directory with backup of existing files"""
        try:
            source_path = Path(source_dir)
            target_path = Path(target_dir)
            
            logger.info(f"Starting file copy with backup: {source_dir} -> {target_dir}")
            
            backup_created = None
            data_backup_created = None
            
            # Create backup of existing server files if directory exists and has content
            if target_path.exists() and any(target_path.iterdir()):
                backup_path = self.create_backup_name(target_path, artifact_number)
                
                logger.info(f"Creating backup: {target_path} -> {backup_path}")
                
                # Move existing directory to backup location
                shutil.move(str(target_path), str(backup_path))
                backup_created = backup_path.name
                
                logger.info(f"Backup created: {backup_path}")
            
            # Create backup of server data if specified and exists
            if server_data_dir:
                server_data_path = Path(server_data_dir)
                if server_data_path.exists() and any(server_data_path.iterdir()):
                    data_backup_path = self.create_backup_name(server_data_path, artifact_number)
                    
                    logger.info(f"Creating server data backup: {server_data_path} -> {data_backup_path}")
                    
                    # Move existing server data to backup location
                    shutil.move(str(server_data_path), str(data_backup_path))
                    data_backup_created = data_backup_path.name
                    
                    logger.info(f"Server data backup created: {data_backup_path}")
            
            # Create fresh target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all files and directories from source
            copied_files = 0
            copied_dirs = 0
            
            for item in source_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_path / item.name)
                    copied_files += 1
                elif item.is_dir():
                    shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)
                    copied_dirs += 1
            
            # Restore server data from backup if it was backed up
            data_restored_files = 0
            data_restored_dirs = 0
            
            if server_data_dir and data_backup_created:
                # Find the backup directory we just created for ServerData
                server_data_path = Path(server_data_dir)
                data_parent_dir = server_data_path.parent
                backup_path = data_parent_dir / data_backup_created
                
                if backup_path.exists():
                    # Create the server data directory
                    server_data_path.mkdir(parents=True, exist_ok=True)
                    
                    logger.info(f"Restoring server data from backup: {backup_path} -> {server_data_path}")
                    
                    for item in backup_path.iterdir():
                        if item.is_file():
                            shutil.copy2(item, server_data_path / item.name)
                            data_restored_files += 1
                        elif item.is_dir():
                            shutil.copytree(item, server_data_path / item.name, dirs_exist_ok=True)
                            data_restored_dirs += 1
                    
                    logger.info(f"Server data restored: {data_restored_files} files, {data_restored_dirs} directories")
            
            # Check if ServerData exists in the server backup (inside the server folder)
            if backup_created:
                server_backup_path = target_path.parent / backup_created
                server_data_in_backup = server_backup_path / 'ServerData'
                
                if server_data_in_backup.exists():
                    logger.info(f"Found ServerData in server backup: {server_data_in_backup}")
                    
                    if server_data_dir:
                        # ServerData location is configured - copy to that location
                        server_data_path = Path(server_data_dir)
                        server_data_path.mkdir(parents=True, exist_ok=True)
                        
                        logger.info(f"Copying ServerData from server backup to configured location: {server_data_in_backup} -> {server_data_path}")
                        
                        for item in server_data_in_backup.iterdir():
                            if item.is_file():
                                shutil.copy2(item, server_data_path / item.name)
                                data_restored_files += 1
                            elif item.is_dir():
                                shutil.copytree(item, server_data_path / item.name, dirs_exist_ok=True)
                                data_restored_dirs += 1
                    else:
                        # No separate ServerData location configured - restore to server folder
                        server_data_in_server = target_path / 'ServerData'
                        
                        logger.info(f"Copying ServerData back to server folder: {server_data_in_backup} -> {server_data_in_server}")
                        
                        shutil.copytree(str(server_data_in_backup), str(server_data_in_server), dirs_exist_ok=True)
                        
                        # Count files and directories for reporting
                        for root, dirs, files in os.walk(server_data_in_server):
                            data_restored_files += len(files)
                            data_restored_dirs += len(dirs)
                    
                    logger.info(f"ServerData from server backup restored: {data_restored_files} files, {data_restored_dirs} directories")
            
            # Fallback: Check if server-data exists in the extracted artifact (for initial setup)
            if data_restored_files == 0 and data_restored_dirs == 0:
                source_data_path = source_path / 'server-data'
                if source_data_path.exists():
                    if server_data_dir:
                        server_data_path = Path(server_data_dir)
                        server_data_path.mkdir(parents=True, exist_ok=True)
                        
                        logger.info(f"Copying server-data from artifact: {source_data_path} -> {server_data_path}")
                        
                        for item in source_data_path.iterdir():
                            if item.is_file():
                                shutil.copy2(item, server_data_path / item.name)
                                data_restored_files += 1
                            elif item.is_dir():
                                shutil.copytree(item, server_data_path / item.name, dirs_exist_ok=True)
                                data_restored_dirs += 1
                    else:
                        # Copy to server folder as ServerData
                        server_data_in_server = target_path / 'ServerData'
                        shutil.copytree(str(source_data_path), str(server_data_in_server), dirs_exist_ok=True)
                        
                        # Count files and directories
                        for root, dirs, files in os.walk(server_data_in_server):
                            data_restored_files += len(files)  
                            data_restored_dirs += len(dirs)
                    
                    logger.info(f"Server data from artifact: {data_restored_files} files, {data_restored_dirs} directories")
            
            logger.info(f"Files copied: {copied_files} files, {copied_dirs} directories from {source_dir} to {target_dir}")
            
            # Create version.txt file in the target directory if artifact number is provided
            if artifact_number:
                self.create_version_file(target_dir, artifact_number)
            
            return {
                'backup_created': backup_created,
                'data_backup_created': data_backup_created,
                'copied_files': copied_files,
                'copied_dirs': copied_dirs,
                'data_restored_files': data_restored_files,
                'data_restored_dirs': data_restored_dirs
            }
            
        except Exception as e:
            logger.error(f"File copy with backup failed: {e}")
            raise
    
    def find_backup_directories(self, server_path, server_data_path=None):
        """Find all backup directories for a given server path and optionally server data path"""
        server_path = Path(server_path)
        parent_dir = server_path.parent
        server_name = server_path.name
        
        # Look for backup directories matching patterns
        backup_pattern = f"{server_name}_backup*"
        backup_dirs = []
        
        if parent_dir.exists():
            for item in parent_dir.glob(backup_pattern):
                if item.is_dir():
                    # Get creation time for sorting
                    stat = item.stat()
                    
                    # Check if this server backup contains ServerData
                    server_data_inside = item / 'ServerData'
                    backup_type = 'server'
                    if server_data_inside.exists():
                        backup_type = 'server+data'
                    
                    backup_entry = {
                        'path': item,
                        'name': item.name,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'size_mb': sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / 1024 / 1024,
                        'type': backup_type
                    }
                    backup_dirs.append(backup_entry)
        
        # Also look for server data backups if server_data_path is specified
        if server_data_path:
            server_data_path = Path(server_data_path)
            data_parent_dir = server_data_path.parent
            data_name = server_data_path.name
            
            if data_parent_dir.exists():
                data_backup_pattern = f"{data_name}_backup*"
                for item in data_parent_dir.glob(data_backup_pattern):
                    if item.is_dir():
                        # Get creation time for sorting
                        stat = item.stat()
                        backup_entry = {
                            'path': item,
                            'name': item.name,
                            'created': datetime.fromtimestamp(stat.st_ctime),
                            'size_mb': sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / 1024 / 1024,
                            'type': 'server-data'
                        }
                        backup_dirs.append(backup_entry)
        
        # Sort by creation time (newest first)
        backup_dirs.sort(key=lambda x: x['created'], reverse=True)
        return backup_dirs
    
    def delete_backup_directory(self, backup_path):
        """Delete a specific backup directory"""
        try:
            backup_path = Path(backup_path)
            if backup_path.exists() and backup_path.is_dir():
                shutil.rmtree(backup_path)
                logger.info(f"Deleted backup directory: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup directory {backup_path}: {e}")
            raise

# Create bot instance
bot = FiveMUpdateBot()

if __name__ == '__main__':
    # Get bot token from config
    try:
        if 'discord' not in bot.config or 'discord_token' not in bot.config['discord']:
            logger.error("Discord token not found in config.ini")
            exit(1)
        
        token = bot.config['discord']['discord_token']
        if token == 'your_discord_bot_token_here':
            logger.error("Please set your Discord bot token in config.ini")
            exit(1)
        
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1) 