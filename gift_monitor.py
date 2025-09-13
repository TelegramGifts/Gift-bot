#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 ماژول رصد گیفت‌های ستاره‌ای تلگرام
Telegram Star Gifts Monitoring Module

این ماژول وظیفه رصد لحظه‌ای گیفت‌های جدید تلگرام را بر عهده دارد
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib

from pyrogram import Client
from pyrogram.raw import functions as raw_functions, types as raw_types

# Telethon fallback
try:
    from telethon import TelegramClient
    from telethon.tl.functions.payments import GetStarGifts as TelethonGetStarGifts
    TELETHON_AVAILABLE = True
except Exception:
    TELETHON_AVAILABLE = False
from pyrogram.errors import FloodWait, RPCError

logger = logging.getLogger(__name__)

class TelegramGiftMonitor:
    """کلاس رصد گیفت‌های تلگرام"""
    
    def __init__(self, client: Client, telethon_client: Optional[object] = None):
        self.client = client
        self.telethon_client = telethon_client
        self.last_hash = 0
        self.known_gifts: Dict[int, Dict] = {}
        self.monitoring_active = False
        self.check_interval = 3  # seconds
        # File-based fallback feed
        from pathlib import Path
        self.file_feed_path = Path("data") / "gifts_feed.jsonl"
        self._file_offset = 0
        try:
            self.file_feed_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_feed_path.touch(exist_ok=True)
        except Exception:
            pass
        
    async def get_star_gifts(self, hash_value: int = 0) -> Optional[Dict]:
        """دریافت لیست گیفت‌های ستاره‌ای از تلگرام"""
        try:
            # استفاده از Telegram API برای دریافت گیفت‌ها
            # برخی نسخه‌های Pyrogram ممکن است این متد را نداشته باشند
            get_star_gifts_cls = getattr(getattr(raw_functions, 'payments', object), 'GetStarGifts', None)
            if get_star_gifts_cls is not None:
                result = await self.client.invoke(
                    get_star_gifts_cls(hash=hash_value)
                )
            else:
                # Fallback to Telethon if available
                if TELETHON_AVAILABLE and self.telethon_client is not None:
                    tl_result = await self.telethon_client(TelethonGetStarGifts(hash=hash_value))
                    # Normalize into a simple object-like dict
                    gifts = []
                    for g in getattr(tl_result, 'gifts', []):
                        gifts.append(self._parse_gift(g))
                    return {
                        'hash': getattr(tl_result, 'hash', 0),
                        'gifts': gifts
                    }
                else:
                    # Last-resort: file feed fallback
                    return await self._read_file_feed()
            
            if hasattr(result, 'gifts') and result.gifts:
                return {
                    'hash': result.hash if hasattr(result, 'hash') else 0,
                    'gifts': [self._parse_gift(gift) for gift in result.gifts]
                }
            
            return None
            
        except FloodWait as e:
            logger.warning(f"درخواست محدود شد، {e.value} ثانیه صبر...")
            await asyncio.sleep(e.value)
            return None
        except RPCError as e:
            logger.error(f"خطای RPC: {e}")
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت گیفت‌ها: {e}")
            return None
    
    def _parse_gift(self, gift_data: Any) -> Dict:
        """تجزیه داده‌های گیفت"""
        return {
            'id': getattr(gift_data, 'id', 0),
            'title': getattr(gift_data, 'title', 'نامشخص'),
            'stars': getattr(gift_data, 'stars', 0),
            'limited': getattr(gift_data, 'limited', False),
            'sold_out': getattr(gift_data, 'sold_out', False),
            'require_premium': getattr(gift_data, 'require_premium', False),
            'can_upgrade': getattr(gift_data, 'can_upgrade', False),
            'first_sale_date': getattr(gift_data, 'first_sale_date', None),
            'last_sale_date': getattr(gift_data, 'last_sale_date', None),
            'availability_remains': getattr(gift_data, 'availability_remains', None),
            'availability_total': getattr(gift_data, 'availability_total', None),
            'discovered_at': datetime.now()
        }
    
    async def start_monitoring(self, callback_func=None):
        """شروع رصد مداوم گیفت‌ها"""
        logger.info("🔍 شروع رصد گیفت‌های ستاره‌ای...")
        self.monitoring_active = True
        
        # دریافت اولیه گیفت‌ها
        initial_gifts = await self.get_star_gifts()
        if initial_gifts:
            self.last_hash = initial_gifts['hash']
            for gift in initial_gifts['gifts']:
                self.known_gifts[gift['id']] = gift
            logger.info(f"📝 {len(initial_gifts['gifts'])} گیفت موجود یافت شد")
        
        # شروع حلقه رصد
        while self.monitoring_active:
            try:
                await self._check_for_new_gifts(callback_func)
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"خطا در رصد: {e}")
                await asyncio.sleep(10)
    
    async def _check_for_new_gifts(self, callback_func=None):
        """بررسی گیفت‌های جدید"""
        gifts_data = await self.get_star_gifts(self.last_hash)
        
        if not gifts_data:
            return
        
        # اگر هش جدید باشد، گیفت‌های جدید اضافه شده
        if gifts_data['hash'] != self.last_hash:
            self.last_hash = gifts_data['hash']
            
            new_gifts = []
            updated_gifts = []
            
            for gift in gifts_data['gifts']:
                gift_id = gift['id']
                
                if gift_id not in self.known_gifts:
                    # گیفت جدید
                    new_gifts.append(gift)
                    self.known_gifts[gift_id] = gift
                    logger.info(f"🆕 گیفت جدید: {gift['title']} ({gift['stars']} ستاره)")
                    
                elif self._gift_changed(self.known_gifts[gift_id], gift):
                    # گیفت موجود تغییر کرده
                    updated_gifts.append(gift)
                    self.known_gifts[gift_id] = gift
                    logger.info(f"🔄 گیفت تغییر کرد: {gift['title']}")
            
            # فراخوانی تابع callback برای گیفت‌های جدید و تغییر یافته
            if callback_func:
                for gift in new_gifts:
                    if self._should_notify(gift):
                        await callback_func(gift, 'new')
                
                for gift in updated_gifts:
                    if self._should_notify(gift):
                        await callback_func(gift, 'updated')

    async def _read_file_feed(self) -> Optional[Dict]:
        """خواندن ورودی از فایل JSONL به عنوان fallback

        فرمت هر خط:
        {"event":"new|updated","gift":{"id":123,"title":"...","stars":100,...}}
        """
        try:
            if not self.file_feed_path.exists():
                return None
            gifts = []
            with open(self.file_feed_path, 'r', encoding='utf-8') as f:
                f.seek(self._file_offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    gift_obj = obj.get('gift') or {}
                    # Normalize keys to our structure
                    gifts.append({
                        'id': gift_obj.get('id', 0),
                        'title': gift_obj.get('title', 'نامشخص'),
                        'stars': gift_obj.get('stars', 0),
                        'limited': gift_obj.get('limited', True),
                        'sold_out': gift_obj.get('sold_out', False),
                        'require_premium': gift_obj.get('require_premium', False),
                        'can_upgrade': gift_obj.get('can_upgrade', False),
                        'availability_remains': gift_obj.get('availability_remains'),
                        'availability_total': gift_obj.get('availability_total'),
                        'discovered_at': datetime.now()
                    })
                self._file_offset = f.tell()
            if not gifts:
                return None
            # Create a pseudo-hash from content length
            content_hash = int(datetime.now().timestamp())
            return {'hash': content_hash, 'gifts': gifts}
        except Exception as e:
            logger.error(f"خطا در خواندن فایل ورودی گیفت: {e}")
            return None
    
    def _gift_changed(self, old_gift: Dict, new_gift: Dict) -> bool:
        """بررسی تغییر در گیفت"""
        important_fields = ['sold_out', 'availability_remains', 'stars']
        return any(old_gift.get(field) != new_gift.get(field) for field in important_fields)
    
    def _should_notify(self, gift: Dict) -> bool:
        """تعیین اینکه آیا باید برای این گیفت اطلاع‌رسانی شود"""
        # فقط گیفت‌های محدود و موجود
        return (gift.get('limited', False) and 
                not gift.get('sold_out', True) and 
                gift.get('stars', 0) > 0)
    
    def stop_monitoring(self):
        """توقف رصد"""
        logger.info("⏹️ رصد گیفت‌ها متوقف شد")
        self.monitoring_active = False
    
    def get_gift_stats(self) -> Dict:
        """دریافت آمار گیفت‌ها"""
        total_gifts = len(self.known_gifts)
        limited_gifts = sum(1 for gift in self.known_gifts.values() if gift.get('limited', False))
        available_gifts = sum(1 for gift in self.known_gifts.values() if not gift.get('sold_out', True))
        
        return {
            'total_gifts': total_gifts,
            'limited_gifts': limited_gifts,
            'available_gifts': available_gifts,
            'last_hash': self.last_hash
        }

class GiftNotificationFormatter:
    """کلاس فرمت‌دهی اعلان‌های گیفت"""
    
    @staticmethod
    def format_new_gift(gift: Dict) -> str:
        """فرمت پیام گیفت جدید"""
        emoji_map = {
            True: "✅",
            False: "❌",
            None: "❓"
        }
        
        # محاسبه درصد موجودی
        availability_percent = ""
        if gift.get('availability_remains') and gift.get('availability_total'):
            percent = (gift['availability_remains'] / gift['availability_total']) * 100
            availability_percent = f"\n📊 **موجودی:** {gift['availability_remains']}/{gift['availability_total']} ({percent:.1f}%)"
        
        # زمان فروش
        sale_info = ""
        if gift.get('first_sale_date'):
            sale_info = f"\n🕐 **شروع فروش:** {datetime.fromtimestamp(gift['first_sale_date']).strftime('%Y/%m/%d %H:%M')}"
        
        message = f"""
🎁 **گیفت جدید کشف شد!**

📝 **نام:** {gift.get('title', 'نامشخص')}
🆔 **شناسه:** `{gift.get('id', 0)}`
🌟 **قیمت:** {gift.get('stars', 0):,} ستاره
⭐ **محدود:** {emoji_map.get(gift.get('limited'), '❓')}
🔴 **فروخته شده:** {emoji_map.get(gift.get('sold_out'), '❓')}
💎 **نیاز به پریمیوم:** {emoji_map.get(gift.get('require_premium'), '❓')}
♻️ **قابل ارتقاء:** {emoji_map.get(gift.get('can_upgrade'), '❓')}{availability_percent}{sale_info}

⏰ **زمان کشف:** {gift.get('discovered_at', datetime.now()).strftime('%Y/%m/%d %H:%M:%S')}

🚀 **سریع به تلگرام برو و خریدش کن!**
"""
        return message.strip()
    
    @staticmethod
    def format_updated_gift(gift: Dict) -> str:
        """فرمت پیام تغییر گیفت"""
        message = f"""
🔄 **گیفت تغییر کرد!**

📝 **نام:** {gift.get('title', 'نامشخص')}
🆔 **شناسه:** `{gift.get('id', 0)}`
🌟 **قیمت جدید:** {gift.get('stars', 0):,} ستاره

⏰ **زمان تغییر:** {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
"""
        return message.strip()

# تست ماژول
async def test_monitor():
    """تست ماژول رصد"""
    print("🧪 تست ماژول رصد گیفت...")
    
    # این تابع برای تست است - باید با اطلاعات واقعی جایگزین شود
    async def mock_callback(gift, event_type):
        print(f"📢 {event_type}: {gift['title']} - {gift['stars']} ستاره")
    
    # نمونه استفاده
    # client = Client(...)  # کلاینت واقعی
    # monitor = TelegramGiftMonitor(client)
    # await monitor.start_monitoring(mock_callback)

if __name__ == "__main__":
    asyncio.run(test_monitor())
