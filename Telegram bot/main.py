#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import os
import sys
from telebot import TeleBot
from config import BOT_TOKEN, LOG_LEVEL, DEBUG, OWNER_ID
from database import db
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
try:
    bot = TeleBot(BOT_TOKEN)
    logger.info("✅ Бот успешно инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    sys.exit(1)

# Импорт обработчиков
from handlers import (
    common,
    owner,
    group_management,
    channel_management,
    vip_management,
    mute_management,
    group_events,
    language,
    callback_handlers
)

# Импорт сервисов
from services.scheduler import scheduler
from services.language_service import language_service

def register_all_handlers():
    """Регистрирует все обработчики"""
    logger.info("📝 Регистрация обработчиков...")
    
    try:
        common.register_handlers(bot)
        owner.register_handlers(bot)
        group_management.register_handlers(bot)
        channel_management.register_handlers(bot)
        vip_management.register_handlers(bot)
        mute_management.register_handlers(bot)
        group_events.register_handlers(bot)
        language.register_handlers(bot)
        callback_handlers.register_handlers(bot)
        
        logger.info("✅ Все обработчики зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации обработчиков: {e}")
        raise

def check_existing_groups():
    """Проверяет существующие группы при запуске"""
    try:
        logger.info("🔍 Проверка существующих групп...")
        
        # Получаем информацию о боте
        bot_info = bot.get_me()
        logger.info(f"🤖 Бот: @{bot_info.username} (ID: {bot_info.id})")
        
        # Получаем обновления за последние 24 часа
        updates = bot.get_updates(limit=100, timeout=30)
        found_groups = set()
        
        for update in updates:
            # Проверяем сообщения
            if update.message and update.message.chat:
                chat = update.message.chat
                if chat.type in ['group', 'supergroup']:
                    found_groups.add(chat.id)
                    logger.info(f"📝 Найдена группа из сообщения: {chat.title}")
            
            # Проверяем chat_member обновления
            if update.my_chat_member and update.my_chat_member.chat:
                chat = update.my_chat_member.chat
                if chat.type in ['group', 'supergroup']:
                    found_groups.add(chat.id)
                    logger.info(f"👥 Найдена группа из chat_member: {chat.title}")
        
        # Добавляем найденные группы в БД
        added = 0
        for chat_id in found_groups:
            try:
                chat = bot.get_chat(chat_id)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Проверяем существование группы
                    cursor.execute('SELECT * FROM groups WHERE group_id = ?', (chat_id,))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        cursor.execute('''
                            INSERT INTO groups (group_id, group_title, group_username, added_date, auto_del_time)
                            VALUES (?, ?, ?, ?, 30)
                        ''', (chat_id, chat.title, chat.username, datetime.now()))
                        added += 1
                        logger.info(f"✅ Добавлена новая группа: {chat.title}")
                    else:
                        # Обновляем информацию о группе
                        cursor.execute('''
                            UPDATE groups SET group_title = ?, group_username = ?
                            WHERE group_id = ?
                        ''', (chat.title, chat.username, chat_id))
                        logger.info(f"🔄 Обновлена информация о группе: {chat.title}")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка при обработке группы {chat_id}: {e}")
        
        logger.info(f"✅ Найдено групп: {len(found_groups)}, добавлено новых: {added}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке существующих групп: {e}")

# Flask для Replit (keep-alive)
try:
    from flask import Flask
    from threading import Thread
    
    app = Flask('')
    
    @app.route('/')
    def home():
        return "🤖 Бот работает!"
    
    @app.route('/health')
    def health():
        return "OK", 200
    
    def run_flask():
        app.run(host='0.0.0.0', port=8080)
    
    def keep_alive():
        t = Thread(target=run_flask)
        t.daemon = True
        t.start()
        logger.info("🌐 Flask сервер запущен на порту 8080")
        
except ImportError:
    logger.warning("⚠️ Flask не установлен, keep-alive отключен")
    def keep_alive():
        pass

def main():
    """Главная функция запуска бота"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК БОТА")
    logger.info(f"👤 ID владельца: {OWNER_ID}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info("=" * 60)
    
    # Проверка подключения к Telegram
    try:
        bot_info = bot.get_me()
        logger.info(f"✅ Бот авторизован: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации бота: {e}")
        logger.error("Проверьте токен в .env файле")
        sys.exit(1)
    
    # Регистрируем обработчики
    register_all_handlers()
    
    # Проверяем существующие группы
    check_existing_groups()
    
    # Запускаем планировщик
    try:
        scheduler.set_bot(bot)
        logger.info("✅ Планировщик задач запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")
    
    # Запускаем Flask сервер для Replit
    keep_alive()
    
    # Отправляем уведомление владельцу
    try:
        bot.send_message(
            OWNER_ID,
            "✅ **Бот успешно запущен и готов к работе!**\n\n"
            "Используй /help для списка команд\n"
            "Используй /scan_groups для поиска всех групп",
            parse_mode="Markdown"
        )
        logger.info("✅ Уведомление владельцу отправлено")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление владельцу: {e}")
    
    logger.info("✅ Бот запущен и ожидает сообщения...")
    
    # Очищаем старые обновления
    try:
        bot.get_updates(offset=-1)
        logger.info("✅ Кэш обновлений очищен")
    except:
        pass
    
    # Бесконечный polling с обработкой ошибок
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            if DEBUG:
                logger.info("🔄 Запуск polling в режиме отладки")
            
            bot.polling(none_stop=True, interval=1, timeout=30)
            
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Ошибка в polling (попытка {retry_count}): {e}")
            
            if retry_count >= max_retries:
                logger.critical("❌ Превышено количество попыток переподключения")
                time.sleep(60)
                retry_count = 0
            
            time.sleep(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
        sys.exit(1)