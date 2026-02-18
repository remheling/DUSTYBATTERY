from functools import wraps
from telebot.types import Message
from config import OWNER_ID
import logging

logger = logging.getLogger(__name__)

def owner_only(func):
    """Декоратор для проверки прав владельца"""
    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id == OWNER_ID:
            return func(message, *args, **kwargs)
        else:
            logger.warning(f"⚠️ Попытка доступа к команде {message.text} от {message.from_user.id}")
            return None
    return wrapper

def group_only(func):
    """Декоратор для проверки, что команда вызвана в группе"""
    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        if message.chat.type in ['group', 'supergroup']:
            return func(message, *args, **kwargs)
        else:
            # Для команды vip_info разрешаем в личке только владельцу
            if message.text and message.text.startswith('/vip_info') and message.from_user.id == OWNER_ID:
                return func(message, *args, **kwargs)
            bot = args[0] if args else None
            if bot:
                bot.reply_to(message, "❌ Эта команда доступна только в группах")
            return None
    return wrapper

def admin_only(func):
    """Декоратор для проверки прав администратора группы"""
    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        try:
            bot = args[0] if args else None
            if not bot:
                return func(message, *args, **kwargs)
            
            # Владелец бота всегда имеет доступ
            if message.from_user.id == OWNER_ID:
                return func(message, *args, **kwargs)
            
            # Проверяем, является ли пользователь администратором группы
            if message.chat.type in ['group', 'supergroup']:
                member = bot.get_chat_member(message.chat.id, message.from_user.id)
                if member.status in ['administrator', 'creator']:
                    return func(message, *args, **kwargs)
            
            bot.reply_to(message, "❌ Эта команда доступна только администраторам группы")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка в admin_only декораторе: {e}")
            return None
    return wrapper