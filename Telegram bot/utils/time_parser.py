import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

def parse_time_string(time_str: str) -> Optional[int]:
    """
    Парсит строку времени в секунды
    Примеры: 6h, 12h, 1d, 30m, 348s
    """
    match = re.match(r'^(\d+)([hmds])$', time_str.lower())
    if not match:
        return None
    
    value, unit = int(match.group(1)), match.group(2)
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    return value * multipliers.get(unit, 1)

def parse_datetime_range(date_range: str) -> Optional[Tuple[datetime, datetime]]:
    """
    Парсит диапазон дат в формате: XX.XX.XXXX XX:XX до XX.XX.XXXX XX:XX
    """
    pattern = r'^(@\S+)\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\s+до\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})$'
    match = re.match(pattern, date_range)
    
    if not match:
        return None
    
    try:
        channel = match.group(1)
        start_date = datetime.strptime(match.group(2), '%d.%m.%Y %H:%M')
        end_date = datetime.strptime(match.group(3), '%d.%m.%Y %H:%M')
        
        if end_date <= start_date:
            return None
            
        return start_date, end_date
    except ValueError:
        return None

def parse_duration_to_end(duration: str) -> Optional[datetime]:
    """
    Парсит длительность и возвращает дату окончания
    Примеры: 7d, 30d
    """
    seconds = parse_time_string(duration)
    if seconds:
        return datetime.now() + timedelta(seconds=seconds)
    return None

def format_datetime(dt: datetime) -> str:
    """Форматирует дату и время для отображения"""
    return dt.strftime('%d.%m.%Y %H:%M:%S')