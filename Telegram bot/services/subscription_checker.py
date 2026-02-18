import threading
import time
import logging
from datetime import datetime
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import OWNER_ID
from services.language_service import language_service

logger = logging.getLogger(__name__)

class SubscriptionChecker:
    def __init__(self, bot: TeleBot):
        self.bot = bot

    def check_user_subscription(self, user_id: int, channels: list) -> bool:
        """
        Проверяет подписку пользователя на каналы
        Возвращает True, если пользователь подписан на все каналы
        """
        if not channels:
            return True
        
        for channel in channels:
            try:
                # Получаем информацию о канале
                chat = self.bot.get_chat(channel)
                
                # Проверяем статус пользователя в канале
                try:
                    member = self.bot.get_chat_member(chat.id, user_id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        logger.debug(f"Пользователь {user_id} не подписан на {channel}")
                        return False
                except Exception as e:
                    logger.error(f"Ошибка проверки подписки на {channel}: {e}")
                    # Если не можем проверить, считаем что не подписан
                    return False
                    
            except Exception as e:
                logger.error(f"Ошибка получения канала {channel}: {e}")
                return False
        
        return True

    def is_user_exempt(self, user_id: int, group_id: int) -> bool:
        """
        Проверяет, освобожден ли пользователь от проверки подписки
        """
        # Владелец бота всегда освобожден
        if user_id == OWNER_ID:
            return True
        
        # Проверяем, является ли пользователь администратором группы
        try:
            member = self.bot.get_chat_member(group_id, user_id)
            if member.status in ['administrator', 'creator']:
                logger.debug(f"Пользователь {user_id} - администратор группы")
                return True
        except Exception as e:
            logger.error(f"Ошибка проверки статуса администратора: {e}")
        
        # Проверяем VIP статус
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем глобальный VIP
            cursor.execute('''
                SELECT * FROM vip_users 
                WHERE user_id = ? AND scope = 'global'
                AND (end_date IS NULL OR end_date > ?)
            ''', (user_id, datetime.now()))
            
            if cursor.fetchone():
                logger.debug(f"Пользователь {user_id} имеет глобальный VIP")
                return True
            
            # Проверяем локальный VIP для этой группы
            cursor.execute('''
                SELECT * FROM vip_users 
                WHERE user_id = ? AND group_id = ? AND scope = 'local'
                AND (end_date IS NULL OR end_date > ?)
            ''', (user_id, group_id, datetime.now()))
            
            if cursor.fetchone():
                logger.debug(f"Пользователь {user_id} имеет локальный VIP в группе {group_id}")
                return True
        
        return False

    def create_subscription_keyboard(self, channels: list, chat_id: int) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с кнопками подписки на каналы
        """
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        for channel in channels:
            clean_channel = channel.lstrip('@')
            button_text = language_service.get_text('subscribe_button', chat_id, channel=channel)
            button = InlineKeyboardButton(
                text=button_text,
                url=f"https://t.me/{clean_channel}"
            )
            keyboard.add(button)
        
        # Кнопка с информацией о VIP
        vip_button_text = language_service.get_text('vip_button', chat_id)
        vip_button = InlineKeyboardButton(
            text=vip_button_text,
            callback_data="vip_info"
        )
        keyboard.add(vip_button)
        
        return keyboard

    def handle_message(self, message):
        """
        Обрабатывает сообщение и проверяет подписку
        """
        if message.chat.type not in ['group', 'supergroup']:
            return
        
        user_id = message.from_user.id
        group_id = message.chat.id
        
        # Проверяем, освобожден ли пользователь
        if self.is_user_exempt(user_id, group_id):
            return
        
        # Получаем активные каналы для этой группы
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT channel_username FROM channels 
                WHERE group_id = ? AND is_active = 1 
                AND (check_until IS NULL OR check_until > ?)
            ''', (group_id, datetime.now()))
            
            channels = [row[0] for row in cursor.fetchall()]
        
        if not channels:
            return
        
        # Проверяем подписку
        if not self.check_user_subscription(user_id, channels):
            try:
                # Удаляем сообщение нарушителя
                self.bot.delete_message(group_id, message.message_id)
                logger.info(f"Удалено сообщение от {user_id} в группе {group_id} (нет подписки)")
            except Exception as e:
                logger.error(f"Не удалось удалить сообщение: {e}")
            
            # Формируем текст предупреждения
            channels_text = ", ".join(channels)
            username = message.from_user.username or message.from_user.first_name
            
            warning_text = language_service.get_text(
                'subscription_warning',
                group_id,
                username=username,
                channels=channels_text
            )
            
            # Создаем клавиатуру
            keyboard = self.create_subscription_keyboard(channels, group_id)
            
            try:
                # Отправляем предупреждение
                sent_msg = self.bot.send_message(
                    group_id,
                    warning_text,
                    reply_markup=keyboard,
                    reply_to_message_id=message.message_id
                )
                
                # Проверяем автоудаление
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT auto_del_time FROM groups WHERE group_id = ?', (group_id,))
                    result = cursor.fetchone()
                    
                    if result and result[0] > 0:
                        auto_del_time = result[0]
                        
                        def delete_later():
                            time.sleep(auto_del_time)
                            try:
                                self.bot.delete_message(group_id, sent_msg.message_id)
                                logger.debug(f"Автоудаление сообщения через {auto_del_time}с")
                            except Exception as e:
                                logger.error(f"Ошибка автоудаления: {e}")
                        
                        threading.Thread(target=delete_later, daemon=True).start()
                        
            except Exception as e:
                logger.error(f"Не удалось отправить предупреждение: {e}")