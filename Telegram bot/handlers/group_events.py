from telebot import TeleBot
from telebot.types import Message, ChatMemberUpdated
from database import db
from services.subscription_checker import SubscriptionChecker
from services.vip_service import VIPService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    checker = SubscriptionChecker(bot)
    vip_service = VIPService(bot)
    
    @bot.chat_member_handler()
    def on_chat_member_update(update: ChatMemberUpdated):
        """Обработчик изменения статуса участников чата"""
        try:
            # Проверяем, что изменение касается самого бота
            bot_user = bot.get_me()
            if update.new_chat_member.user.id != bot_user.id:
                return
            
            old_status = update.old_chat_member.status
            new_status = update.new_chat_member.status
            chat = update.chat
            
            logger.info(f"🤖 Статус бота в чате {chat.id}: {old_status} -> {new_status}")
            
            # Бот был добавлен в группу
            if old_status in ['left', 'kicked'] and new_status in ['member', 'administrator']:
                chat_id = chat.id
                chat_title = chat.title or "Без названия"
                chat_username = chat.username
                
                # Сохраняем группу в БД
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                        VALUES (?, ?, ?, ?, 30)
                    ''', (chat_id, chat_title, chat_username, datetime.now()))
                
                # Уведомляем владельца
                from config import OWNER_ID
                try:
                    bot.send_message(
                        OWNER_ID,
                        f"✅ **Бот добавлен в новую группу!**\n\n"
                        f"📌 Название: {chat_title}\n"
                        f"🆔 ID: `{chat_id}`\n"
                        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Уведомление отправлено владельцу")
                except Exception as e:
                    logger.error(f"❌ Не удалось уведомить владельца: {e}")
                
                logger.info(f"✅ Бот добавлен в группу: {chat_title} ({chat_id})")
            
            # Бот был удален из группы
            elif old_status in ['member', 'administrator'] and new_status in ['left', 'kicked']:
                logger.info(f"❌ Бот удален из группы {chat.id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в chat_member_handler: {e}")
    
    @bot.message_handler(content_types=['new_chat_members'])
    def on_new_chat_members(message: Message):
        """Обработчик новых участников (запасной вариант)"""
        try:
            bot_user = bot.get_me()
            
            for new_member in message.new_chat_members:
                if new_member.id == bot_user.id:
                    chat = message.chat
                    chat_id = chat.id
                    chat_title = chat.title or "Без названия"
                    chat_username = chat.username
                    
                    logger.info(f"🔍 Бот обнаружен в группе через new_chat_members: {chat_title}")
                    
                    # Сохраняем группу в БД
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                            VALUES (?, ?, ?, ?, 30)
                        ''', (chat_id, chat_title, chat_username, datetime.now()))
                    
                    # Уведомляем владельца
                    from config import OWNER_ID
                    try:
                        bot.send_message(
                            OWNER_ID,
                            f"✅ **Бот добавлен в новую группу!**\n\n"
                            f"📌 Название: {chat_title}\n"
                            f"🆔 ID: `{chat_id}`\n"
                            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"❌ Не удалось уведомить владельца: {e}")
                    
                    break
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в new_chat_members: {e}")
    
    @bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker', 'animation'])
    def handle_group_message(message: Message):
        """Обработчик всех сообщений в группах"""
        if message.chat.type not in ['group', 'supergroup']:
            return
        
        try:
            # Проверяем, есть ли группа в БД (если нет - добавляем)
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM groups WHERE group_id = ?', (message.chat.id,))
                group = cursor.fetchone()
                
                if not group:
                    # Автоматически добавляем группу в БД
                    cursor.execute('''
                        INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                        VALUES (?, ?, ?, ?, 30)
                    ''', (message.chat.id, message.chat.title, message.chat.username, datetime.now()))
                    logger.info(f"✅ Группа {message.chat.title} автоматически добавлена в БД")
            
            # Проверка на команды из черного списка
            if message.text and message.text.startswith('/'):
                cmd = message.text.split()[0].lower()
                
                # Список команд, доступных всем
                public_commands = ['/start', '/vip_info', '/help', '/language', '/lang']
                
                from config import OWNER_ID
                if cmd not in public_commands and message.from_user.id != OWNER_ID:
                    from handlers.mute_management import handle_blacklist_command
                    handle_blacklist_command(bot, message)
                    return
            
            # Проверка подписки
            checker.handle_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике сообщений: {e}")