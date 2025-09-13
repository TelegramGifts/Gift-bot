#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔔 موتور پیشرفته اعلان‌رسانی
Advanced Notification Engine

قابلیت‌ها:
- ارسال اعلان‌های هوشمند
- فیلترهای پیشرفته
- قالب‌های شخصی‌سازی شده
- مدیریت صف ارسال
- آمارگیری دقیق
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden

logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    """اولویت اعلان‌ها"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class NotificationType(Enum):
    """نوع اعلان"""
    NEW_GIFT = "new_gift"
    GIFT_UPDATE = "gift_update"
    PRICE_DROP = "price_drop"
    LIMITED_AVAILABLE = "limited_available"
    SYSTEM_ALERT = "system_alert"
    PROMOTION = "promotion"

@dataclass
class NotificationTemplate:
    """قالب اعلان"""
    name: str
    title: str
    message: str
    emoji: str
    priority: NotificationPriority
    has_buttons: bool = False
    custom_buttons: List[Dict] = None

@dataclass
class NotificationFilter:
    """فیلتر اعلان"""
    min_stars: int = 0
    max_stars: int = 1000000
    only_limited: bool = True
    only_premium: bool = False
    exclude_premium_required: bool = False
    keywords: List[str] = None
    excluded_keywords: List[str] = None
    time_restrictions: Dict = None

@dataclass
class NotificationJob:
    """وظیفه اعلان"""
    id: str
    user_id: int
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    created_at: datetime
    scheduled_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    metadata: Dict = None
    buttons: Optional[InlineKeyboardMarkup] = None

class NotificationQueue:
    """صف اعلان‌ها"""
    
    def __init__(self):
        self.queue: List[NotificationJob] = []
        self.processing = False
        self.stats = {
            'total_queued': 0,
            'total_sent': 0,
            'total_failed': 0,
            'last_reset': datetime.now()
        }
    
    def add_job(self, job: NotificationJob):
        """افزودن وظیفه به صف"""
        # Sort by priority and creation time
        self.queue.append(job)
        self.queue.sort(key=lambda x: (x.priority.value, x.created_at), reverse=True)
        self.stats['total_queued'] += 1
    
    def get_next_job(self) -> Optional[NotificationJob]:
        """دریافت وظیفه بعدی"""
        now = datetime.now()
        for i, job in enumerate(self.queue):
            if job.scheduled_at <= now and job.attempts < job.max_attempts:
                return self.queue.pop(i)
        return None
    
    def requeue_job(self, job: NotificationJob, delay_seconds: int = 60):
        """قرار دادن مجدد وظیفه در صف"""
        job.attempts += 1
        job.scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)
        if job.attempts < job.max_attempts:
            self.add_job(job)
        else:
            self.stats['total_failed'] += 1
    
    def get_stats(self) -> Dict:
        """دریافت آمار صف"""
        return {
            **self.stats,
            'queue_size': len(self.queue),
            'processing': self.processing
        }

class SmartNotificationEngine:
    """موتور هوشمند اعلان‌رسانی"""
    
    def __init__(self, client: Client, db_manager):
        self.client = client
        self.db = db_manager
        self.queue = NotificationQueue()
        self.templates = {}
        self.filters = {}
        self.running = False
        
        # Rate limiting
        self.rate_limits = {
            'messages_per_minute': 20,
            'messages_per_hour': 1000
        }
        self.sent_messages = []
        
        # Smart features
        self.user_preferences = {}
        self.notification_history = {}
        
        # Load templates and filters
        self.load_notification_templates()
        self.load_user_filters()
    
    def load_notification_templates(self):
        """بارگذاری قالب‌های اعلان"""
        self.templates = {
            NotificationType.NEW_GIFT: NotificationTemplate(
                name="گیفت جدید",
                title="🎁 گیفت جدید کشف شد!",
                message="""
🎁 **{title}** منتشر شد!

🆔 شناسه: `{id}`
🌟 قیمت: **{stars:,} ستاره**
⭐ محدود: {limited}
💎 پریمیوم: {premium_required}
♻️ قابل ارتقاء: {upgradeable}

{availability_info}

⏰ زمان کشف: {discovery_time}

🚀 **سریع عمل کن! گیفت‌های محدود سریع تمام می‌شوند!**
""",
                emoji="🎁",
                priority=NotificationPriority.HIGH,
                has_buttons=True,
                custom_buttons=[
                    {"text": "🛒 خرید سریع", "url": "https://t.me/giftbot"},
                    {"text": "📊 جزئیات بیشتر", "callback_data": "gift_details_{id}"}
                ]
            ),
            
            NotificationType.PRICE_DROP: NotificationTemplate(
                name="کاهش قیمت",
                title="💰 قیمت کاهش یافت!",
                message="""
💰 **قیمت گیفت کاهش یافت!**

🎁 **{title}**
🆔 `{id}`

📉 قیمت قبلی: ~~{old_price:,}~~ ستاره
🌟 قیمت جدید: **{new_price:,} ستاره**
💵 صرفه‌جویی: **{savings:,} ستاره ({savings_percent:.1f}%)**

⏰ زمان: {update_time}

🎯 **فرصت طلایی برای خرید!**
""",
                emoji="💰",
                priority=NotificationPriority.URGENT,
                has_buttons=True
            ),
            
            NotificationType.LIMITED_AVAILABLE: NotificationTemplate(
                name="گیفت محدود موجود",
                title="⚡ گیفت محدود موجود است!",
                message="""
⚡ **گیفت محدود در دسترس!**

🎁 **{title}**
📦 موجودی: **{remaining}/{total}** ({percentage:.1f}%)
🌟 قیمت: {stars:,} ستاره

⚠️ **هشدار:** تنها {remaining} عدد باقی مانده!

⏱️ **عجله کن!**
""",
                emoji="⚡",
                priority=NotificationPriority.URGENT,
                has_buttons=True
            )
        }
    
    def load_user_filters(self):
        """بارگذاری فیلترهای کاربران"""
        users = self.db.get_all_users()
        for user in users:
            self.filters[user.user_id] = NotificationFilter(
                min_stars=user.min_stars,
                max_stars=user.max_stars,
                only_limited=user.only_limited
            )
    
    def should_notify_user(self, user_id: int, gift_data: Dict, notification_type: NotificationType) -> bool:
        """تعیین اینکه آیا باید به کاربر اطلاع داد"""
        user_filter = self.filters.get(user_id)
        if not user_filter:
            return False
        
        # Check basic filters
        stars = gift_data.get('stars', 0)
        if stars < user_filter.min_stars or stars > user_filter.max_stars:
            return False
        
        if user_filter.only_limited and not gift_data.get('limited', False):
            return False
        
        if user_filter.exclude_premium_required and gift_data.get('require_premium', False):
            return False
        
        # Check keywords
        if user_filter.keywords:
            title = gift_data.get('title', '').lower()
            if not any(keyword.lower() in title for keyword in user_filter.keywords):
                return False
        
        if user_filter.excluded_keywords:
            title = gift_data.get('title', '').lower()
            if any(keyword.lower() in title for keyword in user_filter.excluded_keywords):
                return False
        
        # Check time restrictions
        if user_filter.time_restrictions:
            current_hour = datetime.now().hour
            allowed_hours = user_filter.time_restrictions.get('allowed_hours', [])
            if allowed_hours and current_hour not in allowed_hours:
                return False
        
        # Check notification frequency (anti-spam)
        return self._check_notification_frequency(user_id, notification_type)
    
    def _check_notification_frequency(self, user_id: int, notification_type: NotificationType) -> bool:
        """بررسی تناوب اعلان‌ها (ضد اسپم)"""
        now = datetime.now()
        user_history = self.notification_history.get(user_id, [])
        
        # Remove old notifications (older than 1 hour)
        user_history = [n for n in user_history if now - n['timestamp'] < timedelta(hours=1)]
        self.notification_history[user_id] = user_history
        
        # Count recent notifications of same type
        same_type_count = sum(1 for n in user_history if n['type'] == notification_type)
        
        # Limits per hour
        limits = {
            NotificationType.NEW_GIFT: 10,
            NotificationType.PRICE_DROP: 5,
            NotificationType.LIMITED_AVAILABLE: 3,
            NotificationType.SYSTEM_ALERT: 2
        }
        
        return same_type_count < limits.get(notification_type, 5)
    
    def create_notification(self, user_ids: List[int], gift_data: Dict, 
                          notification_type: NotificationType, 
                          priority: NotificationPriority = NotificationPriority.NORMAL) -> List[str]:
        """ایجاد اعلان جدید"""
        job_ids = []
        template = self.templates.get(notification_type)
        
        if not template:
            logger.error(f"قالب برای نوع {notification_type} یافت نشد")
            return job_ids
        
        for user_id in user_ids:
            if not self.should_notify_user(user_id, gift_data, notification_type):
                continue
            
            # Generate message from template
            message = self._generate_message(template, gift_data)
            buttons = self._generate_buttons(template, gift_data) if template.has_buttons else None
            
            # Create job
            job_id = hashlib.md5(f"{user_id}_{notification_type.value}_{datetime.now().isoformat()}".encode()).hexdigest()
            job = NotificationJob(
                id=job_id,
                user_id=user_id,
                message=message,
                notification_type=notification_type,
                priority=priority,
                created_at=datetime.now(),
                scheduled_at=datetime.now(),
                metadata=gift_data,
                buttons=buttons
            )
            
            self.queue.add_job(job)
            job_ids.append(job_id)
        
        return job_ids
    
    def _generate_message(self, template: NotificationTemplate, data: Dict) -> str:
        """تولید پیام از قالب"""
        try:
            # Prepare data for formatting
            format_data = data.copy()
            
            # Add helper fields
            format_data.update({
                'limited': "✅ بله" if data.get('limited') else "❌ خیر",
                'premium_required': "✅ بله" if data.get('require_premium') else "❌ خیر",
                'upgradeable': "✅ بله" if data.get('can_upgrade') else "❌ خیر",
                'discovery_time': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                'update_time': datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            })
            
            # Availability info
            if data.get('availability_remains') and data.get('availability_total'):
                remaining = data['availability_remains']
                total = data['availability_total']
                percentage = (remaining / total) * 100
                format_data['availability_info'] = f"📦 موجودی: {remaining}/{total} ({percentage:.1f}%)"
            else:
                format_data['availability_info'] = ""
            
            return template.message.format(**format_data)
            
        except KeyError as e:
            logger.error(f"خطا در فرمت پیام: فیلد {e} یافت نشد")
            return f"خطا در تولید پیام: {e}"
        except Exception as e:
            logger.error(f"خطا در تولید پیام: {e}")
            return "خطا در تولید پیام"
    
    def _generate_buttons(self, template: NotificationTemplate, data: Dict) -> Optional[InlineKeyboardMarkup]:
        """تولید دکمه‌ها"""
        if not template.custom_buttons:
            return None
        
        try:
            buttons = []
            for button_data in template.custom_buttons:
                text = button_data['text'].format(**data)
                
                if 'url' in button_data:
                    url = button_data['url'].format(**data)
                    buttons.append(InlineKeyboardButton(text, url=url))
                elif 'callback_data' in button_data:
                    callback = button_data['callback_data'].format(**data)
                    buttons.append(InlineKeyboardButton(text, callback_data=callback))
            
            # Arrange buttons in rows
            keyboard = []
            for i in range(0, len(buttons), 2):
                row = buttons[i:i+2]
                keyboard.append(row)
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"خطا در تولید دکمه‌ها: {e}")
            return None
    
    async def start_processing(self):
        """شروع پردازش صف اعلان‌ها"""
        if self.running:
            return
        
        self.running = True
        logger.info("🔔 موتور اعلان‌رسانی شروع شد")
        
        while self.running:
            try:
                await self._process_queue()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"خطا در پردازش صف اعلان‌ها: {e}")
                await asyncio.sleep(5)
    
    async def _process_queue(self):
        """پردازش صف اعلان‌ها"""
        if self.queue.processing:
            return
        
        self.queue.processing = True
        
        try:
            # Check rate limits
            if not self._check_rate_limits():
                return
            
            job = self.queue.get_next_job()
            if not job:
                return
            
            success = await self._send_notification(job)
            
            if success:
                self.queue.stats['total_sent'] += 1
                # Record notification in history
                self._record_notification(job)
            else:
                self.queue.requeue_job(job)
        
        finally:
            self.queue.processing = False
    
    def _check_rate_limits(self) -> bool:
        """بررسی محدودیت‌های نرخ ارسال"""
        now = datetime.now()
        
        # Remove old messages
        self.sent_messages = [
            msg for msg in self.sent_messages 
            if now - msg < timedelta(minutes=1)
        ]
        
        # Check limits
        if len(self.sent_messages) >= self.rate_limits['messages_per_minute']:
            return False
        
        return True
    
    async def _send_notification(self, job: NotificationJob) -> bool:
        """ارسال اعلان"""
        try:
            await self.client.send_message(
                job.user_id,
                job.message,
                reply_markup=job.buttons
            )
            
            self.sent_messages.append(datetime.now())
            logger.info(f"اعلان به {job.user_id} ارسال شد: {job.notification_type.value}")
            return True
            
        except FloodWait as e:
            logger.warning(f"محدودیت ارسال: {e.value} ثانیه")
            job.scheduled_at = datetime.now() + timedelta(seconds=e.value)
            self.queue.requeue_job(job, delay_seconds=e.value)
            return False
            
        except (UserIsBlocked, ChatWriteForbidden) as e:
            logger.info(f"کاربر {job.user_id} ربات را بلاک کرده: {e}")
            # Mark user as inactive
            await self._mark_user_inactive(job.user_id)
            return False
            
        except Exception as e:
            logger.error(f"خطا در ارسال اعلان به {job.user_id}: {e}")
            return False
    
    def _record_notification(self, job: NotificationJob):
        """ثبت اعلان در تاریخچه"""
        user_id = job.user_id
        if user_id not in self.notification_history:
            self.notification_history[user_id] = []
        
        self.notification_history[user_id].append({
            'type': job.notification_type,
            'timestamp': datetime.now(),
            'job_id': job.id
        })
    
    async def _mark_user_inactive(self, user_id: int):
        """علامت‌گذاری کاربر به عنوان غیرفعال"""
        # Update database to mark notifications as disabled
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET notifications_enabled = 0 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در غیرفعال کردن کاربر {user_id}: {e}")
    
    def stop_processing(self):
        """توقف پردازش"""
        self.running = False
        logger.info("🛑 موتور اعلان‌رسانی متوقف شد")
    
    def get_statistics(self) -> Dict:
        """دریافت آمار موتور اعلان‌ها"""
        queue_stats = self.queue.get_stats()
        
        return {
            'queue': queue_stats,
            'rate_limits': self.rate_limits,
            'recent_messages': len(self.sent_messages),
            'templates_loaded': len(self.templates),
            'active_filters': len(self.filters),
            'notification_history_size': sum(len(h) for h in self.notification_history.values())
        }

# Factory function
def create_notification_engine(client: Client, db_manager) -> SmartNotificationEngine:
    """ایجاد نمونه موتور اعلان‌رسانی"""
    return SmartNotificationEngine(client, db_manager)
