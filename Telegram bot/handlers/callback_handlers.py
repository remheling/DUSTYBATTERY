from telebot import TeleBot
from telebot.types import CallbackQuery
from services.language_service import language_service
import logging

logger = logging.getLogger(__name__)

def register_handlers(bot: TeleBot):
    
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        """Обработчик callback запросов от инлайн кнопок"""
        try:
            logger.info(f"Callback data: {call.data}")
            
            if call.data == "vip_info":
                text = language_service.get_text('vip_info', call.message.chat.id)
                bot.answer_callback_query(call.id, text, show_alert=True)
            
            elif call.data.startswith("select_group_"):
                group_id = int(call.data.replace("select_group_", ""))
                bot.answer_callback_query(call.id, f"✅ Выбрана группа {group_id}")
                
            elif call.data.startswith("confirm_"):
                bot.answer_callback_query(call.id, "✅ Подтверждено")
                
            elif call.data.startswith("cancel_"):
                bot.answer_callback_query(call.id, "❌ Отменено")
                
            else:
                bot.answer_callback_query(call.id, "⚠️ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в callback handler: {e}")
            bot.answer_callback_query(call.id, "❌ Ошибка")