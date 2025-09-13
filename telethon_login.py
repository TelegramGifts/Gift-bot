#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔑 ورود حساب کاربری با Telethon برای رصد گیفت‌ها

این اسکریپت یک سشن کاربری Telethon می‌سازد تا ربات بتواند
از متد payments.GetStarGifts استفاده کند.

مراحل:
1) pip install telethon
2) اجرا: python telethon_login.py
3) شماره تلفن، کد تایید و (در صورت نیاز) رمز دو مرحله‌ای را وارد کنید
4) فایل سشن gift_alert_user.session ساخته می‌شود
"""

import asyncio
from telethon import TelegramClient

API_ID = 0  # API ID خود را وارد کنید یا از bot_config.json بخوانید
API_HASH = ""  # API HASH خود را وارد کنید
SESSION_NAME = "gift_alert_user"

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"✅ ورود موفق: {me.id} - @{getattr(me, 'username', None)}")
    await client.disconnect()

if __name__ == "__main__":
    print("📱 در حال شروع فرآیند ورود کاربر...")
    print("اگر در فایل bot_config.json مقدار API ID / HASH دارید، آن‌ها را در این فایل وارد کنید.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 عملیات لغو شد")
    except Exception as e:
        print(f"❌ خطا: {e}")


