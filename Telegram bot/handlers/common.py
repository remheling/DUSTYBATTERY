from telebot import TeleBot
from telebot.types import Message
from services.language_service import language_service
from config import OWNER_ID
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        """Обработчик команды /start"""
        try:
            text = language_service.get_text('start', message.chat.id)
            bot.reply_to(message, text)
            logger.info(f"Команда /start от {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в /start: {e}")
            bot.reply_to(message, "❌ Произошла ошибка")
    
    @bot.message_handler(commands=['help'])
    def help_command(message: Message):
        """Обработчик команды /help"""
        try:
            # Определяем язык
            lang = language_service.get_chat_language(message.chat.id)
            
            if lang == 'ru':
                help_text = """
🔹 **ДОСТУПНЫЕ КОМАНДЫ:**

👤 **ДЛЯ ВСЕХ:**
/start - Приветствие
/vip_info - Информация о VIP

👑 **ДЛЯ ВЛАДЕЛЬЦА:**

📌 **Управление группами:**
/group @группа - Выбрать группу
/group_list - Список всех групп
/scan_groups - Найти все группы

📢 **Управление каналами:**
/add_one @канал - Добавить канал
/add_channels @канал1 @канал2 @канал3 - Добавить несколько
/add_time 6h/12h/1d - Установить время
/del_one @канал - Удалить канал
/del_all - Удалить все каналы
/status - Статус проверки
/auto_del 30s - Автоудаление

💎 **VIP управление:**
/add_VIP @user - Добавить VIP
/add_VIP_PLUS @user - Добавить VIP+
/del_VIP @user - Удалить VIP
/mute_status - Статус мутов

🌐 **Язык:**
/language ru - Русский
/language en - English
/lang - Текущий язык
                """
            else:
                help_text = """
🔹 **AVAILABLE COMMANDS:**

👤 **FOR EVERYONE:**
/start - Greeting
/vip_info - VIP information

👑 **FOR OWNER:**

📌 **Group Management:**
/group @group - Select group
/group_list - List all groups
/scan_groups - Find all groups

📢 **Channel Management:**
/add_one @channel - Add channel
/add_channels @channel1 @channel2 @channel3 - Add multiple
/add_time 6h/12h/1d - Set time
/del_one @channel - Remove channel
/del_all - Remove all channels
/status - Check status
/auto_del 30s - Auto-delete

💎 **VIP Management:**
/add_VIP @user - Add VIP
/add_VIP_PLUS @user - Add VIP+
/del_VIP @user - Remove VIP
/mute_status - Mute status

🌐 **Language:**
/language ru - Russian
/language en - English
/lang - Current language
                """
            
            bot.reply_to(message, help_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка в /help: {e}")
    
    @bot.message_handler(commands=['vip_info'])
    def vip_info_command(message: Message):
        """Обработчик команды /vip_info"""
        try:
            # Команда доступна всем в группах
            if message.chat.type in ['group', 'supergroup'] or message.from_user.id == OWNER_ID:
                text = language_service.get_text('vip_info', message.chat.id)
                bot.reply_to(message, text)
            else:
                bot.reply_to(message, "❌ Эта команда доступна только в группах")
        except Exception as e:
            logger.error(f"Ошибка в /vip_info: {e}")