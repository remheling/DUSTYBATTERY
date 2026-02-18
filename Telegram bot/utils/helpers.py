from database import db
from config import OWNER_ID

def get_user_id_by_username(bot, username):
    """Получает ID пользователя по username"""
    try:
        username = username.replace('@', '')
        user = bot.get_chat(f"@{username}")
        return user.id
    except:
        return None

def get_group_id_by_username(bot, group_username):
    """Получает ID группы по username"""
    try:
        group_username = group_username.replace('@', '')
        group = bot.get_chat(f"@{group_username}")
        return group.id
    except:
        return None

def get_selected_group(owner_id):
    """Получает выбранную группу для owner"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT selected_group_id FROM owner_selected_group WHERE owner_id = ?
        ''', (owner_id,))
        result = cursor.fetchone()
        return result['selected_group_id'] if result else None