#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 ربات پیشرفته هشدار گیفت تلگرام - فایل اصلی
Advanced Telegram Gift Alert Bot - Main File

این ربات پیشرفته برای رصد و اطلاع‌رسانی گیفت‌های جدید تلگرام طراحی شده
Features:
- Real-time gift monitoring  
- Smart notification system
- Advanced user management
- Admin panel
- Persian UI with glass design
- Anti-spam protection
- Performance optimization

Author: AI Assistant
Version: 2.0.0
Language: Python 3.8+
Framework: Pyrogram
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Import bot modules
from config import config, setup_logging, is_admin
from telegram_gift_bot import TelegramGiftBot, DatabaseManager
from gift_monitor import TelegramGiftMonitor, GiftNotificationFormatter
try:
    from telethon import TelegramClient as TelethonClient
    TELETHON_OK = True
except Exception:
    TELETHON_OK = False
from notification_engine import create_notification_engine, NotificationType, NotificationPriority
from admin_panel import AdminPanel, setup_admin_handlers

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class AdvancedGiftBot:
    """کلاس اصلی ربات پیشرفته گیفت"""
    
    def __init__(self):
        self.config = config
        self.running = False
        self.db_manager = None
        self.gift_monitor = None
        self.notification_engine = None
        self.admin_panel = None
        self.main_bot = None
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'gifts_processed': 0,
            'notifications_sent': 0,
            'users_served': 0,
            'errors_occurred': 0
        }
    
    async def initialize(self):
        """مقداردهی اولیه ربات"""
        logger.info("🚀 شروع مقداردهی ربات...")
        
        try:
            # Validate configuration
            errors = self.config.validate_config()
            if errors:
                logger.error("❌ خطاهای تنظیمات:")
                for error in errors:
                    logger.error(f"  • {error}")
                return False
            
            # Create directory structure
            self.config.create_directory_structure()
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.config.database.db_path)
            logger.info("✅ مدیریت دیتابیس راه‌اندازی شد")
            
            # Initialize main bot
            self.main_bot = TelegramGiftBot(
                api_id=self.config.telegram.api_id,
                api_hash=self.config.telegram.api_hash,
                bot_token=self.config.telegram.bot_token
            )
            self.main_bot.db = self.db_manager
            logger.info("✅ ربات اصلی راه‌اندازی شد")
            
            # Initialize Telethon client (fallback for star gifts) if available
            telethon_client = None
            if TELETHON_OK:
                try:
                    telethon_client = TelethonClient(
                        session="gift_alert_user",
                        api_id=self.config.telegram.api_id,
                        api_hash=self.config.telegram.api_hash
                    )
                    # Must be a user session (not bot). If not logged in, this will require code on console.
                    # We avoid interactive flow here; expect session to exist.
                    try:
                        await telethon_client.connect()
                        if not await telethon_client.is_user_authorized():
                            logger.warning("سشن Telethon یافت نشد. ابتدا telethon_login.py را اجرا کنید تا وارد شوید.")
                            telethon_client = None
                    except Exception as e:
                        logger.warning(f"عدم امکان اتصال Telethon: {e}")
                        telethon_client = None
                except Exception as e:
                    logger.warning(f"عدم امکان راه‌اندازی Telethon fallback: {e}")
                    telethon_client = None

            # Initialize gift monitor with optional Telethon fallback
            self.gift_monitor = TelegramGiftMonitor(self.main_bot.app, telethon_client)
            self.gift_monitor.check_interval = self.config.monitoring.check_interval_seconds
            logger.info("✅ مانیتور گیفت راه‌اندازی شد")
            
            # Initialize notification engine
            self.notification_engine = create_notification_engine(
                self.main_bot.app, 
                self.db_manager
            )
            logger.info("✅ موتور اعلان‌رسانی راه‌اندازی شد")
            
            # Initialize admin panel
            self.admin_panel = AdminPanel(self.db_manager, self.main_bot.app)
            self.admin_panel.admin_users = set(self.config.admin.admin_user_ids)
            logger.info("✅ پنل ادمین راه‌اندازی شد")
            
            logger.info("🎉 مقداردهی ربات با موفقیت تکمیل شد!")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در مقداردهی ربات: {e}")
            return False
    
    async def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        logger.info("🔧 تنظیم هندلرها...")
        
        # Setup main bot handlers
        self.main_bot.setup_handlers()
        
        # Setup admin handlers
        await setup_admin_handlers(self.main_bot.app, self.admin_panel)
        
        # Setup gift monitoring callback
        async def gift_callback(gift_data, event_type):
            await self.handle_gift_event(gift_data, event_type)
        
        # Connect gift monitor to notification system (pass callback on start)
        self._gift_event_callback = gift_callback
        
        logger.info("✅ هندلرها تنظیم شدند")
    
    async def handle_gift_event(self, gift_data: dict, event_type: str):
        """مدیریت رویدادهای گیفت"""
        try:
            self.stats['gifts_processed'] += 1
            
            # Determine notification type
            if event_type == 'new':
                notification_type = NotificationType.NEW_GIFT
                priority = NotificationPriority.HIGH
            elif event_type == 'updated':
                notification_type = NotificationType.GIFT_UPDATE
                priority = NotificationPriority.NORMAL
            else:
                notification_type = NotificationType.NEW_GIFT
                priority = NotificationPriority.NORMAL
            
            # Get active users
            active_users = self.db_manager.get_all_users()
            user_ids = [user.user_id for user in active_users if user.notifications_enabled]
            
            if not user_ids:
                logger.info("هیچ کاربر فعالی برای اطلاع‌رسانی یافت نشد")
                return
            
            # Create notifications
            job_ids = self.notification_engine.create_notification(
                user_ids=user_ids,
                gift_data=gift_data,
                notification_type=notification_type,
                priority=priority
            )
            
            self.stats['notifications_sent'] += len(job_ids)
            
            logger.info(f"🔔 {len(job_ids)} اعلان برای گیفت {gift_data.get('title', 'نامشخص')} ایجاد شد")
            
            # Save gift to database
            from telegram_gift_bot import StarGift
            star_gift = StarGift(
                id=gift_data.get('id', 0),
                title=gift_data.get('title', ''),
                stars=gift_data.get('stars', 0),
                limited=gift_data.get('limited', False),
                sold_out=gift_data.get('sold_out', False),
                require_premium=gift_data.get('require_premium', False),
                can_upgrade=gift_data.get('can_upgrade', False),
                availability_remains=gift_data.get('availability_remains'),
                availability_total=gift_data.get('availability_total')
            )
            
            self.db_manager.add_gift(star_gift)
            
        except Exception as e:
            logger.error(f"خطا در مدیریت رویداد گیفت: {e}")
            self.stats['errors_occurred'] += 1
    
    async def start_services(self):
        """شروع سرویس‌ها"""
        logger.info("🚀 شروع سرویس‌ها...")
        
        tasks = []
        
        try:
            # Start main bot
            await self.main_bot.app.start()
            logger.info("✅ ربات تلگرام شروع شد")
            
            # Start notification engine
            notification_task = asyncio.create_task(
                self.notification_engine.start_processing()
            )
            tasks.append(notification_task)
            logger.info("✅ موتور اعلان‌رسانی شروع شد")
            
            # Start gift monitoring with event callback
            monitoring_task = asyncio.create_task(
                self.gift_monitor.start_monitoring(self._gift_event_callback)
            )
            tasks.append(monitoring_task)
            logger.info("✅ رصد گیفت‌ها شروع شد")
            
            # Send startup notification to admins
            await self.send_startup_notification()
            
            # Statistics reporting task
            stats_task = asyncio.create_task(self.periodic_stats_report())
            tasks.append(stats_task)
            
            self.running = True
            logger.info("🎉 تمام سرویس‌ها با موفقیت شروع شدند!")
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ خطا در شروع سرویس‌ها: {e}")
            await self.shutdown()
    
    async def send_startup_notification(self):
        """ارسال اعلان شروع به ادمین‌ها"""
        startup_message = f"""
🟢 **ربات گیفت آنلاین شد!**

⏰ زمان شروع: {self.stats['start_time'].strftime('%Y/%m/%d %H:%M:%S')}
🎯 وضعیت: رصد فعال
📊 آماده اطلاع‌رسانی گیفت‌های جدید

🔧 تنظیمات:
• فاصله رصد: {self.config.monitoring.check_interval_seconds} ثانیه
• حداکثر اعلان/دقیقه: {self.config.notification.max_notifications_per_minute}
• کاربران فعال: {len(self.db_manager.get_all_users())}

✅ ربات آماده است!
"""
        
        for admin_id in self.config.admin.admin_user_ids:
            try:
                await self.main_bot.app.send_message(
                    admin_id,
                    startup_message
                )
            except Exception as e:
                logger.warning(f"نتوانست پیام شروع به ادمین {admin_id} ارسال کند: {e}")
    
    async def periodic_stats_report(self):
        """گزارش دوره‌ای آمار"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                if datetime.now().hour == 12:  # Daily report at noon
                    await self.send_daily_report()
                    
            except Exception as e:
                logger.error(f"خطا در گزارش آمار: {e}")
    
    async def send_daily_report(self):
        """ارسال گزارش روزانه"""
        uptime = datetime.now() - self.stats['start_time']
        
        report = f"""
📊 **گزارش روزانه ربات گیفت**

⏰ تاریخ: {datetime.now().strftime('%Y/%m/%d')}
🚀 مدت فعالیت: {uptime.days} روز، {uptime.seconds//3600} ساعت

📈 **آمار عملکرد:**
• گیفت‌های پردازش شده: {self.stats['gifts_processed']:,}
• اعلان‌های ارسالی: {self.stats['notifications_sent']:,}
• کاربران فعال: {len(self.db_manager.get_all_users()):,}
• خطاهای رخ داده: {self.stats['errors_occurred']:,}

🎁 **آمار گیفت‌ها:**
{self.gift_monitor.get_gift_stats() if self.gift_monitor else 'در دسترس نیست'}

🔔 **آمار اعلان‌ها:**
{self.notification_engine.get_statistics() if self.notification_engine else 'در دسترس نیست'}

💚 ربات با موفقیت در حال کار است!
"""
        
        for admin_id in self.config.admin.admin_user_ids:
            try:
                await self.main_bot.app.send_message(
                    admin_id,
                    report
                )
            except Exception as e:
                logger.warning(f"نتوانست گزارش روزانه به ادمین {admin_id} ارسال کند: {e}")
    
    async def shutdown(self):
        """خاموش کردن ربات"""
        logger.info("🛑 شروع فرآیند خاموش کردن ربات...")
        
        self.running = False
        
        try:
            # Stop services
            if self.gift_monitor:
                self.gift_monitor.stop_monitoring()
            
            if self.notification_engine:
                self.notification_engine.stop_processing()
            
            # Stop bot
            if self.main_bot and self.main_bot.app:
                await self.main_bot.app.stop()
            
            # Send shutdown notification
            await self.send_shutdown_notification()
            
            logger.info("✅ ربات با موفقیت خاموش شد")
            
        except Exception as e:
            logger.error(f"خطا در خاموش کردن ربات: {e}")
    
    async def send_shutdown_notification(self):
        """ارسال اعلان خاموش شدن"""
        uptime = datetime.now() - self.stats['start_time']
        
        shutdown_message = f"""
🔴 **ربات گیفت خاموش شد**

⏰ زمان خاموش شدن: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
⌛ مدت فعالیت: {uptime.days} روز، {uptime.seconds//3600} ساعت

📊 **آمار نهایی:**
• گیفت‌های پردازش شده: {self.stats['gifts_processed']:,}
• اعلان‌های ارسالی: {self.stats['notifications_sent']:,}
• خطاهای رخ داده: {self.stats['errors_occurred']:,}

💤 ربات به حالت خاموش درآمد.
"""
        
        for admin_id in self.config.admin.admin_user_ids:
            try:
                await self.main_bot.app.send_message(
                    admin_id,
                    shutdown_message
                )
            except:
                pass  # Ignore errors during shutdown

def signal_handler(signum, frame):
    """مدیریت سیگنال‌های سیستم"""
    logger.info(f"دریافت سیگنال {signum}، شروع خاموش کردن...")
    global bot_instance
    if bot_instance:
        asyncio.create_task(bot_instance.shutdown())

async def main():
    """تابع اصلی"""
    global bot_instance
    
    print("""
🎁 ربات پیشرفته هشدار گیفت تلگرام
========================================
نسخه پیشرفته با قابلیت‌های شیشه‌ای و هوشمند

🚀 ویژگی‌ها:
• رصد لحظه‌ای گیفت‌های جدید
• سیستم اعلان‌رسانی هوشمند  
• پنل مدیریت پیشرفته
• رابط کاربری فارسی زیبا
• حفاظت ضد اسپم
• بهینه‌سازی عملکرد

💻 توسعه‌دهنده: AI Assistant
📅 نسخه: 2.0.0 - {datetime.now().strftime('%Y/%m/%d')}
""")
    
    # Create bot instance
    bot_instance = AdvancedGiftBot()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize bot
        if not await bot_instance.initialize():
            logger.error("❌ مقداردهی ربات ناموفق بود!")
            return
        
        # Setup handlers
        await bot_instance.setup_handlers()
        
        # Start services
        await bot_instance.start_services()
        
    except KeyboardInterrupt:
        logger.info("⌨️ دریافت کیبورد اینتراپت")
        await bot_instance.shutdown()
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")
        await bot_instance.shutdown()
    finally:
        logger.info("👋 خداحافظ!")

if __name__ == "__main__":
    # Global bot instance for signal handling
    bot_instance = None
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ربات توسط کاربر متوقف شد!")
    except Exception as e:
        print(f"❌ خطای کلی: {e}")
        logger.error(f"خطای کلی: {e}")
    finally:
        print("🎉 تشکر از استفاده از ربات گیفت!")
        sys.exit(0)
