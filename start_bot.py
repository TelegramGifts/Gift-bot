#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 اسکریپت راه‌اندازی سریع ربات گیفت
Quick Start Script for Gift Bot

این اسکریپت برای راه‌اندازی آسان و سریع ربات طراحی شده
"""

import os
import sys
import json
import asyncio
from pathlib import Path

def print_banner():
    """نمایش بنر شروع"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🎁 ربات پیشرفته هشدار گیفت تلگرام 🎁                 ║
║                                                              ║
║    ⚡ نسخه پیشرفته با رابط فارسی و قابلیت‌های شیشه‌ای ⚡      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🔥 ویژگی‌ها:                                                ║
║  • رصد لحظه‌ای گیفت‌های جدید تلگرام                          ║
║  • سیستم اعلان‌رسانی هوشمند و فیلترهای پیشرفته               ║
║  • پنل مدیریت کامل با آمار تفصیلی                           ║
║  • رابط کاربری فارسی زیبا                                   ║
║  • حفاظت ضد اسپم و بهینه‌سازی عملکرد                        ║
║                                                              ║
║  💻 توسعه‌دهنده: AI Assistant                                ║
║  📅 تاریخ: 2024                                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_python_version():
    """بررسی نسخه پایتون"""
    if sys.version_info < (3, 8):
        print("❌ خطا: پایتون 3.8 یا بالاتر مورد نیاز است!")
        print(f"نسخه فعلی: {sys.version}")
        sys.exit(1)
    print(f"✅ نسخه پایتون: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

def check_requirements():
    """بررسی وابستگی‌ها"""
    required_packages = [
        'pyrogram',
        'tgcrypto',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} (نصب نشده)")
    
    if missing_packages:
        print(f"\n📦 پکیج‌های مفقود: {', '.join(missing_packages)}")
        print("برای نصب: pip install -r requirements.txt")
        
        response = input("\nآیا می‌خواهید الان نصب کنید؟ (y/N): ").lower()
        if response in ['y', 'yes', 'بله']:
            os.system("pip install -r requirements.txt")
            print("✅ نصب کامل شد!")
        else:
            print("❌ لطفاً ابتدا وابستگی‌ها را نصب کنید.")
            sys.exit(1)

def setup_config():
    """تنظیم کانفیگ اولیه"""
    config_file = "bot_config.json"
    env_file = ".env"
    
    # بررسی فایل کانفیگ
    if not Path(config_file).exists():
        print("📁 فایل کانفیگ یافت نشد، ایجاد می‌شود...")
        
        default_config = {
            "telegram": {
                "api_id": 0,
                "api_hash": "",
                "bot_token": "",
                "session_name": "gift_alert_bot"
            },
            "monitoring": {
                "check_interval_seconds": 3,
                "max_retries": 5
            },
            "notification": {
                "max_notifications_per_minute": 20,
                "enable_smart_filtering": True
            },
            "admin": {
                "admin_user_ids": [],
                "enable_admin_panel": True,
                "log_level": "INFO"
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ فایل {config_file} ایجاد شد")
    
    # بررسی فایل .env
    if not Path(env_file).exists():
        if Path("env_example.txt").exists():
            print("📄 کپی کردن فایل نمونه .env...")
            with open("env_example.txt", 'r', encoding='utf-8') as src:
                content = src.read()
            with open(env_file, 'w', encoding='utf-8') as dst:
                dst.write(content)
            print(f"✅ فایل {env_file} ایجاد شد")
        else:
            print("⚠️ فایل env_example.txt یافت نشد")

def get_config_input():
    """دریافت اطلاعات کانفیگ از کاربر"""
    print("\n🔧 تنظیم اطلاعات ربات:")
    print("برای دریافت API ID و Hash به https://my.telegram.org بروید")
    print("برای دریافت Bot Token به @BotFather در تلگرام بروید")
    
    # خواندن کانفیگ فعلی
    config_file = "bot_config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # API ID
    if config["telegram"]["api_id"] == 0:
        api_id = input("\n🔑 API ID را وارد کنید: ").strip()
        if api_id.isdigit():
            config["telegram"]["api_id"] = int(api_id)
        else:
            print("❌ API ID باید عدد باشد!")
            return False
    
    # API Hash
    if not config["telegram"]["api_hash"]:
        api_hash = input("🔐 API Hash را وارد کنید: ").strip()
        if api_hash:
            config["telegram"]["api_hash"] = api_hash
        else:
            print("❌ API Hash نمی‌تواند خالی باشد!")
            return False
    
    # Bot Token
    if not config["telegram"]["bot_token"]:
        bot_token = input("🤖 Bot Token را وارد کنید: ").strip()
        if bot_token:
            config["telegram"]["bot_token"] = bot_token
        else:
            print("❌ Bot Token نمی‌تواند خالی باشد!")
            return False
    
    # Admin ID
    if not config["admin"]["admin_user_ids"]:
        admin_id = input("👑 User ID ادمین را وارد کنید: ").strip()
        if admin_id.isdigit():
            config["admin"]["admin_user_ids"] = [int(admin_id)]
        else:
            print("❌ User ID باید عدد باشد!")
            return False
    
    # ذخیره کانفیگ
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ تنظیمات ذخیره شد!")
    return True

def create_directories():
    """ایجاد دایرکتوری‌های مورد نیاز"""
    directories = ["logs", "backups", "data", "temp"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 {directory}/")
    
    print("✅ ساختار دایرکتوری‌ها ایجاد شد")

def run_tests():
    """اجرای تست‌های اولیه"""
    print("\n🧪 اجرای تست‌های اولیه...")
    
    try:
        # تست import
        from config import config
        print("✅ ماژول config")
        
        # تست کانفیگ
        errors = config.validate_config()
        if errors:
            print("❌ خطاهای کانفیگ:")
            for error in errors:
                print(f"  • {error}")
            return False
        else:
            print("✅ اعتبارسنجی کانفیگ")
        
        print("✅ تمام تست‌ها موفق!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
        return False

async def start_bot():
    """شروع ربات"""
    print("\n🚀 شروع ربات...")
    
    try:
        from main import main
        await main()
    except KeyboardInterrupt:
        print("\n⌨️ ربات توسط کاربر متوقف شد!")
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")

def main():
    """تابع اصلی"""
    print_banner()
    
    print("🔍 بررسی سیستم...")
    check_python_version()
    check_requirements()
    
    print("\n⚙️ تنظیم کانفیگ...")
    setup_config()
    create_directories()
    
    # بررسی نیاز به تنظیمات
    config_file = "bot_config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # چک کردن اینکه آیا اطلاعات اساسی موجود است
    needs_config = (
        config["telegram"]["api_id"] == 0 or
        not config["telegram"]["api_hash"] or
        not config["telegram"]["bot_token"] or
        not config["admin"]["admin_user_ids"]
    )
    
    if needs_config:
        print("\n⚠️ برخی تنظیمات ناقص هستند.")
        response = input("آیا می‌خواهید الان تنظیم کنید؟ (y/N): ").lower()
        
        if response in ['y', 'yes', 'بله']:
            if not get_config_input():
                print("❌ تنظیمات ناقص! لطفاً دوباره تلاش کنید.")
                sys.exit(1)
        else:
            print("❌ برای اجرای ربات، ابتدا تنظیمات را کامل کنید.")
            print(f"فایل {config_file} را ویرایش کنید.")
            sys.exit(1)
    
    # اجرای تست‌ها
    if not run_tests():
        print("❌ تست‌ها ناموفق! لطفاً تنظیمات را بررسی کنید.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🎉 آماده شروع!")
    print("📋 خلاصه:")
    print(f"  • API ID: {config['telegram']['api_id']}")
    print(f"  • Bot Token: {'تنظیم شده' if config['telegram']['bot_token'] else 'تنظیم نشده'}")
    print(f"  • تعداد ادمین‌ها: {len(config['admin']['admin_user_ids'])}")
    print(f"  • فاصله رصد: {config['monitoring']['check_interval_seconds']} ثانیه")
    print("="*60)
    
    input("\n⏎ Enter را بزنید تا ربات شروع شود...")
    
    print("\n🚀 راه‌اندازی ربات...")
    print("برای متوقف کردن ربات: Ctrl+C")
    print("-" * 40)
    
    # شروع ربات
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n👋 خداحافظ!")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    main()
