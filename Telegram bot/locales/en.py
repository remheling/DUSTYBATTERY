# English language
TRANSLATIONS = {
    # Greetings and general
    'start': '🔒 Hello, I am an administrator bot.\nMy task is to maintain order in groups. I check subscription to channels and delete messages from those who are not subscribed.\n\nThe owner can control me through special commands. Just be an obedient participant and there will be no problems.',
    
    'vip_info': '''💎 VIP subscription in the bot:

🔹 VIP - basic level
   • Free from subscription in 1 group
   • Access to contests

🔸 VIP PLUS - premium level
   • Free from subscription in 3 groups
   • Immunity to mutes
   • Anti-flood protection
   • Unlimited media
   • Statistics access
   • Custom commands

Trial period: 7 days
Full access: 30 days''',
    
    # Commands
    'select_group_usage': '❌ Usage: /group @group_name',
    'group_not_found': '❌ Group not found',
    'group_selected': '✅ Selected group: {group_title}',
    'multiple_groups': 'Multiple groups found:\n{groups_list}',
    
    # Channel management
    'add_one_usage': '❌ Usage: /add_one @channel',
    'no_group_selected': '❌ First select a group with /group command',
    'max_channels': '❌ Maximum {max} channels per group',
    'channel_added': '✅ Channel {channel} added for verification',
    
    'add_channels_usage': '❌ Usage: /add_channels @channel1 @channel2 @channel3',
    'can_add_only': '❌ You can only add {available} channels',
    'channels_added': '✅ Channels added: {channels}',
    
    'add_time_usage': '❌ Invalid format. Use:\n/add_time 6h/12h/1d\n/add_time @channel DD.MM.YYYY HH:MM to DD.MM.YYYY HH:MM',
    'channel_not_found': '❌ Channel {channel} not found',
    'time_set': '✅ For channel {channel} verification time set\nfrom {start}\nto {end}',
    'time_set_all': '✅ For all active channels verification time set\nuntil {end}',
    
    'auto_del_usage': '❌ Use format: 15s, 30s, 5m, 10m',
    'auto_del_range': '❌ Time must be from {min}s to {max}m',
    'auto_del_set': '✅ Auto-deletion set to {time}',
    
    'del_one_usage': '❌ Usage: /del_one @channel',
    'channel_deleted': '✅ Channel {channel} removed from verification',
    
    'channels_deleted': '✅ Deleted {count} channels from verification',
    
    # Status
    'status_header': '📊 **GROUP STATUS:** {group_title}\n\n',
    'channels_header': '🔹 **CHANNELS UNDER VERIFICATION:**\n',
    'no_channels': '   • No channels\n',
    'channel_item': '   • {channel} ({end})\n',
    'permanent': 'permanent',
    'until': 'until {date}',
    
    'vip_header': '\n🔹 **VIP USERS:**\n',
    'no_vip': '   • No VIP users\n',
    'vip_item': '   • {username} - {type} ({scope}, {end})\n',
    'vip_type_vip': '💎 VIP',
    'vip_type_plus': '👑 VIP PLUS',
    'scope_global': 'global',
    'scope_local': 'local',
    
    'mute_header': '\n🔹 **MUTED USERS:**\n',
    'no_mutes': '   • No muted users\n',
    'mute_item': '   • {username} - {hours}h {minutes}m left\n',
    
    'auto_del_status': '\n🔹 **AUTO-DELETION:** {time}s\n',
    
    # Subscription warnings
    'subscription_warning': '@{username}, you are not subscribed to channels: {channels}\nSubscribe to write in the chat!',
    'subscribe_button': '📢 Subscribe to {channel}',
    'vip_button': '💎 VIP subscription',
    
    # Blacklist and mutes
    'blacklist_warning': '@{username}, commands are only available to administrators! This is a warning. You will be muted on repeat.',
    'mute_message': '@{username}, you have been muted for {time} for using commands not as intended!',
    'mute_time_format': '{hours}h {minutes}m',
    
    'no_active_mutes': '✅ No active mutes',
    'mutes_header': '🔇 **ACTIVE MUTES:**\n\n',
    'mute_info': '🔹 {username}\n   Violations: {violations}\n   Left: {hours}h {minutes}m\n   Until: {end}\n\n',
    
    'mute_removed': '✅ Mute removed from {username}',
    'mute_not_found': '❌ Mute not found for {username}',
    'mutes_cleared': '✅ Cleared {count} mutes',
    
    # VIP management
    'user_not_found': '❌ User not found',
    'vip_added_global': '✅ Global VIP added for {username}',
    'vip_plus_added_global': '✅ Global VIP PLUS added for {username}',
    'vip_limit_reached': '❌ User has already reached the group limit for VIP (max 1)',
    'vip_plus_limit_reached': '❌ User has already reached the group limit for VIP PLUS (max 3)',
    'vip_added_local': '✅ Local VIP added for {username} in group {group}',
    'vip_time_set': '✅ VIP for {username} set until {date}',
    'vip_removed': '✅ VIP removed from {username}',
    'vip_plus_removed': '✅ VIP PLUS removed from {username}',
    'vip_all_removed': '✅ Removed {count} VIP users',
    'vip_plus_all_removed': '✅ Removed {count} VIP PLUS users',
    
    # User notifications
    'vip_granted_global': '🎉 You have been granted **global VIP status**!\n\n{features}',
    'vip_plus_granted_global': '👑 You have been granted **global VIP PLUS status**!\n\n{features}',
    'vip_granted_local': '🎉 You have been granted **local VIP status** in group {group}!\n\n{features}',
    
    # VIP status for user
    'vip_no_active': '❌ No active VIP subscription',
    'vip_status_header': '✨ **{type} status active** ✨\n\n',
    'vip_features_header': '🔹 **Available features:**\n',
    'vip_feature_3groups': '✅ Access to 3 groups simultaneously\n',
    'vip_feature_mute_immunity': '✅ Immunity to mutes\n',
    'vip_feature_antiflood': '✅ Anti-flood protection\n',
    'vip_feature_unlimited_media': '✅ Unlimited media files\n',
    'vip_feature_stats': '✅ Statistics access\n',
    'vip_feature_commands': '✅ Custom commands (up to 3)\n',
    'vip_feature_contests': '\n✅ Participation in contests',
    
    # VIP commands (added)
    'add_vip_usage': '❌ Usage: /add_VIP @user',
    'add_vip_plus_usage': '❌ Usage: /ad_VIP_PLUS @user',
    'add_vip_local_usage': '❌ Usage: /add_VIP_local @group @user',
    'add_vip_time_usage': '❌ Usage: /add_VIP_time @user 7d/30d',
    'del_vip_usage': '❌ Usage: /del_VIP @user',
    'del_vip_plus_usage': '❌ Usage: /del_VIPPLUS @user',
    'group_or_user_not_found': '❌ Group or user not found',
    'invalid_time_format': '❌ Invalid time format. Use: 7d, 30d',
    'vip_not_found': '❌ VIP not found for {username}',
    'vip_plus_not_found': '❌ VIP PLUS not found for {username}',
    
    # Mute commands (added)
    'off_mute_usage': '❌ Usage: /off_mute @user',
    
    # Errors
    'error_occurred': '❌ Error: {error}',
    
    # Buttons
    'button_confirm': '✅ Confirm',
    'button_cancel': '❌ Cancel',
    'button_subscribe': '📢 Subscribe',
    
    # Language
    'language_set': '✅ Language changed to English',
    'language_usage': '❌ Usage: /language ru/en',
}