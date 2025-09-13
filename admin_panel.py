#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
👑 پنل مدیریت پیشرفته ربات گیفت
Advanced Admin Panel for Gift Bot

قابلیت‌ها:
- مدیریت کاربران
- آمار تفصیلی
- کنترل ربات
- تنظیمات پیشرفته
- پشتیبان‌گیری و بازیابی
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3
import os
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logger = logging.getLogger(__name__)

class AdminPanel:
    """پنل مدیریت پیشرفته"""
    
    def __init__(self, db_manager, bot_client: Client):
        self.db = db_manager
        self.client = bot_client
        self.admin_users = set()  # IDs of admin users
        self.load_admin_config()
        
        # Statistics tracking
        self.daily_stats = {}
        self.bot_status = {
            'started_at': datetime.now(),
            'gifts_monitored': 0,
            'notifications_sent': 0,
            'errors_count': 0,
            'uptime': timedelta(0)
        }
    
    def load_admin_config(self):
        """بارگذاری تنظیمات ادمین"""
        try:
            if os.path.exists('admin_config.json'):
                with open('admin_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.admin_users = set(config.get('admin_users', []))
            else:
                # Default admin config
                self.admin_users = {123456789}  # Replace with actual admin user ID
                self.save_admin_config()
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات ادمین: {e}")
    
    def save_admin_config(self):
        """ذخیره تنظیمات ادمین"""
        try:
            config = {'admin_users': list(self.admin_users)}
            with open('admin_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات ادمین: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """بررسی ادمین بودن کاربر"""
        return user_id in self.admin_users
    
    async def handle_admin_command(self, message: Message):
        """مدیریت دستورات ادمین"""
        if not self.is_admin(message.from_user.id):
            await message.reply("🚫 شما دسترسی ادمین ندارید!")
            return
        
        command = message.command[0] if message.command else ""
        
        if command == "admin":
            await self.show_admin_panel(message)
        elif command == "stats":
            await self.show_detailed_stats(message)
        elif command == "users":
            await self.show_user_management(message)
        elif command == "broadcast":
            await self.handle_broadcast(message)
        elif command == "backup":
            await self.create_backup(message)
        elif command == "logs":
            await self.show_logs(message)
    
    async def show_admin_panel(self, message: Message):
        """نمایش پنل ادمین اصلی"""
        uptime = datetime.now() - self.bot_status['started_at']
        
        panel_text = f"""
👑 **پنل مدیریت ربات گیفت**

📊 **وضعیت کلی:**
🟢 آنلاین: {uptime.days} روز، {uptime.seconds//3600} ساعت
🎁 گیفت‌های رصد شده: {self.bot_status['gifts_monitored']:,}
📨 اعلان‌های ارسالی: {self.bot_status['notifications_sent']:,}
❌ خطاها: {self.bot_status['errors_count']:,}

⚡ **دستورات سریع:**
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 آمار تفصیلی", callback_data="admin_detailed_stats"),
             InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast"),
             InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="admin_backup")],
            [InlineKeyboardButton("📝 مشاهده لاگ‌ها", callback_data="admin_logs"),
             InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("🔄 ریست ربات", callback_data="admin_restart"),
             InlineKeyboardButton("🛑 خاموش کردن", callback_data="admin_shutdown")]
        ])
        
        await message.reply_text(panel_text, reply_markup=keyboard)
    
    async def show_detailed_stats(self, message_or_query):
        """نمایش آمار تفصیلی"""
        # Get database statistics
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # User statistics
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE notifications_enabled = 1")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        premium_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_date >= datetime('now', '-7 days')")
        new_users_week = cursor.fetchone()[0]
        
        # Gift statistics
        cursor.execute("SELECT COUNT(*) FROM gifts")
        total_gifts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gifts WHERE limited = 1")
        limited_gifts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gifts WHERE sold_out = 0")
        available_gifts = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', subscription_date) as date, COUNT(*) 
            FROM users 
            WHERE subscription_date >= datetime('now', '-30 days')
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 7
        """)
        daily_signups = cursor.fetchall()
        
        conn.close()
        
        # Calculate growth rate
        growth_rate = (new_users_week / max(total_users - new_users_week, 1)) * 100
        
        stats_text = f"""
📊 **آمار تفصیلی ربات**

👥 **کاربران:**
• کل کاربران: {total_users:,}
• کاربران فعال: {active_users:,} ({(active_users/max(total_users,1)*100):.1f}%)
• کاربران پریمیوم: {premium_users:,} ({(premium_users/max(total_users,1)*100):.1f}%)
• عضو جدید (7 روز): {new_users_week:,}
• نرخ رشد: {growth_rate:.1f}%

🎁 **گیفت‌ها:**
• کل گیفت‌ها: {total_gifts:,}
• گیفت‌های محدود: {limited_gifts:,}
• گیفت‌های موجود: {available_gifts:,}

📈 **فعالیت اخیر (7 روز):**
"""
        
        for date, count in daily_signups:
            stats_text += f"• {date}: {count} عضو جدید\n"
        
        # System info
        uptime = datetime.now() - self.bot_status['started_at']
        stats_text += f"""
💻 **سیستم:**
• زمان فعالیت: {uptime.days} روز، {uptime.seconds//3600}:{(uptime.seconds%3600)//60:02d}
• حافظه استفاده شده: {self._get_memory_usage():.1f} MB
• حجم دیتابیس: {self._get_database_size():.1f} MB
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_detailed_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main")]
        ])
        
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.edit_message_text(stats_text, reply_markup=keyboard)
        else:
            await message_or_query.reply_text(stats_text, reply_markup=keyboard)
    
    async def show_user_management(self, query: CallbackQuery):
        """نمایش پنل مدیریت کاربران"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Recent users
        cursor.execute("""
            SELECT user_id, first_name, username, subscription_date, notifications_enabled
            FROM users 
            ORDER BY subscription_date DESC 
            LIMIT 10
        """)
        recent_users = cursor.fetchall()
        
        # Top active users (this would need additional tracking)
        cursor.execute("""
            SELECT user_id, first_name, username, subscription_date
            FROM users 
            WHERE notifications_enabled = 1 
            ORDER BY subscription_date ASC 
            LIMIT 5
        """)
        active_users = cursor.fetchall()
        
        conn.close()
        
        text = "👥 **مدیریت کاربران**\n\n"
        text += "📅 **کاربران اخیر:**\n"
        
        for user in recent_users:
            status = "🟢" if user[4] else "🔴"
            username = f"@{user[2]}" if user[2] else "بدون نام کاربری"
            date = datetime.fromisoformat(user[3]).strftime('%m/%d')
            text += f"{status} {user[1]} ({username}) - {date}\n"
        
        text += "\n⭐ **کاربران فعال قدیمی:**\n"
        for user in active_users:
            username = f"@{user[2]}" if user[2] else "بدون نام کاربری"
            date = datetime.fromisoformat(user[3]).strftime('%Y/%m/%d')
            text += f"👤 {user[1]} ({username}) - {date}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
             InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_user_stats")],
            [InlineKeyboardButton("🚫 بن کاربر", callback_data="admin_ban_user"),
             InlineKeyboardButton("✅ آنبن کاربر", callback_data="admin_unban_user")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
    
    async def handle_broadcast(self, query: CallbackQuery):
        """مدیریت پیام همگانی"""
        text = """
📢 **ارسال پیام همگانی**

برای ارسال پیام همگانی، کامند زیر را استفاده کنید:
`/broadcast متن پیام شما`

مثال:
`/broadcast سلام! این یک پیام تست است 🎁`

⚠️ **توجه:** پیام به تمام کاربران فعال ارسال می‌شود.
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
    
    async def send_broadcast_message(self, message: Message):
        """ارسال پیام همگانی"""
        if not self.is_admin(message.from_user.id):
            return
        
        if len(message.command) < 2:
            await message.reply("❌ لطفاً متن پیام را وارد کنید!\nمثال: `/broadcast سلام!`")
            return
        
        broadcast_text = " ".join(message.command[1:])
        users = self.db.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        status_message = await message.reply("📤 شروع ارسال پیام همگانی...")
        
        for i, user in enumerate(users):
            try:
                await self.client.send_message(user.user_id, broadcast_text)
                sent_count += 1
                
                # Update status every 10 users
                if (i + 1) % 10 == 0:
                    await status_message.edit_text(
                        f"📤 در حال ارسال... {i + 1}/{len(users)}\n"
                        f"✅ موفق: {sent_count} | ❌ ناموفق: {failed_count}"
                    )
                
                await asyncio.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                failed_count += 1
                logger.error(f"خطا در ارسال به {user.user_id}: {e}")
        
        final_text = f"""
✅ **ارسال پیام همگانی تکمیل شد!**

📊 **نتایج:**
• کل کاربران: {len(users)}
• ارسال موفق: {sent_count}
• ارسال ناموفق: {failed_count}
• نرخ موفقیت: {(sent_count/len(users)*100):.1f}%

⏰ زمان: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
"""
        
        await status_message.edit_text(final_text)
    
    async def create_backup(self, query: CallbackQuery):
        """ایجاد پشتیبان"""
        try:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = Path("backups") / backup_name
            backup_path.parent.mkdir(exist_ok=True)
            
            # Copy database
            import shutil
            shutil.copy2(self.db.db_path, backup_path)
            
            # Create config backup
            config_backup = {
                'timestamp': datetime.now().isoformat(),
                'bot_status': self.bot_status,
                'admin_users': list(self.admin_users)
            }
            
            config_path = backup_path.with_suffix('.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_backup, f, ensure_ascii=False, indent=2, default=str)
            
            text = f"""
💾 **پشتیبان‌گیری تکمیل شد!**

📁 فایل دیتابیس: `{backup_name}`
📄 فایل تنظیمات: `{config_path.name}`
📂 مسیر: `backups/`

⏰ زمان: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
💽 حجم: {backup_path.stat().st_size / 1024:.1f} KB
"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 ارسال فایل", callback_data=f"admin_send_backup_{backup_name}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در پشتیبان‌گیری: {e}")
    
    def _get_memory_usage(self) -> float:
        """دریافت میزان استفاده از حافظه"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def _get_database_size(self) -> float:
        """دریافت حجم دیتابیس"""
        try:
            return Path(self.db.db_path).stat().st_size / 1024 / 1024  # MB
        except FileNotFoundError:
            return 0.0
    
    async def handle_admin_callback(self, query: CallbackQuery):
        """مدیریت کالبک‌های ادمین"""
        if not self.is_admin(query.from_user.id):
            await query.answer("🚫 دسترسی غیرمجاز!", show_alert=True)
            return
        
        data = query.data
        
        if data == "admin_main":
            await self.show_admin_panel(query.message)
        elif data == "admin_detailed_stats":
            await self.show_detailed_stats(query)
        elif data == "admin_users":
            await self.show_user_management(query)
        elif data == "admin_broadcast":
            await self.handle_broadcast(query)
        elif data == "admin_backup":
            await self.create_backup(query)
        elif data.startswith("admin_send_backup_"):
            backup_name = data.replace("admin_send_backup_", "")
            await self.send_backup_file(query, backup_name)
    
    async def send_backup_file(self, query: CallbackQuery, backup_name: str):
        """ارسال فایل پشتیبان"""
        try:
            backup_path = Path("backups") / backup_name
            if backup_path.exists():
                await self.client.send_document(
                    query.from_user.id,
                    str(backup_path),
                    caption=f"💾 فایل پشتیبان: {backup_name}\n⏰ {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
                )
                await query.answer("✅ فایل ارسال شد!")
            else:
                await query.answer("❌ فایل پیدا نشد!", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ خطا: {e}", show_alert=True)

# Usage example
async def setup_admin_handlers(app: Client, admin_panel: AdminPanel):
    """تنظیم هندلرهای ادمین"""
    
    @app.on_message(filters.command(["admin", "stats", "users", "logs"]))
    async def admin_commands(client, message):
        await admin_panel.handle_admin_command(message)
    
    @app.on_message(filters.command("broadcast"))
    async def broadcast_command(client, message):
        await admin_panel.send_broadcast_message(message)
    
    @app.on_callback_query(filters.regex(r"^admin_"))
    async def admin_callbacks(client, query):
        await admin_panel.handle_admin_callback(query)
