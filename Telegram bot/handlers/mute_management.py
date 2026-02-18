from telebot import TeleBot
from telebot.types import Message, ChatPermissions
from database import db
from utils.decorators import owner_only
from utils.helpers import get_user_id_by_username, get_selected_group
from services.vip_service import VIPService
from services.language_service import language_service
from config import VIOLATION_LEVELS
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    vip_service = VIPService(bot)
    
    def handle_blacklist_command(bot: TeleBot, message: Message):
        """Обрабатывает команды из черного списка"""
        user_id = message.from_user.id
        group_id = message.chat.id
        username = message.from_user.username or message.from_user.first_name
        
        # Проверяем иммунитет у VIP PLUS
        if vip_service.has_immunity_to_mute(user_id, group_id):
            return False
        
        # Удаляем сообщение с командой
        try:
            bot.delete_message(group_id, message.message_id)
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем текущий статус нарушений
            cursor.execute('''
                SELECT * FROM muted_users 
                WHERE user_id = ? AND group_id = ?
            ''', (user_id, group_id))
            
            muted = cursor.fetchone()
            
            if muted:
                violations = muted['violations'] + 1
                if violations > 4:
                    violations = 4
            else:
                violations = 1
            
            level = VIOLATION_LEVELS.get(violations, VIOLATION_LEVELS[4])
            
            # Отправляем предупреждение
            if violations == 1:
                warning = language_service.get_text('blacklist_warning', group_id, username=username)
                bot.send_message(group_id, warning, reply_to_message_id=message.message_id)
                
            elif violations >= 2:
                mute_time = level['mute_time']
                mute_end = datetime.now() + timedelta(seconds=mute_time)
                
                # Мутим пользователя
                try:
                    bot.restrict_chat_member(
                        group_id,
                        user_id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=int(time.time()) + mute_time
                    )
                    
                    hours = mute_time // 3600
                    minutes = (mute_time % 3600) // 60
                    
                    if hours > 0:
                        time_text = f"{hours}ч {minutes}м"
                    else:
                        time_text = f"{minutes}м"
                    
                    warning = language_service.get_text('mute_message', group_id, username=username, time=time_text)
                    bot.send_message(group_id, warning)
                    
                    # Сохраняем в БД
                    if muted:
                        cursor.execute('''
                            UPDATE muted_users SET 
                                violations = ?,
                                mute_end = ?
                            WHERE user_id = ? AND group_id = ?
                        ''', (violations, mute_end, user_id, group_id))
                    else:
                        cursor.execute('''
                            INSERT INTO muted_users (user_id, username, group_id, mute_time, mute_end, violations)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (user_id, username, group_id, datetime.now(), mute_end, violations))
                        
                except Exception as e:
                    logger.error(f"Ошибка мута: {e}")
            
            return True
    
    @bot.message_handler(commands=['mute_status'])
    @owner_only
    def mute_status(message: Message):
        """Статус всех мутов"""
        group_id = get_selected_group(message.from_user.id)
        
        if not group_id:
            bot.reply_to(
                message,
                language_service.get_text('no_group_selected', message.chat.id)
            )
            return
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM muted_users 
                WHERE group_id = ? AND mute_end > ?
                ORDER BY mute_end
            ''', (group_id, datetime.now()))
            
            mutes = cursor.fetchall()
        
        if not mutes:
            bot.reply_to(
                message,
                language_service.get_text('no_active_mutes', message.chat.id)
            )
            return
        
        text = language_service.get_text('mutes_header', message.chat.id)
        for mute in mutes:
            # Преобразуем строку в datetime если нужно
            mute_end = mute['mute_end']
            if isinstance(mute_end, str):
                mute_end = datetime.fromisoformat(mute_end)
            
            time_left = mute_end - datetime.now()
            hours = int(time_left.total_seconds() / 3600)
            minutes = int((time_left.total_seconds() % 3600) / 60)
            
            text += language_service.get_text('mute_info', message.chat.id,
                                             username=mute['username'],
                                             violations=mute['violations'],
                                             hours=hours,
                                             minutes=minutes,
                                             end=mute_end.strftime('%d.%m.%Y %H:%M'))
        
        bot.send_message(message.chat.id, text)

    @bot.message_handler(commands=['off_mute'])
    @owner_only
    def off_mute(message: Message):
        """Снять мут с пользователя"""
        try:
            username = message.text.split()[1]
            group_id = get_selected_group(message.from_user.id)
            
            if not group_id:
                bot.reply_to(
                    message,
                    language_service.get_text('no_group_selected', message.chat.id)
                )
                return
            
            user_id = get_user_id_by_username(bot, username)
            if not user_id:
                bot.reply_to(
                    message,
                    language_service.get_text('user_not_found', message.chat.id)
                )
                return
            
            # Размучиваем
            try:
                bot.restrict_chat_member(
                    group_id,
                    user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
            except Exception as e:
                logger.error(f"Ошибка размута: {e}")
            
            # Удаляем из БД
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM muted_users 
                    WHERE user_id = ? AND group_id = ?
                ''', (user_id, group_id))
                
                if cursor.rowcount > 0:
                    bot.reply_to(
                        message,
                        language_service.get_text('mute_removed', message.chat.id, username=username)
                    )
                else:
                    bot.reply_to(
                        message,
                        language_service.get_text('mute_not_found', message.chat.id, username=username)
                    )
                    
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('off_mute_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /off_mute: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_all_mute'])
    @owner_only
    def del_all_mute(message: Message):
        """Удалить все муты в группе"""
        group_id = get_selected_group(message.from_user.id)
        
        if not group_id:
            bot.reply_to(
                message,
                language_service.get_text('no_group_selected', message.chat.id)
            )
            return
        
        # Получаем всех замученных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id FROM muted_users WHERE group_id = ?
            ''', (group_id,))
            users = cursor.fetchall()
            
            # Размучиваем каждого
            for user in users:
                try:
                    bot.restrict_chat_member(
                        group_id,
                        user['user_id'],
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_polls=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )
                except Exception as e:
                    logger.error(f"Ошибка размута пользователя {user['user_id']}: {e}")
            
            # Удаляем из БД
            cursor.execute('DELETE FROM muted_users WHERE group_id = ?', (group_id,))
            count = cursor.rowcount
        
        bot.reply_to(
            message,
            language_service.get_text('mutes_cleared', message.chat.id, count=count)
        )