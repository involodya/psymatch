#!/usr/bin/env python3

import os
import sys

def setup():
    print("=== PsyMatch Bot Setup ===\n")
    
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print("\nPlease provide the following information:\n")
    
    bot_token = input("1. Telegram Bot Token (from @BotFather): ").strip()
    if not bot_token:
        print("❌ Bot token is required!")
        sys.exit(1)
    
    admin_ids = input("2. Admin IDs (comma-separated, get from @userinfobot): ").strip()
    if not admin_ids:
        print("❌ At least one admin ID is required!")
        sys.exit(1)
    
    db_path = input("3. Database path (default: psymatch.db): ").strip() or "psymatch.db"
    log_file = input("4. Log file path (default: bot.log): ").strip() or "bot.log"
    
    env_content = f"""BOT_TOKEN={bot_token}
ADMIN_IDS={admin_ids}
DATABASE_PATH={db_path}
LOG_FILE={log_file}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully!")
    print("\nYou can now run the bot with: python bot.py")

if __name__ == '__main__':
    setup()

