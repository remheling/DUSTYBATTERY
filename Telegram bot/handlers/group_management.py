from telebot import TeleBot
from telebot.types import Message
from database import db
from utils.decorators import owner_only
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.message_handler(commands=['group_list'])
    @owner_only
    def list_groups(message: Message):
        """Показать все группы, где есть бот"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT group_id, group_title, added_date FROM groups ORDER BY added_date DESC")
                groups = cursor.fetchall()
            
            if not groups:
                bot.reply_to(message, "❌ Бот не добавлен ни в одну группу")
                return
            
            text = "📋 **Список групп:**\n\n"
            for group in groups:
                group_id = group[0]
                group_title = group[1]
                added_date = group[2] if len(group) > 2 else "Неизвестно"
                
                text += f"🔹 {group_title}\n"
                text += f"   ID: `{group_id}`\n"
                text += f"   Добавлен: {added_date}\n\n"
            
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в /group_list: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")