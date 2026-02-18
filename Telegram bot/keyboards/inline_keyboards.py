from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from services.language_service import language_service

def create_channel_keyboard(channels: List[str], chat_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками каналов"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for channel in channels:
        clean_channel = channel.lstrip('@')
        button_text = language_service.get_text('subscribe_button', chat_id, channel=channel)
        button = InlineKeyboardButton(
            text=button_text,
            url=f"https://t.me/{clean_channel}"
        )
        keyboard.add(button)
    
    vip_button_text = language_service.get_text('vip_button', chat_id)
    vip_button = InlineKeyboardButton(
        text=vip_button_text,
        callback_data="vip_info"
    )
    keyboard.add(vip_button)
    
    return keyboard

def create_confirmation_keyboard(action: str, target: str, chat_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения действия"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    confirm_text = language_service.get_text('button_confirm', chat_id)
    cancel_text = language_service.get_text('button_cancel', chat_id)
    
    confirm = InlineKeyboardButton(
        text=confirm_text,
        callback_data=f"confirm_{action}_{target}"
    )
    cancel = InlineKeyboardButton(
        text=cancel_text,
        callback_data=f"cancel_{action}"
    )
    
    keyboard.add(confirm, cancel)
    return keyboard

def create_group_selection_keyboard(groups: List[tuple], chat_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора группы"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for group_id, group_title in groups:
        button = InlineKeyboardButton(
            text=group_title,
            callback_data=f"select_group_{group_id}"
        )
        keyboard.add(button)
    
    return keyboard