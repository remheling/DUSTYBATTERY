import threading
import time
import logging
from datetime import datetime
from typing import Optional
from telebot import TeleBot
from database import db
from config import OWNER_ID

logger = logging.getLogger(__name__)

class Scheduler:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.bot: Optional[TeleBot] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def set_bot(self, bot: TeleBot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
        if not self.running:
            self.start()
    
    def start(self):
        """Запускает планировщик"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Планировщик задач запущен")
    
    def stop(self):
        """Останавливает планировщик"""
        self.running = False
        logger.info("Планировщик задач остановлен")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                self._check_expired_channels()
                self._check_expired_vip()
                self._check_expired_mutes()
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
            
            # Проверяем каждую минуту
            time.sleep(60)
    
    def _check_expired_channels(self):
        """Проверяет истекшие каналы"""
        if not self.bot:
            return
        
        now = datetime.now()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Находим каналы с истекшим сроком проверки
            cursor.execute('''
                SELECT c.*, g.group_title 
                FROM channels c
                JOIN groups g ON c.group_id = g.group_id
                WHERE c.check_until IS NOT NULL 
                AND c.check_until <= ? 
                AND c.is_active = 1
            ''', (now,))
            
            expired = cursor.fetchall()
            
            for channel in expired:
                try:
                    # Получаем данные по индексам
                    channel_id = channel[0]
                    channel_username = channel[2]
                    check_until = channel[5]
                    group_title = channel[7]
                    
                    # Отправляем уведомление владельцу
                    self.bot.send_message(
                        OWNER_ID,
                        f"⏰ **Канал снят с проверки**\n\n"
                        f"📢 Канал: {channel_username}\n"
                        f"👥 Группа: {group_title}\n"
                        f"📅 Время окончания: {check_until}",
                        parse_mode="Markdown"
                    )
                    
                    # Деактивируем канал
                    cursor.execute('''
                        UPDATE channels SET is_active = 0 
                        WHERE id = ?
                    ''', (channel_id,))
                    
                    logger.info(f"Канал {channel_username} снят с проверки (истек срок)")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке истекшего канала: {e}")
    
    def _check_expired_vip(self):
        """Проверяет истекшие VIP подписки"""
        now = datetime.now()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем истекшие VIP
            cursor.execute('''
                DELETE FROM vip_users 
                WHERE end_date IS NOT NULL AND end_date <= ?
            ''', (now,))
            
            if cursor.rowcount > 0:
                logger.info(f"Удалено {cursor.rowcount} истекших VIP подписок")
    
    def _check_expired_mutes(self):
        """Проверяет истекшие муты и размучивает пользователей"""
        if not self.bot:
            return
        
        now = datetime.now()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Находим истекшие муты
            cursor.execute('''
                SELECT * FROM muted_users 
                WHERE mute_end <= ?
            ''', (now,))
            
            expired = cursor.fetchall()
            
            for mute in expired:
                try:
                    # Размучиваем пользователя
                    from telebot.types import ChatPermissions
                    
                    permissions = ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                        can_change_info=True,
                        can_invite_users=True,
                        can_pin_messages=True
                    )
                    
                    self.bot.restrict_chat_member(
                        mute['group_id'],  # group_id
                        mute['user_id'],  # user_id
                        permissions=permissions
                    )
                    
                    logger.info(f"Пользователь {mute['user_id']} размучен (истек срок)")
                    
                except Exception as e:
                    logger.error(f"Не удалось размутить {mute['user_id']}: {e}")
                
                # Удаляем из таблицы мутов
                cursor.execute('''
                    DELETE FROM muted_users 
                    WHERE user_id = ? AND group_id = ?
                ''', (mute['user_id'], mute['group_id']))

# Глобальный экземпляр планировщика
scheduler = Scheduler()