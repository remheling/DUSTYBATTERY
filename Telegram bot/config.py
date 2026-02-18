import os
from typing import Final
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота
BOT_TOKEN: Final = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле!")

# ID владельца
OWNER_ID_STR: Final = os.getenv('OWNER_ID')
if not OWNER_ID_STR:
    raise ValueError("OWNER_ID не установлен в .env файле!")
OWNER_ID: Final = int(OWNER_ID_STR)

# Настройки базы данных
DATABASE_NAME: Final = os.getenv('DATABASE_NAME', 'bot_database.db')

# Максимальное количество каналов на проверку в одной группе
MAX_CHANNELS_PER_GROUP: Final = 3

# Временные ограничения
MIN_AUTO_DELETE_TIME: Final = 15  # секунд
MAX_AUTO_DELETE_TIME: Final = 600  # секунд (10 минут)

# Режим отладки
DEBUG: Final = os.getenv('DEBUG', 'False').lower() == 'true'

# Уровень логирования
LOG_LEVEL: Final = os.getenv('LOG_LEVEL', 'INFO')

# Различия VIP и VIP PLUS
VIP_FEATURES = {
    'VIP': {
        'name': '💎 VIP',
        'features': {
            'subscription_free': True,
            'max_groups': 1,
            'contests': True,
            'antiflood_protection': False,
            'no_mute': False,
            'media_unlimited': False,
            'stats': False,
            'custom_commands': False,
            'profile_mark': 'VIP'
        }
    },
    'VIP_PLUS': {
        'name': '👑 VIP PLUS',
        'features': {
            'subscription_free': True,
            'max_groups': 3,
            'contests': True,
            'antiflood_protection': True,
            'no_mute': True,
            'media_unlimited': True,
            'stats': True,
            'custom_commands': True,
            'profile_mark': 'VIP_PLUS'
        }
    }
}

# Уровни нарушений для мута
VIOLATION_LEVELS = {
    1: {"mute_time": 0, "action": "warning"},           # 1 нарушение - предупреждение
    2: {"mute_time": 600, "action": "mute"},            # 2 нарушение - мут 10 минут
    3: {"mute_time": 3600, "action": "mute"},           # 3 нарушение - мут 1 час
    4: {"mute_time": 86400, "action": "mute"}           # 4 нарушение - мут 24 часа
}