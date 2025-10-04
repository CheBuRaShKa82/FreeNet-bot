# keyboards/inline_keyboards.py

from telebot import types
import logging

logger = logging.getLogger(__name__)

# --- Функции клавиатуры администратора ---

def get_admin_main_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚙️ Управление серверами", callback_data="admin_server_management"),
        types.InlineKeyboardButton("💰 Управление планами", callback_data="admin_plan_management"),
        types.InlineKeyboardButton("💳 Управление шлюзами", callback_data="admin_payment_management"),
        types.InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_user_management"),
        types.InlineKeyboardButton("🔗 Управление блокировкой канала", callback_data="admin_channel_lock_management"),
        types.InlineKeyboardButton("📊 Панель управления", callback_data="admin_dashboard"),
        types.InlineKeyboardButton("💡 Управление инструкциями", callback_data="admin_tutorial_management"),
        types.InlineKeyboardButton("📞 Управление поддержкой", callback_data="admin_support_management"),
        types.InlineKeyboardButton("🗂️ Управление профилями", callback_data="admin_profile_management"),
        types.InlineKeyboardButton("🌐 Управление доменами", callback_data="admin_domain_management"),
        types.InlineKeyboardButton("⚙️ Проверить Nginx", callback_data="admin_check_nginx"),
        types.InlineKeyboardButton("🩺 Проверка состояния системы", callback_data="admin_health_check"),
        types.InlineKeyboardButton("👁️ Просмотр состояния БД", callback_data="admin_view_profile_db"),
        types.InlineKeyboardButton("🔧 Проверить ссылки подписки", callback_data="admin_check_subscription_links"),
        types.InlineKeyboardButton("🔄 Обновить все ссылки", callback_data="admin_refresh_all_subscriptions"),
        types.InlineKeyboardButton("📊 Состояние системы подписок", callback_data="admin_subscription_system_status"),
        types.InlineKeyboardButton("🧪 Тест конструктора конфигов", callback_data="admin_test_config_builder"),
        types.InlineKeyboardButton("🔧 Создать конфиг", callback_data="admin_create_config_menu"),
        types.InlineKeyboardButton("📋 Полный JSON лог", callback_data="admin_log_full_json"),
        types.InlineKeyboardButton("🔑 Настроить API Key", callback_data="admin_set_api_key"),
        types.InlineKeyboardButton("🎨 Настройки брендинга", callback_data="admin_branding_settings"),
        types.InlineKeyboardButton("✍️ Управление сообщениями", callback_data="admin_message_management"),
        types.InlineKeyboardButton("⚙️ Настройка Webhook и домена", callback_data="admin_webhook_setup"),
        types.InlineKeyboardButton("📣 Массовая рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🗄 Создать резервную копию", callback_data="admin_create_backup")
    )
    return markup

def get_server_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить сервер", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📝 Список серверов", callback_data="admin_list_servers"),
        types.InlineKeyboardButton("🔌 Управление Inbounds", callback_data="admin_manage_inbounds"),
        types.InlineKeyboardButton("🔄 Тестировать все серверы", callback_data="admin_test_all_servers"),
        types.InlineKeyboardButton("❌ Удалить сервер", callback_data="admin_delete_server"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return markup
    
def get_plan_management_inline_menu():
    """ --- MODIFIED: Added Edit and Delete buttons --- """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить план", callback_data="admin_add_plan"),
        types.InlineKeyboardButton("📝 Список планов", callback_data="admin_list_plans"),
        types.InlineKeyboardButton("✏️ Редактировать план", callback_data="admin_edit_plan"), # <-- NEW
        types.InlineKeyboardButton("❌ Удалить план", callback_data="admin_delete_plan"),     # <-- NEW
        types.InlineKeyboardButton("🔄 Изменить статус плана", callback_data="admin_toggle_plan_status"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return markup

def get_payment_gateway_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить шлюз", callback_data="admin_add_gateway"),
        types.InlineKeyboardButton("📝 Список шлюзов", callback_data="admin_list_gateways"),
        types.InlineKeyboardButton("🔄 Изменить статус шлюза", callback_data="admin_toggle_gateway_status"),
        types.InlineKeyboardButton("✏️ Редактировать шлюз", callback_data="admin_edit_gateway"),
        types.InlineKeyboardButton("🗑️ Удалить шлюз", callback_data="admin_delete_gateway"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return markup
    
def get_user_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 Список всех пользователей", callback_data="admin_list_users"),
        types.InlineKeyboardButton("🔎 Поиск пользователя", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return markup

def get_plan_type_selection_menu_admin():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Месячный (Фиксированный)", callback_data="plan_type_fixed_monthly"),
        types.InlineKeyboardButton("По объему (Гигабайты)", callback_data="plan_type_gigabyte_based"),
        types.InlineKeyboardButton("🔙 Отмена", callback_data="admin_plan_management")
    )
    return markup
    
    
def get_inbound_selection_menu(server_id: int, panel_inbounds: list, active_inbound_ids: list):
    """
    Меню выбора инбаундов с трюком анти-кэша для обеспечения обновления.
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Выбрать все", callback_data=f"inbound_select_all_{server_id}"),
        types.InlineKeyboardButton("⬜️ Снять выделение со всех", callback_data=f"inbound_deselect_all_{server_id}")
    )

    for inbound in panel_inbounds:
        inbound_id = inbound['id']
        is_active = inbound_id in active_inbound_ids
        emoji = "✅" if is_active else "⬜️"
        button_text = f"{emoji} {inbound.get('remark', f'Инбаунд {inbound_id}')}"
        
        # --- Основной трюк ---
        # Добавляем дополнительный параметр (is_active) в callback_data
        # Это делает callback_data разным в каждом состоянии (активен/неактивен)
        callback_data = f"inbound_toggle_{server_id}_{inbound_id}_{1 if is_active else 0}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_server_management"),
        types.InlineKeyboardButton("✔️ Сохранить изменения", callback_data=f"inbound_save_{server_id}")
    )
    return markup

def get_confirmation_menu(confirm_callback: str, cancel_callback: str, confirm_text="✅ Да", cancel_text="❌ Нет"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
        types.InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
    )
    return markup

# --- Функции клавиатуры пользователя ---

def get_user_main_inline_menu(support_link: str):
    """ --- Обновленная версия с кнопкой профиля --- """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Купить обычный сервис", callback_data="user_buy_service"),
        types.InlineKeyboardButton("🗂️ Купить профиль", callback_data="user_buy_profile"),
        types.InlineKeyboardButton("🎁 Бесплатный тестовый аккаунт", callback_data="user_free_test"),
        types.InlineKeyboardButton("🗂️ Мои сервисы", callback_data="user_my_services"),
        types.InlineKeyboardButton("👤 Мой аккаунт", callback_data="user_account"),
        types.InlineKeyboardButton("💡 Инструкция по подключению", callback_data="user_how_to_connect")
    )

    if support_link and support_link.startswith('http'):
        markup.add(types.InlineKeyboardButton("📞 Поддержка", url=support_link))
        
    return markup
    
def get_back_button(callback_data: str, text: str = "🔙 Назад"):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))
    return markup

def get_server_selection_menu(servers: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for server in servers:
        markup.add(types.InlineKeyboardButton(server['name'], callback_data=f"buy_select_server_{server['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="user_main_menu"))
    return markup
    
def get_plan_type_selection_menu_user(server_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Месячный (Фиксированный)", callback_data="buy_plan_type_fixed_monthly"),
        types.InlineKeyboardButton("По объему (Гигабайты)", callback_data="buy_plan_type_gigabyte_based")
    )
    markup.add(get_back_button(f"user_buy_service").keyboard[0][0]) # Add back button
    return markup

def get_fixed_plan_selection_menu(plans: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for plan in plans:
        button_text = f"{plan['name']} - {plan['volume_gb']:.1f} ГБ / {plan['duration_days']} дней - {plan['price']:,.0f} руб."
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_select_plan_{plan['id']}"))
    markup.add(get_back_button("user_buy_service").keyboard[0][0]) # Назад к выбору сервера
    return markup
    
def get_order_confirmation_menu():
    return get_confirmation_menu(
        confirm_callback="confirm_and_pay",
        cancel_callback="cancel_order",
        confirm_text="✅ Подтвердить и оплатить",
        cancel_text="❌ Отмена"
    )

def get_payment_gateway_selection_menu(gateways: list, wallet_balance: float = 0, order_price: float = 0):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # --- Новая логика для отображения кнопки кошелька ---
    if wallet_balance >= order_price:
        balance_str = f"{wallet_balance:,.0f}"
        btn_text = f"💳 Оплатить с кошелька (баланс: {balance_str} руб.)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data="pay_with_wallet"))

    # Отображение остальных шлюзов
    for gateway in gateways:
        markup.add(types.InlineKeyboardButton(gateway['name'], callback_data=f"select_gateway_{gateway['id']}"))
        
    markup.add(types.InlineKeyboardButton("🔙 Назад к информации о заказе", callback_data="show_order_summary"))
    return markup
    
def get_admin_payment_action_menu(payment_id: int):
    return get_confirmation_menu(
        confirm_callback=f"admin_approve_payment_{payment_id}",
        cancel_callback=f"admin_reject_payment_{payment_id}",
        confirm_text="✅ Подтвердить платеж",
        cancel_text="❌ Отклонить"
    )
    
def get_single_configs_button(purchase_id: int):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📄 Получить отдельные конфиги", callback_data=f"user_get_single_configs_{purchase_id}"))
    return markup

def get_my_services_menu(purchases: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not purchases:
        markup.add(types.InlineKeyboardButton("У вас нет активных сервисов", callback_data="no_action"))
    else:
        for p in purchases:
            status_emoji = "✅" if p['is_active'] else "❌"
            
            # --- THE FIX IS HERE ---
            if p['expire_date']:
                # First, format the datetime object into a YYYY-MM-DD string
                expire_date_str = p['expire_date'].strftime('%Y-%m-%d')
            else:
                expire_date_str = "Безлимитный"
            # --- End of fix ---

            btn_text = f"{status_emoji} Сервис {p['id']} ({p.get('server_name', 'N/A')}) - Истекает: {expire_date_str}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"user_service_details_{p['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад в главное меню", callback_data="user_main_menu"))
    return markup



# В файле keyboards/inline_keyboards.py





def get_gateway_type_selection_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 Карта на карту", callback_data="gateway_type_card_to_card"),
        types.InlineKeyboardButton("🟢 Zarinpal", callback_data="gateway_type_zarinpal")
    )
    markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="admin_payment_management"))
    return markup


def get_channel_lock_management_menu(channel_set: bool):
    """Creates the menu for managing the required channel."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ Установить/Изменить канал", callback_data="admin_set_channel_lock"))
    if channel_set:
        markup.add(types.InlineKeyboardButton("❌ Снять блокировку канала", callback_data="admin_remove_channel_lock"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup

def get_user_management_menu():
    """Creates the main menu for user management."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔎 Поиск пользователя", callback_data="admin_search_user"))
    # Add more user management options here later if needed
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup

def get_user_subscriptions_management_menu(db_manager, purchases: list, user_telegram_id: int):
    """
    --- MODIFIED: Accepts db_manager as a parameter to fetch server names ---
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not purchases:
        markup.add(types.InlineKeyboardButton("У этого пользователя нет активных подписок", callback_data="no_action"))
    else:
        for p in purchases:
            # Now we use the passed db_manager to get server info
            server = db_manager.get_server_by_id(p['server_id'])
            server_name = server['name'] if server else "N/A"
            expire_str = p['expire_date'][:10] if p['expire_date'] else "Безлимитный"
            btn_text = f"❌ Удалить сервис {p['id']} ({server_name} - {expire_str})"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_purchase_{p['id']}_{user_telegram_id}"))
            
    markup.add(types.InlineKeyboardButton("🔙 Назад к управлению пользователями", callback_data="admin_user_management"))
    return markup


def get_join_channel_keyboard(channel_link: str):
    """
    --- NEW: Creates the keyboard for the channel lock message ---
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Button to join the channel (as a URL)
    markup.add(types.InlineKeyboardButton("🚀 Вступить в канал", url=channel_link))
    # Button to check membership status again
    markup.add(types.InlineKeyboardButton("✅ Я вступил, проверить снова", callback_data="user_check_join_status"))
    return markup



def get_tutorial_management_menu():
    """Creates the menu for managing tutorials."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Добавить инструкцию", callback_data="admin_add_tutorial"))
    markup.add(types.InlineKeyboardButton("📝 Список и удаление инструкций", callback_data="admin_list_tutorials"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup

def get_tutorials_list_menu(tutorials: list):
    """Displays a list of tutorials with delete buttons."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not tutorials:
        markup.add(types.InlineKeyboardButton("Инструкций не найдено", callback_data="no_action"))
    else:
        for t in tutorials:
            btn_text = f"❌ Удалить: {t['platform']} - {t['app_name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_tutorial_{t['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_tutorial_management"))
    return markup

def get_platforms_menu(platforms: list):
    """Creates a menu for users to select a platform."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(p, callback_data=f"user_select_platform_{p}") for p in platforms]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="user_main_menu"))
    return markup

def get_apps_for_platform_menu(tutorials: list, platform: str):
    """Creates a menu for users to select an app for a specific platform."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in tutorials:
        markup.add(types.InlineKeyboardButton(t['app_name'], callback_data=f"user_select_tutorial_{t['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад к платформам", callback_data="user_how_to_connect"))
    return markup



def get_support_management_menu(): # The 'support_type' argument has been removed
    """--- SIMPLIFIED: Creates a simple menu for setting the support link ---"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ Установить/Изменить ссылку поддержки", callback_data="admin_edit_support_link"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup




def get_panel_type_selection_menu():
    """Создает клавиатуру для выбора типа панели при добавлении нового сервера."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("3x-ui (стандарт)", callback_data="panel_type_x-ui"),
        types.InlineKeyboardButton("Alireza-x-ui", callback_data="panel_type_alireza"),
        # types.InlineKeyboardButton("Hiddify", callback_data="panel_type_hiddify"), # на будущее
        types.InlineKeyboardButton("🔙 Отмена", callback_data="admin_server_management")
    )
    return markup



def get_profile_management_inline_menu():
    """Создает главное меню для управления профилями."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить профиль", callback_data="admin_add_profile"),
        types.InlineKeyboardButton("📝 Список профилей", callback_data="admin_list_profiles"),
        types.InlineKeyboardButton("🔗 Управление инбаундами профиля", callback_data="admin_manage_profile_inbounds"),
        types.InlineKeyboardButton("❌ Удалить профиль", callback_data="admin_delete_profile"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
    )
    return markup



def get_profile_selection_menu(profiles):
    """Создает меню для выбора из существующих профилей."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for profile in profiles:
        btn_text = f"🗂️ {profile['name']} (ID: {profile['id']})"
        callback_data = f"admin_select_profile_{profile['id']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_profile_management"))
    return markup


def get_server_selection_menu_for_profile(servers, profile_id):
    """Создает меню для выбора сервера для добавления инбаунда в профиль."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for server in servers:
        btn_text = f"⚙️ {server['name']} (ID: {server['id']})"
        # Мы также передаем ID профиля в callback_data, чтобы иметь к нему доступ на следующем шаге
        callback_data = f"admin_ps_{profile_id}_{server['id']}" # ps = Profile Server
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад к выбору профиля", callback_data="admin_manage_profile_inbounds"))
    return markup



def get_inbound_selection_menu_for_profile(profile_id, server_id, panel_inbounds, selected_inbound_ids):
    """Создает меню-чеклист для выбора инбаундов для определенного профиля."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for inbound in panel_inbounds:
        inbound_id = inbound['id']
        is_selected = inbound_id in selected_inbound_ids
        emoji = "✅" if is_selected else "⬜️"
        button_text = f"{emoji} {inbound.get('remark', f'Инбаунд {inbound_id}')}"
        
        # callback_data включает ID профиля, сервера и инбаунда
        callback_data = f"admin_pi_toggle_{profile_id}_{server_id}_{inbound_id}" # pi = Profile Inbound
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
    markup.add(
        types.InlineKeyboardButton("✔️ Сохранить изменения для этого сервера", callback_data=f"admin_pi_save_{profile_id}_{server_id}")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад к выбору сервера", callback_data=f"admin_select_profile_{profile_id}"))
    return markup



def get_profile_selection_menu_for_user(profiles):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for profile in profiles:
        btn_text = f"🗂️ {profile['name']} (Цена за ГБ: {profile['per_gb_price']:,.0f} руб.)"
        callback_data = f"buy_select_profile_{profile['id']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад в меню", callback_data="user_main_menu"))
    return markup




def get_domain_management_menu(domains):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ Добавить новый домен", callback_data="admin_add_domain"))
    
    if domains:
        markup.add(types.InlineKeyboardButton("--- Зарегистрированные домены ---", callback_data="no_action"))
        for domain in domains:
            status = " (Активен ✅)" if domain['is_active'] else ""
            ssl_emoji = "🌐" if domain.get('ssl_status') else "⚠️"
            
            btn_text_activate = f"{ssl_emoji} Активировать: {domain['domain_name']}{status}"
            btn_text_delete = "❌ Удалить"
            
            markup.add(
                types.InlineKeyboardButton(btn_text_activate, callback_data=f"admin_activate_domain_{domain['id']}"),
                types.InlineKeyboardButton(btn_text_delete, callback_data=f"admin_delete_domain_{domain['id']}")
            )

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup


def get_admin_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add_admin"),
        types.InlineKeyboardButton("❌ Удалить админа", callback_data="admin_remove_admin")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup


def get_template_management_menu(all_active_inbounds):
    """
    Создает меню управления шаблонами с отображением статуса каждого инбаунда.
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_active_inbounds:
        markup.add(types.InlineKeyboardButton("Активных инбаундов не найдено", callback_data="no_action"))
    else:
        for inbound in all_active_inbounds:
            status_emoji = "✅" if inbound.get('config_params') else "⚠️"
            
            # --- Основное исправление сделано в этой строке ---
            inbound_remark = inbound.get('remark', f"ID: {inbound['inbound_id']}")
            
            btn_text = (
                f"{status_emoji} {inbound['server_name']} - {inbound_remark}"
            )
            # callback_data содержит ID сервера и инбаунда, чтобы мы знали, какой шаблон редактировать
            callback_data = f"admin_edit_template_{inbound['server_id']}_{inbound['inbound_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
            
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_server_management"))
    return markup


def get_profile_template_management_menu(all_profile_inbounds):
    """
    Создает меню управления шаблонами для профилей.
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_profile_inbounds:
        markup.add(types.InlineKeyboardButton("К профилям не подключено ни одного инбаунда", callback_data="no_action"))
    else:
        current_profile = None
        for inbound in all_profile_inbounds:
            # Для читаемости отображаем имя профиля в качестве заголовка
            if current_profile != inbound['profile_name']:
                current_profile = inbound['profile_name']
                markup.add(types.InlineKeyboardButton(f"--- Профиль: {current_profile} ---", callback_data="no_action"))

            status_emoji = "✅" if inbound.get('config_params') else "⚠️"
            
            # --- Основное исправление сделано в этих двух строках ---
            inbound_remark = inbound.get('remark', f"ID: {inbound['inbound_id']}")
            btn_text = (
                f"{status_emoji} {inbound['server_name']} - {inbound_remark}"
            )
            
            callback_data = f"admin_edit_profile_template_{inbound['profile_id']}_{inbound['server_id']}_{inbound['inbound_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
            
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_profile_management"))
    return markup



def get_user_account_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Пополнить баланс", callback_data="user_add_balance"),
        types.InlineKeyboardButton("📝 Заполнить профиль", callback_data="user_complete_profile")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад в главное меню", callback_data="user_main_menu"))
    return markup


def get_message_management_menu(messages_on_page, current_page, total_pages):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for msg in messages_on_page:
        preview_text = msg['message_text'][:30].replace('\n', ' ') + "..."
        btn_text = f"✏️ {msg['message_key']} | {preview_text}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_edit_msg_{msg['message_key']}"))
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_msg_page_{current_page - 1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="no_action"))
    if current_page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_msg_page_{current_page + 1}"))
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)
        
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
    return markup


def get_manage_user_menu(user_telegram_id):
    """Создает панель управления для конкретного пользователя."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Изменить роль", callback_data=f"admin_change_role_{user_telegram_id}"),
        types.InlineKeyboardButton("💰 Настроить баланс", callback_data=f"admin_adjust_balance_{user_telegram_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🗂️ Просмотр подписок", callback_data=f"admin_view_subs_{user_telegram_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_user_management")
    )
    return markup


def get_change_role_menu(user_telegram_id):
    """Создает меню для выбора новой роли для пользователя."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    roles = {
        'admin': '👑 Администратор',
        'reseller': '🤝 Реселлер',
        'user': '👤 Пользователь'
    }
    for role_key, role_name in roles.items():
        markup.add(types.InlineKeyboardButton(
            f"Установить как: {role_name}", 
            callback_data=f"admin_set_role_{user_telegram_id}_{role_key}"
        ))

    # Кнопка возврата в панель управления этого же пользователя
    # Мы определяем новый callback для этого
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_manage_user_{user_telegram_id}"))
    return markup

def get_admin_subs_list_menu(user_telegram_id):
    """Создает кнопку возврата в панель управления конкретного пользователя."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(
        "🔙 Назад в панель пользователя", 
        callback_data=f"admin_manage_user_{user_telegram_id}"
    ))
    return markup


def get_broadcast_confirmation_menu():
    """Создает клавиатуру окончательного подтверждения для массовой рассылки."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Отправить", callback_data="admin_confirm_broadcast"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel_broadcast")
    )
    return markup


def get_gateway_selection_menu_for_edit(gateways: list):
    """Меню выбора шлюза для редактирования"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not gateways:
        markup.add(types.InlineKeyboardButton("❌ Шлюзы не найдены", callback_data="no_action"))
    else:
        for gateway in gateways:
            status_emoji = "✅" if gateway.get('is_active', False) else "❌"
            gateway_type_emoji = "💳" if gateway.get('type') == 'card_to_card' else "🟢"
            btn_text = f"{status_emoji} {gateway_type_emoji} {gateway['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_edit_gateway_{gateway['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_payment_management"))
    return markup


def get_gateway_selection_menu_for_delete(gateways: list):
    """Меню выбора шлюза для удаления"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not gateways:
        markup.add(types.InlineKeyboardButton("❌ Шлюзы не найдены", callback_data="no_action"))
    else:
        for gateway in gateways:
            status_emoji = "✅" if gateway.get('is_active', False) else "❌"
            gateway_type_emoji = "💳" if gateway.get('type') == 'card_to_card' else "🟢"
            btn_text = f"{status_emoji} {gateway_type_emoji} {gateway['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_gateway_{gateway['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_payment_management"))
    return markup


def get_gateway_delete_confirmation_menu(gateway_id: int, gateway_name: str):
    """Меню подтверждения удаления шлюза"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"admin_confirm_delete_gateway_{gateway_id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="admin_payment_management")
    )
    return markup


def get_user_purchases_menu(purchases):
    """Меню покупок пользователя"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for purchase in purchases:
        # Отображение информации о покупке
        purchase_info = f"📦 {purchase['id']} - {purchase.get('server_name', 'N/A')}"
        if purchase.get('expire_date'):
            from datetime import datetime
            expire_date = purchase['expire_date']
            if isinstance(expire_date, str):
                expire_date = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
            days_left = (expire_date - datetime.now()).days
            status = "✅ Активен" if days_left > 0 else "❌ Истек"
            purchase_info += f" ({status})"
        
        # Кнопки действий
        markup.add(
            types.InlineKeyboardButton(
                purchase_info, 
                callback_data=f"admin_view_purchase_{purchase['id']}"
            )
        )
        
        # Дополнительные кнопки
        markup.add(
            types.InlineKeyboardButton(
                "🔄 Обновить конфиг", 
                callback_data=f"admin_update_configs_{purchase['id']}"
            ),
            types.InlineKeyboardButton(
                "📊 Детали", 
                callback_data=f"admin_purchase_details_{purchase['id']}"
            )
        )
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_user_management"))
    return markup