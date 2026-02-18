import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_NAME, OWNER_ID
import logging

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info(f"📁 Инициализация базы данных: {DATABASE_NAME}")
        self._init_db()
        self._check_tables()

    def _check_tables(self):
        """Проверяет наличие всех таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            logger.info(f"📊 Таблицы в БД: {', '.join(table_names)}")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(DATABASE_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Ошибка БД: {e}")
            raise e
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица групп
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    group_title TEXT,
                    group_username TEXT,
                    added_date TIMESTAMP,
                    auto_del_time INTEGER DEFAULT 30
                )
            ''')
            
            # Таблица каналов на проверке
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_username TEXT,
                    group_id INTEGER,
                    added_date TIMESTAMP,
                    check_until TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY(group_id) REFERENCES groups(group_id)
                )
            ''')
            
            # Таблица VIP пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vip_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    vip_type TEXT CHECK(vip_type IN ('VIP', 'VIP_PLUS')),
                    scope TEXT CHECK(scope IN ('local', 'global')),
                    group_id INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    FOREIGN KEY(group_id) REFERENCES groups(group_id)
                )
            ''')
            
            # Таблица мутированных пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS muted_users (
                    user_id INTEGER,
                    username TEXT,
                    group_id INTEGER,
                    mute_time TIMESTAMP,
                    mute_end TIMESTAMP,
                    violations INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, group_id)
                )
            ''')
            
            # Таблица выбранной группы для owner
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS owner_selected_group (
                    owner_id INTEGER PRIMARY KEY,
                    selected_group_id INTEGER
                )
            ''')
            
            # Вставляем запись для владельца если нет
            cursor.execute('''
                INSERT OR IGNORE INTO owner_selected_group (owner_id, selected_group_id) 
                VALUES (?, NULL)
            ''', (OWNER_ID,))
            
            # Таблица для черного списка команд
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist_commands (
                    command TEXT PRIMARY KEY,
                    description TEXT
                )
            ''')
            
            # Таблица языков чатов - ОЧЕНЬ ВАЖНО!
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_languages (
                    chat_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ru'
                )
            ''')
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'ru',
                    joined_date TIMESTAMP
                )
            ''')
            
            # Добавляем команды в черный список
            blacklist_commands = [
                ('/add_one', 'Добавить канал'),
                ('/add_channels', 'Добавить несколько каналов'),
                ('/add_time', 'Установить время проверки'),
                ('/auto_del', 'Автоудаление'),
                ('/del_one', 'Удалить канал'),
                ('/del_all', 'Удалить все каналы'),
                ('/add_VIP', 'Добавить VIP'),
                ('/ad_VIP_PLUS', 'Добавить VIP PLUS'),
                ('/add_VIP_local', 'Добавить локальный VIP'),
                ('/add_VIP_global', 'Добавить глобальный VIP'),
                ('/add_VIP_time', 'VIP с временем'),
                ('/del_VIP', 'Удалить VIP'),
                ('/del_VIPPLUS', 'Удалить VIP PLUS'),
                ('/del_all_VIP', 'Удалить всех VIP'),
                ('/del_all_VIPPLUS', 'Удалить всех VIP PLUS'),
                ('/mute_status', 'Статус мутов'),
                ('/off_mute', 'Снять мут'),
                ('/del_all_mute', 'Удалить все муты'),
                ('/group', 'Выбор группы'),
                ('/group_list', 'Список групп'),
                ('/scan_groups', 'Сканировать группы')
            ]
            
            for cmd, desc in blacklist_commands:
                cursor.execute('INSERT OR IGNORE INTO blacklist_commands (command, description) VALUES (?, ?)',
                             (cmd, desc))
            
            logger.info("✅ База данных инициализирована")

db = Database()