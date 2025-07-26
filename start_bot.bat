@echo off
echo FiveM Update Bot - TCAdmin Edition
echo ====================================
echo.

:: Check if config.ini exists
if not exist "config.ini" (
    echo Config file not found!
    echo Please run setup first: python setup_environment.py
    echo.
    echo Note: This bot requires TCAdmin for server management
    echo.
    pause
    exit /b 1
)

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.8 or higher.
    echo.
    pause
    exit /b 1
)

:: Start the bot
echo Starting FiveM Update Bot...
echo Make sure your TCAdmin server is accessible!
echo.
python main.py

:: Keep window open if there's an error
if %errorlevel% neq 0 (
    echo.
    echo Bot exited with error code %errorlevel%
    echo Check your TCAdmin configuration and network connectivity
    echo.
    pause
) 