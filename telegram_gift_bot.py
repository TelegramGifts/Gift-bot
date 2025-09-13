#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 ربات پیشرفته هشدار گیفت تلگرام
Advanced Telegram Gift Alert Bot
Persian/Farsi Version with Glass UI Design

Features:
- Real-time Star Gift monitoring
- User subscription management  
- Advanced filtering and notifications
- Beautiful Persian interface
- SQLite database for persistence
- Admin panel and statistics
"""

import asyncio
import logging
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from pyrogram import Client, filters, types
from pyrogram.handlers import MessageHandler
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, User as PyrogramUser
)

# Configure logging with Persian support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gift_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StarGift:
    """کلاس گیفت ستاره‌ای"""
    id: int
    title: str
    stars: int
    limited: bool
    sold_out: bool
    require_premium: bool
    can_upgrade: bool
    first_sale_date: Optional[int] = None
    last_sale_date: Optional[int] = None
    availability_remains: Optional[int] = None
    availability_total: Optional[int] = None

@dataclass
class User:
    """کلاس کاربر"""
    user_id: int
    username: Optional[str]
    first_name: str
    is_premium: bool
    subscription_date: datetime
    notifications_enabled: bool = True
    min_stars: int = 0
    max_stars: int = 1000000
    only_limited: bool = True
    language: str = 'fa'

class DatabaseManager:
    """مدیریت پایگاه داده"""
    
    def __init__(self, db_path: str = "gift_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """ایجاد جداول پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL,
                is_premium BOOLEAN DEFAULT 0,
                subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notifications_enabled BOOLEAN DEFAULT 1,
                min_stars INTEGER DEFAULT 0,
                max_stars INTEGER DEFAULT 1000000,
                only_limited BOOLEAN DEFAULT 1,
                language TEXT DEFAULT 'fa'
            )
        ''')
        
        # جدول گیفت‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                stars INTEGER NOT NULL,
                limited BOOLEAN DEFAULT 0,
                sold_out BOOLEAN DEFAULT 0,
                require_premium BOOLEAN DEFAULT 0,
                can_upgrade BOOLEAN DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                availability_remains INTEGER,
                availability_total INTEGER
            )
        ''')
        
        # جدول آمار
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                gifts_found INTEGER DEFAULT 0,
                notifications_sent INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user: User) -> bool:
        """افزودن کاربر جدید"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, is_premium, subscription_date, 
                 notifications_enabled, min_stars, max_stars, only_limited, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.user_id, user.username, user.first_name, user.is_premium,
                user.subscription_date, user.notifications_enabled, user.min_stars,
                user.max_stars, user.only_limited, user.language
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در افزودن کاربر: {e}")
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[User]:
        """دریافت اطلاعات کاربر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0], username=row[1], first_name=row[2],
                is_premium=bool(row[3]), subscription_date=datetime.fromisoformat(row[4]),
                notifications_enabled=bool(row[5]), min_stars=row[6], max_stars=row[7],
                only_limited=bool(row[8]), language=row[9]
            )
        return None
    
    def get_all_users(self) -> List[User]:
        """دریافت تمام کاربران فعال"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE notifications_enabled = 1')
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append(User(
                user_id=row[0], username=row[1], first_name=row[2],
                is_premium=bool(row[3]), subscription_date=datetime.fromisoformat(row[4]),
                notifications_enabled=bool(row[5]), min_stars=row[6], max_stars=row[7],
                only_limited=bool(row[8]), language=row[9]
            ))
        return users
    
    def add_gift(self, gift: StarGift) -> bool:
        """افزودن گیفت جدید"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO gifts 
                (id, title, stars, limited, sold_out, require_premium, can_upgrade,
                 availability_remains, availability_total, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                gift.id, gift.title, gift.stars, gift.limited, gift.sold_out,
                gift.require_premium, gift.can_upgrade, gift.availability_remains,
                gift.availability_total
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در افزودن گیفت: {e}")
            return False
        finally:
            conn.close()

class TelegramGiftBot:
    """ربات پیشرفته هشدار گیفت تلگرام"""
    
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        
        # Initialize client
        self.app = Client(
            "gift_alert_bot",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token
        )
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Gift monitoring
        self.known_gifts: Dict[int, StarGift] = {}
        self.gift_hash = 0
        self.monitoring_active = False
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'total_notifications': 0,
            'gifts_found': 0,
            'active_users': 0
        }
        
        # Persian text messages
        self.messages = {
            'welcome': '''
🎁 سلام و خوش آمدید! 

به ربات پیشرفته **هشدار گیفت تلگرام** خوش آمدید! 🌟

✨ قابلیت‌های ربات:
🔹 رصد لحظه‌ای گیفت‌های جدید تلگرام
🔹 فیلترهای پیشرفته بر اساس قیمت و نوع
🔹 اعلان‌های شخصی‌سازی شده
🔹 رابط کاربری زیبا و شیشه‌ای
🔹 پشتیبانی کامل از زبان فارسی

برای شروع، روی دکمه "عضویت" کلیک کنید! 👇
''',
            'subscribed': '''
🎉 تبریک! شما با موفقیت عضو شدید!

حالا من هر گیفت جدید و محدود تلگرام رو بهتون اطلاع می‌دم! 

⚙️ برای تنظیمات بیشتر از منوی زیر استفاده کنید:
''',
            'already_subscribed': '''
✅ شما قبلاً عضو هستید!

از منوی زیر می‌تونید تنظیمات رو تغییر بدید:
''',
            'new_gift_alert': '''
🎁 **گیفت جدید کشف شد!** 

📝 **نام گیفت:** {title}
🆔 **شناسه:** `{id}`
🌟 **قیمت:** {stars} ستاره
⭐ **محدود:** {limited}
🔴 **فروخته شده:** {sold_out}
💎 **نیاز به پریمیوم:** {premium}
♻️ **قابل ارتقاء:** {upgrade}

⏰ **زمان کشف:** {time}

🚀 هم اکنون به تلگرام برو و خریدش کن!
''',
            'settings_menu': '''
⚙️ **تنظیمات شما**

🔔 اعلان‌ها: {notifications}
💰 حداقل ستاره: {min_stars}
💎 حداکثر ستاره: {max_stars}
🎯 فقط محدود: {only_limited}
🌐 زبان: {language}

تنظیمات مورد نظر را انتخاب کنید:
''',
            'statistics': '''
📊 **آمار ربات**

👥 کل کاربران: {total_users}
🟢 کاربران فعال: {active_users}
🎁 گیفت‌های کشف شده: {gifts_found}
📨 اعلان‌های ارسالی: {notifications_sent}
⏰ زمان فعالیت: {uptime}

📈 ربات از {start_time} فعال است.
'''
        }
    
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        
        @self.app.on_message(filters.command("start"))
        async def start_command(client, message: Message):
            await self.handle_start(message)
        
        @self.app.on_message(filters.command("settings"))
        async def settings_command(client, message: Message):
            await self.handle_settings(message)
        
        @self.app.on_message(filters.command("stats"))
        async def stats_command(client, message: Message):
            await self.handle_statistics(message)
        
        @self.app.on_message(filters.command("help"))
        async def help_command(client, message: Message):
            await self.handle_help(message)
        
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.handle_callback(callback_query)
    
    async def handle_start(self, message: Message):
        """مدیریت دستور شروع"""
        user_id = message.from_user.id
        existing_user = self.db.get_user(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 عضویت در هشدارها", callback_data="subscribe")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
             InlineKeyboardButton("📊 آمار", callback_data="statistics")],
            [InlineKeyboardButton("❓ راهنما", callback_data="help")]
        ])
        
        if existing_user:
            await message.reply_text(
                self.messages['already_subscribed'],
                reply_markup=keyboard
            )
        else:
            await message.reply_text(
                self.messages['welcome'],
                reply_markup=keyboard
            )
    
    async def handle_callback(self, callback_query: CallbackQuery):
        """مدیریت کالبک‌ها"""
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data == "subscribe":
            await self.subscribe_user(callback_query)
        elif data == "settings":
            await self.show_settings(callback_query)
        elif data == "statistics":
            await self.show_statistics(callback_query)
        elif data == "help":
            await self.show_help(callback_query)
        elif data.startswith("toggle_"):
            await self.toggle_setting(callback_query, data)
        elif data.startswith("set_"):
            await self.set_value(callback_query, data)
    
    async def subscribe_user(self, callback_query: CallbackQuery):
        """عضویت کاربر"""
        user_data = callback_query.from_user
        user_id = user_data.id
        
        existing_user = self.db.get_user(user_id)
        
        if existing_user:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
                 InlineKeyboardButton("📊 آمار", callback_data="statistics")]
            ])
            
            await callback_query.edit_message_text(
                self.messages['already_subscribed'],
                reply_markup=keyboard
            )
        else:
            new_user = User(
                user_id=user_id,
                username=user_data.username,
                first_name=user_data.first_name,
                is_premium=user_data.is_premium or False,
                subscription_date=datetime.now()
            )
            
            if self.db.add_user(new_user):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
                     InlineKeyboardButton("📊 آمار", callback_data="statistics")]
                ])
                
                await callback_query.edit_message_text(
                    self.messages['subscribed'],
                    reply_markup=keyboard
                )
                logger.info(f"کاربر جدید عضو شد: {user_id}")
            else:
                await callback_query.answer("❌ خطا در عضویت! دوباره تلاش کنید.", show_alert=True)
    
    async def show_settings(self, callback_query: CallbackQuery):
        """نمایش تنظیمات"""
        user_id = callback_query.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            await callback_query.answer("ابتدا عضو شوید!", show_alert=True)
            return
        
        settings_text = self.messages['settings_menu'].format(
            notifications="فعال" if user.notifications_enabled else "غیرفعال",
            min_stars=user.min_stars,
            max_stars=user.max_stars,
            only_limited="بله" if user.only_limited else "خیر",
            language="فارسی" if user.language == 'fa' else "انگلیسی"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"🔔 اعلان‌ها: {'فعال' if user.notifications_enabled else 'غیرفعال'}", 
                callback_data="toggle_notifications"
            )],
            [InlineKeyboardButton(
                f"🎯 فقط محدود: {'بله' if user.only_limited else 'خیر'}", 
                callback_data="toggle_limited"
            )],
            [InlineKeyboardButton("💰 تنظیم حداقل ستاره", callback_data="set_min_stars"),
             InlineKeyboardButton("💎 تنظیم حداکثر ستاره", callback_data="set_max_stars")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ])
        
        await callback_query.edit_message_text(
            settings_text,
            reply_markup=keyboard
        )
    
    async def show_statistics(self, callback_query: CallbackQuery):
        """نمایش آمار"""
        all_users = self.db.get_all_users()
        uptime = datetime.now() - self.stats['start_time']
        
        stats_text = self.messages['statistics'].format(
            total_users=len(all_users),
            active_users=len([u for u in all_users if u.notifications_enabled]),
            gifts_found=self.stats['gifts_found'],
            notifications_sent=self.stats['total_notifications'],
            uptime=str(uptime).split('.')[0],
            start_time=self.stats['start_time'].strftime('%Y/%m/%d %H:%M:%S')
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ])
        
        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )
    
    async def monitor_gifts(self):
        """رصد مداوم گیفت‌ها"""
        logger.info("شروع رصد گیفت‌ها...")
        
        while self.monitoring_active:
            try:
                # Simulate gift monitoring (replace with actual Telegram API calls)
                await self.check_new_gifts()
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"خطا در رصد گیفت‌ها: {e}")
                await asyncio.sleep(10)
    
    async def check_new_gifts(self):
        """بررسی گیفت‌های جدید"""
        # This is a placeholder - replace with actual Telegram API implementation
        # You'll need to implement the actual gift monitoring logic here
        pass
    
    async def notify_users(self, gift: StarGift):
        """اطلاع‌رسانی به کاربران"""
        users = self.db.get_all_users()
        notification_count = 0
        
        for user in users:
            if not user.notifications_enabled:
                continue
                
            # Apply user filters
            if gift.stars < user.min_stars or gift.stars > user.max_stars:
                continue
            
            if user.only_limited and not gift.limited:
                continue
            
            try:
                message_text = self.messages['new_gift_alert'].format(
                    title=gift.title,
                    id=gift.id,
                    stars=gift.stars,
                    limited="✅ بله" if gift.limited else "❌ خیر",
                    sold_out="❌ بله" if gift.sold_out else "✅ خیر",
                    premium="✅ بله" if gift.require_premium else "❌ خیر",
                    upgrade="✅ بله" if gift.can_upgrade else "❌ خیر",
                    time=datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                )
                
                await self.app.send_message(
                    user.user_id,
                    message_text
                )
                notification_count += 1
                
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به {user.user_id}: {e}")
        
        self.stats['total_notifications'] += notification_count
        logger.info(f"گیفت جدید به {notification_count} کاربر اطلاع داده شد")
    
    async def start_bot(self):
        """شروع ربات"""
        logger.info("🚀 شروع ربات هشدار گیفت تلگرام...")
        
        # Setup handlers
        self.setup_handlers()
        
        # Start the bot
        await self.app.start()
        logger.info("✅ ربات با موفقیت شروع شد!")
        
        # Start gift monitoring
        self.monitoring_active = True
        monitoring_task = asyncio.create_task(self.monitor_gifts())
        
        # Send startup message to admin
        try:
            admin_message = f"""
🟢 **ربات آنلاین شد!**

⏰ زمان: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
🎯 حالت: رصد فعال
📊 آماده دریافت گیفت‌های جدید!
"""
            # Replace with your admin user ID
            # await self.app.send_message(ADMIN_USER_ID, admin_message, parse_mode="markdown")
        except:
            pass
        
        # Keep the bot running
        try:
            await asyncio.gather(monitoring_task)
        except KeyboardInterrupt:
            logger.info("🛑 ربات متوقف شد")
        finally:
            self.monitoring_active = False
            await self.app.stop()

# Configuration
API_ID = 26575668  # Replace with your API ID
API_HASH = "5b883684efd9b2b681e2b7e1e98c2e10"  # Replace with your API Hash
BOT_TOKEN = "8347736545:AAHEMiX-1wm6jNCAtj2U8SBnixcT9QLEYM4"  # Replace with your bot token

async def main():
    """تابع اصلی"""
    bot = TelegramGiftBot(API_ID, API_HASH, BOT_TOKEN)
    await bot.start_bot()

if __name__ == "__main__":
    print("""
🎁 ربات پیشرفته هشدار گیفت تلگرام
========================================
نسخه فارسی با رابط شیشه‌ای و قابلیت‌های پیشرفته

توسعه‌دهنده: AI Assistant
زبان: Python 3.8+
لایبرری: Pyrogram
""")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ربات متوقف شد!")
    except Exception as e:
        print(f"❌ خطا: {e}")
