import logging
from datetime import datetime
from typing import Optional, List, Dict
from database import db
from config import VIP_FEATURES

logger = logging.getLogger(__name__)

class VIPService:
    def __init__(self, bot):
        self.bot = bot

    def check_vip_limits(self, user_id: int, group_id: int, vip_type: str) -> bool:
        """
        Проверяет лимиты VIP подписки
        Возвращает True, если можно добавить, False если превышен лимит групп
        """
        features = VIP_FEATURES.get(vip_type, {}).get('features', {})
        max_groups = features.get('max_groups', 1)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(DISTINCT group_id) FROM vip_users 
                WHERE user_id = ? AND vip_type = ? AND scope = 'local'
                AND (end_date IS NULL OR end_date > ?)
            ''', (user_id, vip_type, datetime.now()))
            
            current_groups = cursor.fetchone()[0] or 0
            
            return current_groups < max_groups

    def get_vip_features(self, user_id: int, group_id: int) -> Dict:
        """Возвращает доступные функции для VIP пользователя"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT vip_type FROM vip_users 
                WHERE user_id = ? AND (group_id = ? OR scope = 'global')
                AND (end_date IS NULL OR end_date > ?)
            ''', (user_id, group_id, datetime.now()))
            
            result = cursor.fetchone()
            
            if result:
                vip_type = result['vip_type']
                return VIP_FEATURES.get(vip_type, {}).get('features', {})
            
            return {}

    def has_immunity_to_mute(self, user_id: int, group_id: int) -> bool:
        """Проверяет, есть ли у пользователя иммунитет к мутам (VIP PLUS)"""
        features = self.get_vip_features(user_id, group_id)
        return features.get('no_mute', False)

    def has_antiflood_immunity(self, user_id: int, group_id: int) -> bool:
        """Проверяет иммунитет к антифлуду"""
        features = self.get_vip_features(user_id, group_id)
        return features.get('antiflood_protection', False)

    def can_send_unlimited_media(self, user_id: int, group_id: int) -> bool:
        """Проверяет безлимит на медиа"""
        features = self.get_vip_features(user_id, group_id)
        return features.get('media_unlimited', False)

    def get_profile_mark(self, user_id: int, group_id: int) -> str:
        """Возвращает отметку для профиля"""
        features = self.get_vip_features(user_id, group_id)
        return features.get('profile_mark', '')

    def show_vip_status(self, user_id: int, group_id: int) -> str:
        """Показывает статус VIP пользователя"""
        features = self.get_vip_features(user_id, group_id)
        
        if not features:
            return "❌ Нет активной VIP подписки"
        
        vip_type = "VIP" if features.get('profile_mark') == 'VIP' else "VIP PLUS"
        
        status = f"✨ **{vip_type} статус активен** ✨\n\n"
        status += "🔹 **Доступные возможности:**\n"
        
        if features.get('max_groups') == 3:
            status += "✅ Доступ в 3 группы одновременно\n"
        
        if features.get('no_mute'):
            status += "✅ Иммунитет к мутам\n"
        
        if features.get('antiflood_protection'):
            status += "✅ Защита от антифлуда\n"
        
        if features.get('media_unlimited'):
            status += "✅ Безлимит на медиафайлы\n"
        
        if features.get('stats'):
            status += "✅ Доступ к статистике\n"
        
        if features.get('custom_commands'):
            status += "✅ Свои команды (до 3)\n"
        
        status += "\n✅ Участие в конкурсах"
        
        return status