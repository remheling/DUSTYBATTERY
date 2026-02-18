from typing import Optional
from database import db
from locales import ru, en
import logging

logger = logging.getLogger(__name__)

class LanguageService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.languages = {
            'ru': ru.TRANSLATIONS,
            'en': en.TRANSLATIONS
        }
        logger.info("✅ LanguageService инициализирован")
        logger.info(f"📚 Доступные языки: {', '.join(self.languages.keys())}")
    
    def get_text(self, key: str, chat_id: int, **kwargs) -> str:
        """Получает текст на нужном языке с подстановкой переменных"""
        try:
            lang = self.get_chat_language(chat_id)
            translations = self.languages.get(lang, self.languages['ru'])
            
            # Получаем текст или ключ если нет перевода
            text = translations.get(key)
            if text is None:
                logger.warning(f"⚠️ Отсутствует перевод для ключа '{key}' на языке {lang}")
                text = key
            
            # Подставляем переменные
            if kwargs and text != key:
                try:
                    text = text.format(**kwargs)
                except KeyError as e:
                    logger.error(f"❌ Отсутствует ключ в переводе '{key}': {e}")
                except Exception as e:
                    logger.error(f"❌ Ошибка форматирования текста '{key}': {e}")
            
            return text
        except Exception as e:
            logger.error(f"❌ Ошибка в get_text для ключа '{key}': {e}")
            return key
    
    def get_chat_language(self, chat_id: int) -> str:
        """Получает язык чата"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Убеждаемся что таблица существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_languages (
                        chat_id INTEGER PRIMARY KEY,
                        language TEXT DEFAULT 'ru'
                    )
                ''')
                
                cursor.execute('''
                    SELECT language FROM chat_languages WHERE chat_id = ?
                ''', (chat_id,))
                result = cursor.fetchone()
                
                if result:
                    return result['language']
                
                # По умолчанию русский
                self.set_chat_language(chat_id, 'ru')
                return 'ru'
        except Exception as e:
            logger.error(f"❌ Ошибка получения языка для чата {chat_id}: {e}")
            return 'ru'
    
    def set_chat_language(self, chat_id: int, language: str) -> bool:
        """Устанавливает язык для чата"""
        try:
            if language not in self.languages:
                logger.warning(f"⚠️ Попытка установить неподдерживаемый язык: {language}")
                return False
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Убеждаемся что таблица существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_languages (
                        chat_id INTEGER PRIMARY KEY,
                        language TEXT DEFAULT 'ru'
                    )
                ''')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO chat_languages (chat_id, language)
                    VALUES (?, ?)
                ''', (chat_id, language))
                
                logger.info(f"✅ Язык для чата {chat_id} установлен на {language}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка установки языка для чата {chat_id}: {e}")
            return False

# Глобальный экземпляр
language_service = LanguageService()