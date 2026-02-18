from telebot import TeleBot
from telebot.types import Message
from database import db
from utils.decorators import owner_only
from utils.helpers import get_user_id_by_username, get_group_id_by_username
from utils.time_parser import parse_duration_to_end
from services.vip_service import VIPService
from services.language_service import language_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    vip_service = VIPService(bot)
    
    @bot.message_handler(commands=['add_VIP'])
    @owner_only
    def add_vip_global(message: Message):
        """Добавить глобальный VIP"""
        try:
            username = message.text.split()[1]
            user_id = get_user_id_by_username(bot, username)
            
            if not user_id:
                bot.reply_to(
                    message,
                    language_service.get_text('user_not_found', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vip_users (user_id, username, vip_type, scope, start_date)
                    VALUES (?, ?, 'VIP', 'global', ?)
                ''', (user_id, username, datetime.now()))
            
            bot.reply_to(
                message,
                language_service.get_text('vip_added_global', message.chat.id, username=username)
            )
            
            try:
                status_text = vip_service.show_vip_status(user_id, 0)
                user_text = language_service.get_text('vip_granted_global', user_id, features=status_text)
                bot.send_message(user_id, user_text)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
                
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('add_vip_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /add_VIP: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['ad_VIP_PLUS'])
    @owner_only
    def add_vip_plus_global(message: Message):
        """Добавить глобальный VIP PLUS"""
        try:
            username = message.text.split()[1]
            user_id = get_user_id_by_username(bot, username)
            
            if not user_id:
                bot.reply_to(
                    message,
                    language_service.get_text('user_not_found', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vip_users (user_id, username, vip_type, scope, start_date)
                    VALUES (?, ?, 'VIP_PLUS', 'global', ?)
                ''', (user_id, username, datetime.now()))
            
            bot.reply_to(
                message,
                language_service.get_text('vip_plus_added_global', message.chat.id, username=username)
            )
            
            try:
                status_text = vip_service.show_vip_status(user_id, 0)
                user_text = language_service.get_text('vip_plus_granted_global', user_id, features=status_text)
                bot.send_message(user_id, user_text)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
                
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('add_vip_plus_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /ad_VIP_PLUS: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['add_VIP_local'])
    @owner_only
    def add_vip_local(message: Message):
        """Добавить локальный VIP"""
        try:
            args = message.text.split()
            if len(args) < 3:
                bot.reply_to(
                    message,
                    language_service.get_text('add_vip_local_usage', message.chat.id)
                )
                return
            
            group_username = args[1]
            username = args[2]
            
            group_id = get_group_id_by_username(bot, group_username)
            user_id = get_user_id_by_username(bot, username)
            
            if not group_id or not user_id:
                bot.reply_to(
                    message,
                    language_service.get_text('group_or_user_not_found', message.chat.id)
                )
                return
            
            # Проверяем лимиты
            if not vip_service.check_vip_limits(user_id, group_id, 'VIP'):
                bot.reply_to(
                    message,
                    language_service.get_text('vip_limit_reached', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vip_users (user_id, username, vip_type, scope, group_id, start_date)
                    VALUES (?, ?, 'VIP', 'local', ?, ?)
                ''', (user_id, username, group_id, datetime.now()))
            
            bot.reply_to(
                message,
                language_service.get_text('vip_added_local', message.chat.id, username=username, group=group_username)
            )
            
            try:
                status_text = vip_service.show_vip_status(user_id, group_id)
                user_text = language_service.get_text('vip_granted_local', user_id, group=group_username, features=status_text)
                bot.send_message(user_id, user_text)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка в /add_VIP_local: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['add_VIP_global'])
    @owner_only
    def add_vip_global_cmd(message: Message):
        """Добавить глобальный VIP (алиас для add_VIP)"""
        add_vip_global(message)

    @bot.message_handler(commands=['add_VIP_time'])
    @owner_only
    def add_vip_time(message: Message):
        """Добавить VIP на время"""
        try:
            args = message.text.split()
            if len(args) < 3:
                bot.reply_to(
                    message,
                    language_service.get_text('add_vip_time_usage', message.chat.id)
                )
                return
            
            username = args[1]
            duration = args[2]
            
            user_id = get_user_id_by_username(bot, username)
            if not user_id:
                bot.reply_to(
                    message,
                    language_service.get_text('user_not_found', message.chat.id)
                )
                return
            
            end_date = parse_duration_to_end(duration)
            if not end_date:
                bot.reply_to(
                    message,
                    language_service.get_text('invalid_time_format', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vip_users (user_id, username, vip_type, scope, start_date, end_date)
                    VALUES (?, ?, 'VIP', 'global', ?, ?)
                ''', (user_id, username, datetime.now(), end_date))
            
            bot.reply_to(
                message,
                language_service.get_text('vip_time_set', message.chat.id, username=username, date=end_date.strftime('%d.%m.%Y %H:%M'))
            )
            
        except Exception as e:
            logger.error(f"Ошибка в /add_VIP_time: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_VIP'])
    @owner_only
    def del_vip(message: Message):
        """Удалить VIP"""
        try:
            username = message.text.split()[1]
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM vip_users 
                    WHERE username = ? AND vip_type = 'VIP'
                ''', (username,))
                
                if cursor.rowcount > 0:
                    bot.reply_to(
                        message,
                        language_service.get_text('vip_removed', message.chat.id, username=username)
                    )
                else:
                    bot.reply_to(
                        message,
                        language_service.get_text('vip_not_found', message.chat.id, username=username)
                    )
                    
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('del_vip_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /del_VIP: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_VIPPLUS'])
    @owner_only
    def del_vip_plus(message: Message):
        """Удалить VIP PLUS"""
        try:
            username = message.text.split()[1]
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM vip_users 
                    WHERE username = ? AND vip_type = 'VIP_PLUS'
                ''', (username,))
                
                if cursor.rowcount > 0:
                    bot.reply_to(
                        message,
                        language_service.get_text('vip_plus_removed', message.chat.id, username=username)
                    )
                else:
                    bot.reply_to(
                        message,
                        language_service.get_text('vip_plus_not_found', message.chat.id, username=username)
                    )
                    
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('del_vip_plus_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /del_VIPPLUS: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_all_VIP'])
    @owner_only
    def del_all_vip(message: Message):
        """Удалить всех VIP"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vip_users WHERE vip_type = 'VIP'")
            count = cursor.rowcount
            
            bot.reply_to(
                message,
                language_service.get_text('vip_all_removed', message.chat.id, count=count)
            )

    @bot.message_handler(commands=['del_all_VIPPLUS'])
    @owner_only
    def del_all_vip_plus(message: Message):
        """Удалить всех VIP PLUS"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vip_users WHERE vip_type = 'VIP_PLUS'")
            count = cursor.rowcount
            
            bot.reply_to(
                message,
                language_service.get_text('vip_plus_all_removed', message.chat.id, count=count)
            )