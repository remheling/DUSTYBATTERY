from telebot import TeleBot
from telebot.types import Message
from utils.decorators import owner_only
from services.language_service import language_service
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.message_handler(commands=['language', 'lang'])
    @owner_only
    def handle_language(message: Message):
        """Обработчик команд языка"""
        try:
            args = message.text.split()
            cmd = args[0].lower()
            
            # Команда /lang - показать текущий язык
            if cmd == '/lang' or (cmd == '/language' and len(args) == 1):
                current_lang = language_service.get_chat_language(message.chat.id)
                lang_names = {'ru': 'Русский', 'en': 'English'}
                lang_name = lang_names.get(current_lang, current_lang)
                
                text = f"🌐 **Текущий язык:** {lang_name} ({current_lang})\n\n"
                text += "Для смены языка используй:\n"
                text += "`/language ru` - Русский\n"
                text += "`/language en` - English"
                
                bot.reply_to(message, text, parse_mode="Markdown")
                return
            
            # Команда /language ru/en - сменить язык
            if len(args) >= 2:
                lang = args[1].lower()
                
                if lang not in ['ru', 'en']:
                    text = language_service.get_text('language_usage', message.chat.id)
                    bot.reply_to(message, text)
                    return
                
                if language_service.set_chat_language(message.chat.id, lang):
                    # Отправляем подтверждение на новом языке
                    response = language_service.get_text('language_set', message.chat.id)
                    bot.reply_to(message, response)
                    logger.info(f"✅ Язык для чата {message.chat.id} изменен на {lang}")
                    
                    # Показываем тестовое сообщение
                    test_text = language_service.get_text('start', message.chat.id)
                    bot.send_message(message.chat.id, f"📝 Тест: {test_text[:50]}...")
                else:
                    bot.reply_to(message, "❌ Ошибка при установке языка")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в language handler: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")
    
    @bot.message_handler(commands=['test_lang'])
    @owner_only
    def test_language(message: Message):
        """Тестовая команда для проверки языка"""
        try:
            current_lang = language_service.get_chat_language(message.chat.id)
            
            # Тестируем разные ключи
            test_keys = [
                ('start', {}),
                ('vip_info', {}),
                ('select_group_usage', {}),
                ('add_one_usage', {}),
                ('subscription_warning', {'username': 'test_user', 'channels': '@test_channel'}),
                ('mute_message', {'username': 'test_user', 'time': '10 минут'}),
            ]
            
            response = f"🌐 **Текущий язык:** {current_lang}\n\n"
            response += "**ТЕСТОВЫЕ ПЕРЕВОДЫ:**\n"
            response += "=" * 30 + "\n\n"
            
            for key, params in test_keys:
                try:
                    text = language_service.get_text(key, message.chat.id, **params)
                    preview = text[:100] + "..." if len(text) > 100 else text
                    response += f"🔹 **{key}**:\n{preview}\n\n"
                except Exception as e:
                    response += f"🔹 **{key}**: ❌ Ошибка: {e}\n\n"
            
            # Разбиваем длинное сообщение
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в /test_lang: {e}")
            bot.reply_to(message, f"❌ Ошибка: {e}")