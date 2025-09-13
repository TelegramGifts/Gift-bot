#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ تنظیمات ربات گیفت تلگرام
Telegram Gift Bot Configuration

این فایل تمام تنظیمات و کانفیگ‌های ربات را مدیریت می‌کند
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class TelegramConfig:
    """تنظیمات تلگرام"""
    api_id: int
    api_hash: str
    bot_token: str
    session_name: str = "gift_alert_bot"
    device_model: str = "PC 64bit"
    system_version: str = "4.14.186"
    app_version: str = "1.28.5"
    use_ipv6: bool = False
    hide_log: bool = True

@dataclass
class DatabaseConfig:
    """تنظیمات پایگاه داده"""
    db_path: str = "gift_bot.db"
    backup_interval_hours: int = 6
    auto_backup: bool = True
    backup_directory: str = "backups"
    max_backups: int = 10

@dataclass
class MonitoringConfig:
    """تنظیمات رصد گیفت‌ها"""
    check_interval_seconds: int = 3
    max_retries: int = 5
    timeout_seconds: int = 30
    enable_price_tracking: bool = True
    enable_availability_tracking: bool = True
    
@dataclass
class NotificationConfig:
    """تنظیمات اعلان‌رسانی"""
    max_notifications_per_minute: int = 20
    max_notifications_per_hour: int = 1000
    enable_smart_filtering: bool = True
    enable_anti_spam: bool = True
    default_language: str = "fa"
    retry_failed_notifications: bool = True
    max_retry_attempts: int = 3

@dataclass
class AdminConfig:
    """تنظیمات مدیریت"""
    admin_user_ids: List[int]
    enable_admin_panel: bool = True
    enable_statistics: bool = True
    enable_user_management: bool = True
    enable_broadcast: bool = True
    log_level: str = "INFO"
    log_file: str = "gift_bot.log"

@dataclass
class SecurityConfig:
    """تنظیمات امنیتی"""
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60
    block_suspicious_users: bool = True
    enable_flood_protection: bool = True
    allowed_update_types: List[str] = None

@dataclass
class PerformanceConfig:
    """تنظیمات عملکرد"""
    max_concurrent_requests: int = 10
    connection_pool_size: int = 5
    cache_size_mb: int = 50
    enable_compression: bool = True
    optimize_memory: bool = True

class BotConfig:
    """کلاس اصلی تنظیمات ربات"""
    
    def __init__(self, config_file: str = "bot_config.json"):
        self.config_file = config_file
        self.telegram: Optional[TelegramConfig] = None
        self.database: Optional[DatabaseConfig] = None
        self.monitoring: Optional[MonitoringConfig] = None
        self.notification: Optional[NotificationConfig] = None
        self.admin: Optional[AdminConfig] = None
        self.security: Optional[SecurityConfig] = None
        self.performance: Optional[PerformanceConfig] = None
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """بارگذاری تنظیمات از فایل"""
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self._load_from_dict(config_data)
                print(f"✅ تنظیمات از {self.config_file} بارگذاری شد")
                
            except Exception as e:
                print(f"❌ خطا در بارگذاری تنظیمات: {e}")
                self._load_defaults()
        else:
            print(f"📁 فایل تنظیمات یافت نشد، تنظیمات پیش‌فرض ایجاد می‌شود...")
            self._load_defaults()
            self.save_config()
    
    def _load_from_dict(self, config_data: Dict):
        """بارگذاری تنظیمات از دیکشنری"""
        self.telegram = TelegramConfig(
            **config_data.get('telegram', {})
        )
        self.database = DatabaseConfig(
            **config_data.get('database', {})
        )
        self.monitoring = MonitoringConfig(
            **config_data.get('monitoring', {})
        )
        self.notification = NotificationConfig(
            **config_data.get('notification', {})
        )
        self.admin = AdminConfig(
            **config_data.get('admin', {})
        )
        self.security = SecurityConfig(
            **config_data.get('security', {})
        )
        self.performance = PerformanceConfig(
            **config_data.get('performance', {})
        )
    
    def _load_defaults(self):
        """بارگذاری تنظیمات پیش‌فرض"""
        self.telegram = TelegramConfig(
            api_id=int(os.getenv('API_ID', '0')),
            api_hash=os.getenv('API_HASH', ''),
            bot_token=os.getenv('BOT_TOKEN', '')
        )
        
        self.database = DatabaseConfig()
        self.monitoring = MonitoringConfig()
        self.notification = NotificationConfig()
        
        self.admin = AdminConfig(
            admin_user_ids=[int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
        )
        
        self.security = SecurityConfig(
            allowed_update_types=["message", "callback_query", "inline_query"]
        )
        
        self.performance = PerformanceConfig()
    
    def save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            config_data = {
                'telegram': asdict(self.telegram),
                'database': asdict(self.database),
                'monitoring': asdict(self.monitoring),
                'notification': asdict(self.notification),
                'admin': asdict(self.admin),
                'security': asdict(self.security),
                'performance': asdict(self.performance)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ تنظیمات در {self.config_file} ذخیره شد")
            
        except Exception as e:
            print(f"❌ خطا در ذخیره تنظیمات: {e}")
    
    def validate_config(self) -> List[str]:
        """اعتبارسنجی تنظیمات"""
        errors = []
        
        # Validate Telegram config
        if not self.telegram.api_id or self.telegram.api_id == 0:
            errors.append("API ID تنظیم نشده است")
        
        if not self.telegram.api_hash:
            errors.append("API Hash تنظیم نشده است")
        
        if not self.telegram.bot_token:
            errors.append("Bot Token تنظیم نشده است")
        
        # Validate admin config
        if not self.admin.admin_user_ids:
            errors.append("هیچ ادمینی تعریف نشده است")
        
        # Validate monitoring config
        if self.monitoring.check_interval_seconds < 1:
            errors.append("فاصله رصد باید حداقل 1 ثانیه باشد")
        
        # Validate database config
        if not self.database.db_path:
            errors.append("مسیر دیتابیس تعریف نشده است")
        
        return errors
    
    def get_logging_config(self) -> Dict:
        """دریافت تنظیمات لاگ"""
        return {
            'level': getattr(logging, self.admin.log_level.upper()),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'handlers': [
                {
                    'type': 'file',
                    'filename': self.admin.log_file,
                    'encoding': 'utf-8',
                    'maxBytes': 10*1024*1024,  # 10MB
                    'backupCount': 5
                },
                {
                    'type': 'console',
                    'level': 'INFO'
                }
            ]
        }
    
    def create_directory_structure(self):
        """ایجاد ساختار دایرکتوری‌ها"""
        directories = [
            self.database.backup_directory,
            "logs",
            "temp",
            "data"
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        
        print("📁 ساختار دایرکتوری‌ها ایجاد شد")
    
    def update_setting(self, section: str, key: str, value: Any):
        """بروزرسانی یک تنظیم"""
        try:
            section_obj = getattr(self, section)
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
                self.save_config()
                return True
            else:
                print(f"❌ کلید {key} در بخش {section} یافت نشد")
                return False
        except AttributeError:
            print(f"❌ بخش {section} یافت نشد")
            return False
    
    def get_environment_config(self) -> Dict[str, str]:
        """دریافت تنظیمات محیط"""
        return {
            'API_ID': str(self.telegram.api_id),
            'API_HASH': self.telegram.api_hash,
            'BOT_TOKEN': self.telegram.bot_token,
            'ADMIN_IDS': ','.join(map(str, self.admin.admin_user_ids)),
            'DB_PATH': self.database.db_path,
            'LOG_LEVEL': self.admin.log_level
        }
    
    def export_config(self, export_file: str = "config_export.json"):
        """صادرات تنظیمات (بدون اطلاعات حساس)"""
        try:
            safe_config = {
                'database': asdict(self.database),
                'monitoring': asdict(self.monitoring),
                'notification': asdict(self.notification),
                'security': asdict(self.security),
                'performance': asdict(self.performance),
                'admin': {
                    'enable_admin_panel': self.admin.enable_admin_panel,
                    'enable_statistics': self.admin.enable_statistics,
                    'log_level': self.admin.log_level
                }
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(safe_config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ تنظیمات در {export_file} صادر شد")
            
        except Exception as e:
            print(f"❌ خطا در صادرات تنظیمات: {e}")

# Global configuration instance
config = BotConfig()

# Convenience functions
def get_telegram_config() -> TelegramConfig:
    """دریافت تنظیمات تلگرام"""
    return config.telegram

def get_database_config() -> DatabaseConfig:
    """دریافت تنظیمات دیتابیس"""
    return config.database

def get_monitoring_config() -> MonitoringConfig:
    """دریافت تنظیمات رصد"""
    return config.monitoring

def get_notification_config() -> NotificationConfig:
    """دریافت تنظیمات اعلان‌رسانی"""
    return config.notification

def get_admin_config() -> AdminConfig:
    """دریافت تنظیمات ادمین"""
    return config.admin

def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    return user_id in config.admin.admin_user_ids

def setup_logging():
    """تنظیم سیستم لاگ"""
    log_config = config.get_logging_config()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_config['level'],
        format=log_config['format'],
        handlers=[
            logging.FileHandler(
                f"logs/{config.admin.log_file}",
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

if __name__ == "__main__":
    print("🔧 تست تنظیمات ربات گیفت...")
    
    # Validate configuration
    errors = config.validate_config()
    if errors:
        print("❌ خطاهای تنظیمات:")
        for error in errors:
            print(f"  • {error}")
    else:
        print("✅ تمام تنظیمات معتبر هستند!")
    
    # Create directory structure
    config.create_directory_structure()
    
    # Export safe config
    config.export_config()
    
    print("\n📋 خلاصه تنظیمات:")
    print(f"  • Telegram API ID: {'✅ تنظیم شده' if config.telegram.api_id else '❌ تنظیم نشده'}")
    print(f"  • Bot Token: {'✅ تنظیم شده' if config.telegram.bot_token else '❌ تنظیم نشده'}")
    print(f"  • تعداد ادمین‌ها: {len(config.admin.admin_user_ids)}")
    print(f"  • فاصله رصد: {config.monitoring.check_interval_seconds} ثانیه")
    print(f"  • حداکثر اعلان در دقیقه: {config.notification.max_notifications_per_minute}")
