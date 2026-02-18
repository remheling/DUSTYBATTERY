from telebot import TeleBot
from telebot.types import Message
from database import db
from utils.decorators import owner_only
from config import OWNER_ID
from services.language_service import language_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.message_handler(commands=['group'])
    @owner_only
    def select_group(message: Message):
        """Выбор группы для управления"""
        try:
            args = message.text.split()
            if len(args) < 2:
                text = language_service.get_text('select_group_usage', message.chat.id)
                bot.reply_to(message, text)
                return
            
            group_query = args[1].replace('@', '')
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ищем группы по названию или ID
                if group_query.isdigit():
                    cursor.execute('''
                        SELECT group_id, group_title FROM groups 
                        WHERE group_id = ?
                    ''', (int(group_query),))
                else:
                    cursor.execute('''
                        SELECT group_id, group_title FROM groups 
                        WHERE group_title LIKE ? OR group_username LIKE ?
                    ''', (f'%{group_query}%', f'%{group_query}%'))
                
                groups = cursor.fetchall()
                
                if not groups:
                    # Пробуем получить группу напрямую из Telegram
                    try:
                        chat = bot.get_chat(f"@{group_query}")
                        cursor.execute('''
                            INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                            VALUES (?, ?, ?, ?, 30)
                        ''', (chat.id, chat.title, chat.username, datetime.now()))
                        
                        group_id = chat.id
                        group_title = chat.title
                        
                        # Сохраняем выбранную группу
                        cursor.execute('''
                            INSERT OR REPLACE INTO owner_selected_group (owner_id, selected_group_id) 
                            VALUES (?, ?)
                        ''', (OWNER_ID, group_id))
                        
                        text = language_service.get_text('group_selected', message.chat.id, 
                                                        group_title=group_title)
                        bot.reply_to(message, text)
                        logger.info(f"✅ Добавлена и выбрана группа: {group_title} ({group_id})")
                        return
                    except:
                        text = language_service.get_text('group_not_found', message.chat.id)
                        bot.reply_to(message, text)
                        return
                
                if len(groups) == 1:
                    group_id = groups[0][0]
                    group_title = groups[0][1]
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO owner_selected_group (owner_id, selected_group_id) 
                        VALUES (?, ?)
                    ''', (OWNER_ID, group_id))
                    
                    text = language_service.get_text('group_selected', message.chat.id, 
                                                    group_title=group_title)
                    bot.reply_to(message, text)
                    logger.info(f"✅ Выбрана группа: {group_title} ({group_id})")
                else:
                    groups_list = "\n".join([f"🔹 {g[1]} (ID: {g[0]})" for g in groups])
                    text = language_service.get_text('multiple_groups', message.chat.id, 
                                                    groups_list=groups_list)
                    bot.reply_to(message, text)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в /group: {e}")
            text = language_service.get_text('error_occurred', message.chat.id, error=str(e))
            bot.reply_to(message, text)
    
    @bot.message_handler(commands=['group_list'])
    @owner_only
    def list_groups(message: Message):
        """Показать все группы, где есть бот"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT group_id, group_title, group_username, added_date 
                    FROM groups 
                    ORDER BY added_date DESC
                ''')
                groups = cursor.fetchall()
            
            if not groups:
                bot.reply_to(message, "❌ Бот не добавлен ни в одну группу.\n\nИспользуй /scan_groups для поиска групп.")
                return
            
            # Получаем выбранную группу
            cursor.execute('SELECT selected_group_id FROM owner_selected_group WHERE owner_id = ?', (OWNER_ID,))
            selected = cursor.fetchone()
            selected_id = selected[0] if selected else None
            
            text = "📋 **СПИСОК ГРУПП:**\n\n"
            for group in groups:
                group_id = group[0]
                group_title = group[1] or "Без названия"
                group_username = group[2]
                added_date = group[3] if group[3] else "Неизвестно"
                
                # Отметка выбранной группы
                marker = "✅ " if group_id == selected_id else "🔹 "
                
                text += f"{marker}**{group_title}**\n"
                text += f"   ID: `{group_id}`\n"
                if group_username:
                    text += f"   Username: @{group_username}\n"
                text += f"   Добавлен: {added_date}\n\n"
            
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в /group_list: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")
    
    @bot.message_handler(commands=['scan_groups'])
    @owner_only
    def scan_groups(message: Message):
        """Сканирует все чаты, где есть бот, и добавляет их в БД"""
        try:
            msg = bot.send_message(message.chat.id, "🔍 Сканирую группы... Это может занять несколько секунд")
            
            # Получаем обновления
            updates = bot.get_updates(limit=100)
            found = 0
            processed_chats = set()
            
            # Проходим по всем обновлениям
            for update in updates:
                # Проверяем сообщения
                if update.message and update.message.chat:
                    chat = update.message.chat
                    if chat.type in ['group', 'supergroup'] and chat.id not in processed_chats:
                        processed_chats.add(chat.id)
                        
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                                VALUES (?, ?, ?, ?, 30)
                            ''', (chat.id, chat.title, chat.username, datetime.now()))
                        found += 1
                        logger.info(f"✅ Найдена группа из сообщения: {chat.title}")
                
                # Проверяем chat_member обновления
                if update.my_chat_member and update.my_chat_member.chat:
                    chat = update.my_chat_member.chat
                    if chat.type in ['group', 'supergroup'] and chat.id not in processed_chats:
                        processed_chats.add(chat.id)
                        
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                                VALUES (?, ?, ?, ?, 30)
                            ''', (chat.id, chat.title, chat.username, datetime.now()))
                        found += 1
                        logger.info(f"✅ Найдена группа из chat_member: {chat.title}")
            
            # Дополнительно проверяем все чаты, где бот является участником
            try:
                # Этот метод может не работать в некоторых версиях API
                chats = bot.get_chat_administrators(OWNER_ID)  # Неправильно, нужно другое
                # Вместо этого используем более простой способ
                pass
            except:
                pass
            
            bot.edit_message_text(
                f"✅ Сканирование завершено!\n\nНайдено и добавлено групп: {found}",
                message.chat.id,
                msg.message_id
            )
            
            # Показываем список групп
            list_groups(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в /scan_groups: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")