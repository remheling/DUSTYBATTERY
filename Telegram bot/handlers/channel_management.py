from telebot import TeleBot
from telebot.types import Message
from database import db
from utils.decorators import owner_only
from utils.helpers import get_selected_group
from utils.time_parser import parse_time_string, parse_datetime_range
from config import MAX_CHANNELS_PER_GROUP, MIN_AUTO_DELETE_TIME, MAX_AUTO_DELETE_TIME
from datetime import datetime, timedelta
from services.language_service import language_service
import re
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.message_handler(commands=['add_one'])
    @owner_only
    def add_one_channel(message: Message):
        """Добавить один канал на проверку"""
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.reply_to(
                    message,
                    language_service.get_text('add_one_usage', message.chat.id)
                )
                return
            
            channel = args[1]
            if not channel.startswith('@'):
                channel = '@' + channel
            
            group_id = get_selected_group(message.from_user.id)
            
            if not group_id:
                bot.reply_to(
                    message,
                    language_service.get_text('no_group_selected', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем количество каналов
                cursor.execute(
                    "SELECT COUNT(*) FROM channels WHERE group_id = ? AND is_active = 1",
                    (group_id,)
                )
                count = cursor.fetchone()[0]
                
                if count >= MAX_CHANNELS_PER_GROUP:
                    bot.reply_to(
                        message,
                        language_service.get_text('max_channels', message.chat.id, 
                                                max=MAX_CHANNELS_PER_GROUP)
                    )
                    return
                
                # Добавляем канал
                cursor.execute('''
                    INSERT INTO channels (channel_username, group_id, added_date, is_active)
                    VALUES (?, ?, ?, 1)
                ''', (channel, group_id, datetime.now()))
                
                bot.reply_to(
                    message,
                    language_service.get_text('channel_added', message.chat.id, channel=channel)
                )
                logger.info(f"Канал {channel} добавлен в группу {group_id}")
                
        except Exception as e:
            logger.error(f"Ошибка в /add_one: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['add_channels'])
    @owner_only
    def add_channels(message: Message):
        """Добавить несколько каналов на проверку"""
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.reply_to(
                    message,
                    language_service.get_text('add_channels_usage', message.chat.id)
                )
                return
            
            channels = []
            for arg in args[1:4]:  # Максимум 3 канала
                if arg.startswith('@'):
                    channels.append(arg)
                else:
                    channels.append('@' + arg)
            
            group_id = get_selected_group(message.from_user.id)
            
            if not group_id:
                bot.reply_to(
                    message,
                    language_service.get_text('no_group_selected', message.chat.id)
                )
                return
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем сколько можно добавить
                cursor.execute(
                    "SELECT COUNT(*) FROM channels WHERE group_id = ? AND is_active = 1",
                    (group_id,)
                )
                current = cursor.fetchone()[0]
                
                available = MAX_CHANNELS_PER_GROUP - current
                if len(channels) > available:
                    bot.reply_to(
                        message,
                        language_service.get_text('can_add_only', message.chat.id, 
                                                available=available)
                    )
                    return
                
                # Добавляем каналы
                added = []
                for channel in channels:
                    cursor.execute('''
                        INSERT INTO channels (channel_username, group_id, added_date, is_active)
                        VALUES (?, ?, ?, 1)
                    ''', (channel, group_id, datetime.now()))
                    added.append(channel)
                
                bot.reply_to(
                    message,
                    language_service.get_text('channels_added', message.chat.id, 
                                            channels=', '.join(added))
                )
                logger.info(f"Каналы {added} добавлены в группу {group_id}")
                
        except Exception as e:
            logger.error(f"Ошибка в /add_channels: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['add_time'])
    @owner_only
    def add_time(message: Message):
        """Установить время проверки для каналов"""
        try:
            text = message.text.replace('/add_time', '').strip()
            group_id = get_selected_group(message.from_user.id)
            
            if not group_id:
                bot.reply_to(
                    message,
                    language_service.get_text('no_group_selected', message.chat.id)
                )
                return
            
            # Проверяем формат с датами для конкретного канала
            date_range = parse_datetime_range(text)
            if date_range:
                channel, start_date, end_date = date_range
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE channels SET check_until = ? 
                        WHERE channel_username = ? AND group_id = ? AND is_active = 1
                    ''', (end_date, channel, group_id))
                    
                    if cursor.rowcount > 0:
                        bot.reply_to(
                            message,
                            language_service.get_text('time_set', message.chat.id, 
                                                    channel=channel,
                                                    start=start_date.strftime('%d.%m.%Y %H:%M'),
                                                    end=end_date.strftime('%d.%m.%Y %H:%M'))
                        )
                        logger.info(f"Установлено время для {channel}: до {end_date}")
                    else:
                        bot.reply_to(
                            message,
                            language_service.get_text('channel_not_found', message.chat.id, 
                                                    channel=channel)
                        )
                return
            
            # Формат с длительностью для всех каналов
            duration = parse_time_string(text)
            if duration:
                end_date = datetime.now() + timedelta(seconds=duration)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE channels SET check_until = ? 
                        WHERE group_id = ? AND is_active = 1 AND check_until IS NULL
                    ''', (end_date, group_id))
                    
                    updated = cursor.rowcount
                    
                    if updated > 0:
                        bot.reply_to(
                            message,
                            language_service.get_text('time_set_all', message.chat.id,
                                                    end=end_date.strftime('%d.%m.%Y %H:%M'))
                        )
                        logger.info(f"Установлено время для {updated} каналов: до {end_date}")
                    else:
                        bot.reply_to(
                            message,
                            language_service.get_text('add_time_usage', message.chat.id)
                        )
                return
            
            bot.reply_to(
                message,
                language_service.get_text('add_time_usage', message.chat.id)
            )
            
        except Exception as e:
            logger.error(f"Ошибка в /add_time: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['auto_del'])
    @owner_only
    def auto_del(message: Message):
        """Установить автоудаление сообщений бота"""
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.reply_to(
                    message,
                    language_service.get_text('auto_del_usage', message.chat.id)
                )
                return
            
            time_str = args[1]
            
            # Парсим время (15s, 30s, 5m, 10m)
            match = re.match(r'^(\d+)([sm])$', time_str.lower())
            if not match:
                bot.reply_to(
                    message,
                    language_service.get_text('auto_del_usage', message.chat.id)
                )
                return
            
            value, unit = int(match.group(1)), match.group(2)
            seconds = value if unit == 's' else value * 60
            
            if seconds < MIN_AUTO_DELETE_TIME or seconds > MAX_AUTO_DELETE_TIME:
                bot.reply_to(
                    message,
                    language_service.get_text('auto_del_range', message.chat.id,
                                            min=MIN_AUTO_DELETE_TIME,
                                            max=MAX_AUTO_DELETE_TIME//60)
                )
                return
            
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
                    UPDATE groups SET auto_del_time = ? WHERE group_id = ?
                ''', (seconds, group_id))
                
                bot.reply_to(
                    message,
                    language_service.get_text('auto_del_set', message.chat.id, time=time_str)
                )
                logger.info(f"Автоудаление в группе {group_id} установлено на {seconds}с")
                
        except IndexError:
            bot.reply_to(
                message,
                language_service.get_text('auto_del_usage', message.chat.id)
            )
        except Exception as e:
            logger.error(f"Ошибка в /auto_del: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_one'])
    @owner_only
    def del_one(message: Message):
        """Удалить канал с проверки"""
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.reply_to(
                    message,
                    language_service.get_text('del_one_usage', message.chat.id)
                )
                return
            
            channel = args[1]
            if not channel.startswith('@'):
                channel = '@' + channel
            
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
                    UPDATE channels SET is_active = 0 
                    WHERE channel_username = ? AND group_id = ?
                ''', (channel, group_id))
                
                if cursor.rowcount > 0:
                    bot.reply_to(
                        message,
                        language_service.get_text('channel_deleted', message.chat.id, 
                                                channel=channel)
                    )
                    logger.info(f"Канал {channel} удален из группы {group_id}")
                else:
                    bot.reply_to(
                        message,
                        language_service.get_text('channel_not_found', message.chat.id, 
                                                channel=channel)
                    )
                    
        except Exception as e:
            logger.error(f"Ошибка в /del_one: {e}")
            bot.reply_to(
                message,
                language_service.get_text('error_occurred', message.chat.id, error=str(e))
            )

    @bot.message_handler(commands=['del_all'])
    @owner_only
    def del_all(message: Message):
        """Удалить все каналы с проверки"""
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
                UPDATE channels SET is_active = 0 WHERE group_id = ?
            ''', (group_id,))
            count = cursor.rowcount
            
            bot.reply_to(
                message,
                language_service.get_text('channels_deleted', message.chat.id, count=count)
            )
            logger.info(f"Удалено {count} каналов из группы {group_id}")

    @bot.message_handler(commands=['status'])
    @owner_only
    def status(message: Message):
        """Показать статус проверки"""
        group_id = get_selected_group(message.from_user.id)
        
        if not group_id:
            bot.reply_to(
                message,
                language_service.get_text('no_group_selected', message.chat.id)
            )
            return
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Информация о группе
                cursor.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,))
                group = cursor.fetchone()
                
                if not group:
                    bot.reply_to(message, "❌ Группа не найдена в базе")
                    return
                
                # Каналы на проверке
                cursor.execute('''
                    SELECT * FROM channels WHERE group_id = ? AND is_active = 1
                ''', (group_id,))
                channels = cursor.fetchall()
                
                # VIP пользователи
                cursor.execute('''
                    SELECT * FROM vip_users WHERE (group_id = ? OR scope = 'global')
                    AND (end_date IS NULL OR end_date > ?)
                ''', (group_id, datetime.now()))
                vips = cursor.fetchall()
                
                # Муты
                cursor.execute('''
                    SELECT * FROM muted_users WHERE group_id = ? AND mute_end > ?
                ''', (group_id, datetime.now()))
                mutes = cursor.fetchall()
            
            # Формируем статус
            status_text = language_service.get_text('status_header', message.chat.id, 
                                                   group_title=group[1])
            
            # Каналы
            status_text += language_service.get_text('channels_header', message.chat.id)
            if channels:
                for ch in channels:
                    if ch[5]:  # check_until
                        end = language_service.get_text('until', message.chat.id, 
                                                       date=ch[5][:16])
                    else:
                        end = language_service.get_text('permanent', message.chat.id)
                    status_text += language_service.get_text('channel_item', message.chat.id, 
                                                           channel=ch[2], end=end)
            else:
                status_text += language_service.get_text('no_channels', message.chat.id)
            
            # VIP
            status_text += language_service.get_text('vip_header', message.chat.id)
            if vips:
                for vip in vips:
                    vip_type = (language_service.get_text('vip_type_plus', message.chat.id) 
                               if vip[3] == 'VIP_PLUS' 
                               else language_service.get_text('vip_type_vip', message.chat.id))
                    scope = (language_service.get_text('scope_global', message.chat.id) 
                            if vip[4] == 'global' 
                            else language_service.get_text('scope_local', message.chat.id))
                    end = (language_service.get_text('until', message.chat.id, date=vip[7][:16]) 
                          if vip[7] else language_service.get_text('permanent', message.chat.id))
                    status_text += language_service.get_text('vip_item', message.chat.id, 
                                                           username=vip[2], type=vip_type, 
                                                           scope=scope, end=end)
            else:
                status_text += language_service.get_text('no_vip', message.chat.id)
            
            # Муты
            status_text += language_service.get_text('mute_header', message.chat.id)
            if mutes:
                for mute in mutes:
                    time_left = datetime.fromisoformat(mute[4]) - datetime.now()
                    hours = int(time_left.total_seconds() / 3600)
                    minutes = int((time_left.total_seconds() % 3600) / 60)
                    status_text += language_service.get_text('mute_item', message.chat.id, 
                                                           username=mute[1], hours=hours, 
                                                           minutes=minutes)
            else:
                status_text += language_service.get_text('no_mutes', message.chat.id)
            
            # Автоудаление
            status_text += language_service.get_text('auto_del_status', message.chat.id, 
                                                    time=group[3])
            
            bot.send_message(message.chat.id, status_text)
            
        except Exception as e:
            logger.error(f"Ошибка в /status: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")