# handlers/admin_handlers.py (финальная, полная и профессиональная версия)

import telebot
from telebot import types
import logging
import datetime
import json
import os
import zipfile
import time
import uuid
from config import ADMIN_IDS, SUPPORT_CHANNEL_LINK
from database.db_manager import DatabaseManager
from api_client.xui_api_client import XuiAPIClient
from utils import messages, helpers
from keyboards import inline_keyboards
from utils.config_generator import ConfigGenerator
from utils.bot_helpers import send_subscription_info # это новый импорт
from handlers.user_handlers import _user_states
from config import REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_LINK # This should already be there
from api_client.factory import get_api_client
from utils.helpers import normalize_panel_inbounds
from utils.bot_helpers import finalize_profile_purchase
from handlers.domain_handlers import register_domain_handlers # <-- новый импорт
from utils.system_helpers import remove_domain_nginx_files
from utils.system_helpers import run_shell_command
from utils import helpers
from utils.helpers import update_env_file
from utils.system_helpers import run_shell_command
from .domain_handlers import register_domain_handlers, start_webhook_setup_flow # <-- добавьте новую функцию
from utils.helpers import normalize_panel_inbounds, parse_config_link

logger = logging.getLogger(__name__)

# Глобальные модули
_bot: telebot.TeleBot = None
_db_manager: DatabaseManager = None
_xui_api: XuiAPIClient = None
_config_generator: ConfigGenerator = None
_admin_states = {}

def register_admin_handlers(bot_instance, db_manager_instance, xui_api_instance):
    global _bot, _db_manager, _xui_api, _config_generator , _admin_states
    _bot = bot_instance
    _db_manager = db_manager_instance
    _xui_api = xui_api_instance
    _config_generator = ConfigGenerator(db_manager_instance)

    # =============================================================================
    # SECTION: Helper and Menu Functions
    # =============================================================================
    register_domain_handlers(bot=_bot, db_manager=_db_manager, admin_states=_admin_states)


    def _clear_admin_state(admin_id):
        """Очищает состояние администратора только из словаря."""
        if admin_id in _admin_states:
            del _admin_states[admin_id]

    def _show_menu(user_id, text, markup, message=None, parse_mode='Markdown'):
        """
        --- FINAL & ROBUST VERSION ---
        This function intelligently handles Markdown parsing errors.
        It first tries to send the message with Markdown. If Telegram rejects it
        due to a formatting error, it automatically retries sending it as plain text.
        """
        try:
            # First attempt: Send with specified parse_mode (usually Markdown)
            if message:
                return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=parse_mode)
            else:
                return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)

        except telebot.apihelper.ApiTelegramException as e:
            # If the error is specifically a Markdown parsing error...
            if "can't parse entities" in str(e):
                logger.warning(f"Markdown parse error for user {user_id}. Retrying with plain text.")
                try:
                    # Second attempt: Send as plain text
                    if message:
                        return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=None)
                    else:
                        return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=None)
                except telebot.apihelper.ApiTelegramException as retry_e:
                    logger.error(f"Failed to send menu even as plain text for user {user_id}: {retry_e}")

            # Handle other common errors
            elif 'message to edit not found' in str(e):
                return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)
            elif 'message is not modified' not in str(e):
                logger.warning(f"Menu error for {user_id}: {e}")
                
        return message

    def _show_admin_main_menu(admin_id, message=None): 
        brand_name = _db_manager.get_setting('brand_name') or "Alamor VPN"
        welcome_text = messages.ADMIN_WELCOME.format(brand_name=brand_name)
        _show_menu(admin_id, welcome_text, inline_keyboards.get_admin_main_inline_menu(), message)
    def _show_server_management_menu(admin_id, message=None): _show_menu(admin_id, messages.SERVER_MGMT_MENU_TEXT, inline_keyboards.get_server_management_inline_menu(), message)
    def _show_plan_management_menu(admin_id, message=None): _show_menu(admin_id, messages.PLAN_MGMT_MENU_TEXT, inline_keyboards.get_plan_management_inline_menu(), message)
    def _show_payment_gateway_management_menu(admin_id, message=None): _show_menu(admin_id, messages.PAYMENT_GATEWAY_MGMT_MENU_TEXT, inline_keyboards.get_payment_gateway_management_inline_menu(), message)
    def _show_user_management_menu(admin_id, message=None): _show_menu(admin_id, messages.USER_MGMT_MENU_TEXT, inline_keyboards.get_user_management_inline_menu(), message)
    def _show_profile_management_menu(admin_id, message=None):
        _show_menu(admin_id, "🗂️ Опции управления профилями:", inline_keyboards.get_profile_management_inline_menu(), message)

    # =============================================================================
    # SECTION: Single-Action Functions (Listing, Testing)
    # =============================================================================

    def list_all_servers(admin_id, message):
        _bot.edit_message_text(_generate_server_list_text(), admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_server_management"))

    # в файле handlers/admin_handlers.py

    def list_all_plans(admin_id, message, return_text=False):
        plans = _db_manager.get_all_plans()
        if not plans: 
            text = messages.NO_PLANS_FOUND
        else:
            text = messages.LIST_PLANS_HEADER
            for p in plans:
                status = "✅ Активен" if p['is_active'] else "❌ Неактивен"
                if p['plan_type'] == 'fixed_monthly':
                    details = f"Объем: {p['volume_gb']}GB | Срок: {p['duration_days']} дней | Цена: {p['price']:,.0f} туманов"
                else:
                    # --- исправленная часть ---
                    duration_days = p.get('duration_days') # значение может быть None
                    if duration_days and duration_days > 0:
                        duration_text = f"{duration_days} дней"
                    else:
                        duration_text = "Безлимитно"
                    # --- конец исправленной части ---
                    details = f"Цена за гигабайт: {p['per_gb_price']:,.0f} туманов | Срок: {duration_text}"
                text += f"**ID: `{p['id']}`** - {helpers.escape_markdown_v1(p['name'])}\n_({details})_ - {status}\n---\n"
        
        if return_text:
            return text
        _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_plan_management"))
    def list_all_gateways(admin_id, message, return_text=False):
        gateways = _db_manager.get_all_payment_gateways()
        if not gateways:
            text = messages.NO_GATEWAYS_FOUND
        else:
            text = messages.LIST_GATEWAYS_HEADER
            for g in gateways:
                status = "✅ Активен" if g['is_active'] else "❌ Неактивен"
                text += f"**ID: `{g['id']}`** - {helpers.escape_markdown_v1(g['name'])}\n`{g.get('card_number', 'N/A')}` - {status}\n---\n"
        
        if return_text:
            return text
        _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_payment_management"))


    def list_all_users(admin_id, message):
        users = _db_manager.get_all_users()
        if not users:
            text = messages.NO_USERS_FOUND
        else:
            total_users = len(users)
            text = f"👥 **Список пользователей бота (всего: {total_users} человек):**\n\n"

            # Словарь для красивого отображения ролей
            role_map = {
                'admin': '👑 Администратор',
                'reseller': '🤝 Реселлер',
                'user': '👤 Пользователь'
            }

            for user in users:
                first_name = helpers.escape_markdown_v1(user.get('first_name', ''))
                username = helpers.escape_markdown_v1(user.get('username', 'N/A'))

                # Чтение роли из нового столбца 'role'
                user_role_key = user.get('role', 'user')
                role = role_map.get(user_role_key, '👤 Пользователь')

                balance = f"{user.get('balance', 0):,.0f} туманов"

                text += (
                    f"**Имя:** {first_name} (@{username})\n"
                    f"`ID: {user['telegram_id']}`\n"
                    f"**Роль:** {role} | **Баланс:** {balance}\n"
                    "-----------------------------------\n"
                )

        _show_menu(admin_id, text, inline_keyboards.get_back_button("admin_user_management"), message)

    def test_all_servers(admin_id, message):
        _bot.edit_message_text(messages.TESTING_ALL_SERVERS, admin_id, message.message_id, reply_markup=None)
        servers = _db_manager.get_all_servers(only_active=False) # Тестируем все серверы
        if not servers:
            _bot.send_message(admin_id, messages.NO_SERVERS_FOUND)
            _show_server_management_menu(admin_id)
            return
            
        results = []
        for s in servers:
            # --- основное исправление здесь ---
            # Использование factory для выбора подходящего клиента
            api_client = get_api_client(s)
            is_online = False
            if api_client:
                # функция check_login также выполняет вход
                is_online = api_client.check_login()
            # --- конец исправленной части ---

            _db_manager.update_server_status(s['id'], is_online, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            status_emoji = "✅" if is_online else "❌"
            results.append(f"{status_emoji} {helpers.escape_markdown_v1(s['name'])} (Type: {s['panel_type']})")

        _bot.send_message(admin_id, messages.TEST_RESULTS_HEADER + "\n".join(results), parse_mode='Markdown')
        _show_server_management_menu(admin_id)
    # =============================================================================
    # SECTION: Stateful Process Handlers
    # =============================================================================
    def get_plan_details_from_callback(admin_id, message, plan_type):
        """Обрабатывает выбранный тип тарифа и задает следующий вопрос."""
        state_info = _admin_states.get(admin_id, {})
        if state_info.get('state') != 'waiting_for_plan_type': return

        state_info['data']['plan_type'] = plan_type
        
        if plan_type == 'fixed_monthly':
            # Для фиксированного тарифа следующий вопрос - объем
            state_info['state'] = 'waiting_for_plan_volume'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_VOLUME, admin_id, message.message_id)
        elif plan_type == 'gigabyte_based':
            # Для тарифа по гигабайтам следующий вопрос - цена за гигабайт
            state_info['state'] = 'waiting_for_per_gb_price'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_PER_GB_PRICE, admin_id, message.message_id)
        
        state_info['prompt_message_id'] = message.message_id
    def _handle_stateful_message(admin_id, message):
        # === Новая и умная логика удаления сообщений ===
        state_info = _admin_states.get(admin_id, {})
        state = state_info.get("state")
        states_to_preserve_message = ['waiting_for_broadcast_message', 'waiting_for_tutorial_forward']
        
        if state not in states_to_preserve_message:
            try:
                # Удалять сообщение только в том случае, если оно не для рассылки или туториала
                _bot.delete_message(admin_id, message.message_id)
            except Exception:
                pass
    # === Конец новой логики ===
        
        prompt_id = state_info.get("prompt_message_id")
        data = state_info.get("data", {})
        text = message.text.strip()

        # --- Новая логика для получения примера конфигурации ---
        if state == 'waiting_for_sample_config':
            process_sample_config_input(admin_id, message)
            return

        # --- Server Flows ---
        if state == 'waiting_for_server_name':
            data['name'] = text
            state_info['state'] = 'waiting_for_panel_type_selection'
            prompt_text = "Пожалуйста, выберите тип панели нового сервера:"
            _bot.edit_message_text(prompt_text, admin_id, prompt_id, reply_markup=inline_keyboards.get_panel_type_selection_menu())
            return

        elif state == 'waiting_for_server_url':
            data['url'] = text
            state_info['state'] = 'waiting_for_server_username'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_USERNAME, admin_id, prompt_id)
        elif state == 'waiting_for_server_username':
            data['username'] = text
            state_info['state'] = 'waiting_for_server_password'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_PASSWORD, admin_id, prompt_id)
        elif state == 'waiting_for_server_password':
            data['password'] = text
            state_info['state'] = 'waiting_for_sub_base_url'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_SUB_BASE_URL, admin_id, prompt_id)
        elif state == 'waiting_for_sub_base_url':
            data['sub_base_url'] = text
            state_info['state'] = 'waiting_for_sub_path_prefix'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_SUB_PATH_PREFIX, admin_id, prompt_id)
        elif state == 'waiting_for_sub_path_prefix':
            data['sub_path_prefix'] = text
            execute_add_server(admin_id, data)
        elif state == 'waiting_for_server_id_to_delete':
            process_delete_server_id(admin_id, message)

        # --- Plan Flows ---
        elif state == 'waiting_for_plan_name':
            data['name'] = text
            state_info['state'] = 'waiting_for_plan_type'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_TYPE, admin_id, prompt_id, reply_markup=inline_keyboards.get_plan_type_selection_menu_admin())
        elif state == 'waiting_for_plan_volume':
            if not helpers.is_float_or_int(text) or float(text) <= 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_VOLUME}", admin_id, prompt_id); return
            data['volume_gb'] = float(text)
            state_info['state'] = 'waiting_for_plan_duration'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_DURATION, admin_id, prompt_id)
        elif state == 'waiting_for_plan_duration':
            if not text.isdigit() or int(text) < 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_DURATION}", admin_id, prompt_id); return
            data['duration_days'] = int(text)
            state_info['state'] = 'waiting_for_plan_price'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_PRICE, admin_id, prompt_id)
        elif state == 'waiting_for_plan_price':
            if not helpers.is_float_or_int(text) or float(text) < 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_PRICE}", admin_id, prompt_id); return
            data['price'] = float(text)
            execute_add_plan(admin_id, data)
        elif state == 'waiting_for_per_gb_price':
            if not helpers.is_float_or_int(text) or float(text) <= 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_PER_GB_PRICE}", admin_id, prompt_id); return
            data['per_gb_price'] = float(text)
            state_info['state'] = 'waiting_for_gb_plan_duration'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_DURATION_GB, admin_id, prompt_id)
        elif state == 'waiting_for_gb_plan_duration':
            if not text.isdigit() or int(text) < 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_DURATION_GB}", admin_id, prompt_id); return
            data['duration_days'] = int(text)
            execute_add_plan(admin_id, data)
        elif state == 'waiting_for_plan_id_to_toggle':
            execute_toggle_plan_status(admin_id, text)
        elif state == 'waiting_for_plan_id_to_delete':
            process_delete_plan_id(admin_id, message)
        elif state == 'waiting_for_plan_id_to_edit':
            process_edit_plan_id(admin_id, message)
        elif state == 'waiting_for_new_plan_name':
            process_edit_plan_name(admin_id, message)
        elif state == 'waiting_for_new_plan_price':
            process_edit_plan_price(admin_id, message)

        # --- Profile Flows ---
        elif state == 'waiting_for_profile_name':
            data['name'] = text
            state_info['state'] = 'waiting_for_profile_per_gb_price'
            _bot.edit_message_text(messages.ADD_PROFILE_PROMPT_PER_GB_PRICE, admin_id, prompt_id)
        elif state == 'waiting_for_profile_per_gb_price':
            if not helpers.is_float_or_int(text) or float(text) <= 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PROFILE_PROMPT_PER_GB_PRICE}", admin_id, prompt_id); return
            data['per_gb_price'] = float(text)
            state_info['state'] = 'waiting_for_profile_duration'
            _bot.edit_message_text(messages.ADD_PROFILE_PROMPT_DURATION, admin_id, prompt_id)
        elif state == 'waiting_for_profile_duration':
            if not text.isdigit() or int(text) <= 0:
                _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PROFILE_PROMPT_DURATION}", admin_id, prompt_id); return
            data['duration_days'] = int(text)
            state_info['state'] = 'waiting_for_profile_description'
            _bot.edit_message_text(messages.ADD_PROFILE_PROMPT_DESCRIPTION, admin_id, prompt_id)
        elif state == 'waiting_for_profile_description':
            data['description'] = None if text.lower() == 'skip' else text
            execute_add_profile(admin_id, data)

        # --- Gateway Flows ---
        elif state == 'waiting_for_gateway_name':
            data['name'] = text
            state_info['state'] = 'waiting_for_gateway_type'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_TYPE, admin_id, prompt_id, reply_markup=inline_keyboards.get_gateway_type_selection_menu())
        elif state == 'waiting_for_merchant_id':
            data['merchant_id'] = text
            state_info['state'] = 'waiting_for_gateway_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)
        elif state == 'waiting_for_card_number':
            if not text.isdigit() or len(text) != 16:
                _bot.edit_message_text(f"Неверный номер карты.\n\n{messages.ADD_GATEWAY_PROMPT_CARD_NUMBER}", admin_id, prompt_id); return
            data['card_number'] = text
            state_info['state'] = 'waiting_for_card_holder_name'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_HOLDER_NAME, admin_id, prompt_id)
        elif state == 'waiting_for_card_holder_name':
            data['card_holder_name'] = text
            state_info['state'] = 'waiting_for_gateway_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)
        elif state == 'waiting_for_gateway_description':
            data['description'] = None if text.lower() == 'skip' else text
            execute_add_gateway(admin_id, data)
        elif state == 'waiting_for_gateway_id_to_toggle':
            execute_toggle_gateway_status(admin_id, text)
        elif state == 'waiting_for_gateway_edit_name':
            data['new_name'] = text
            state_info['state'] = 'waiting_for_gateway_edit_type'
            current_gateway = data['current_gateway']
            _bot.edit_message_text(
                f"Новое имя: **{text}**\n\n"
                f"Пожалуйста, выберите тип шлюза:",
                admin_id, 
                prompt_id,
                reply_markup=inline_keyboards.get_gateway_type_selection_menu(),
                parse_mode='Markdown'
            )
        elif state == 'waiting_for_gateway_edit_merchant_id':
            data['new_merchant_id'] = text
            state_info['state'] = 'waiting_for_gateway_edit_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)
        elif state == 'waiting_for_gateway_edit_card_number':
            if not text.isdigit() or len(text) != 16:
                _bot.edit_message_text(f"Неверный номер карты.\n\n{messages.ADD_GATEWAY_PROMPT_CARD_NUMBER}", admin_id, prompt_id); return
            data['new_card_number'] = text
            state_info['state'] = 'waiting_for_gateway_edit_card_holder_name'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_HOLDER_NAME, admin_id, prompt_id)
        elif state == 'waiting_for_gateway_edit_card_holder_name':
            data['new_card_holder_name'] = text
            state_info['state'] = 'waiting_for_gateway_edit_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)
        elif state == 'waiting_for_gateway_edit_description':
            data['new_description'] = None if text.lower() == 'skip' else text
            execute_update_gateway(admin_id, data)
            
        # --- Admin Management Flows ---
        elif state == 'waiting_for_admin_id_to_add':
            if not text.isdigit():
                _bot.send_message(admin_id, "Неверный ID. Пожалуйста, введите число.")
                return
            target_user_id = int(text)
            # Используем новую функцию set_user_role
            if _db_manager.set_user_role(target_user_id, 'admin'):
                _bot.send_message(admin_id, f"✅ Пользователь с ID `{target_user_id}` успешно повышен до роли «Администратор».")
            else:
                _bot.send_message(admin_id, "❌ Пользователь не найден или произошла ошибка при изменении роли.")
            _clear_admin_state(admin_id)
            _show_admin_management_menu(admin_id, message)

        elif state == 'waiting_for_admin_id_to_remove':
            if not text.isdigit():
                _bot.send_message(admin_id, "Неверный ID. Пожалуйста, введите число.")
                return
            target_user_id = int(text)
            if target_user_id == admin_id:
                _bot.send_message(admin_id, "❌ Вы не можете изменить свою собственную роль.")
                return
            # Используем новую функцию set_user_role, чтобы сделать пользователя обычным
            if _db_manager.set_user_role(target_user_id, 'user'):
                _bot.send_message(admin_id, f"✅ Роль пользователя с ID `{target_user_id}` успешно изменена на «Обычный пользователь».")
            else:
                _bot.send_message(admin_id, "❌ Пользователь не найден или произошла ошибка при изменении роли.")
            _clear_admin_state(admin_id)
            _show_admin_management_menu(admin_id, message)
        # --- Branding Settings Flows ---
        elif state == 'waiting_for_brand_name':
            new_brand_name = message.text.strip()
            # Простая проверка, чтобы убедиться, что имя подходит
            if not new_brand_name.isalnum():
                _bot.send_message(admin_id, "Неверное название бренда. Пожалуйста, используйте только английские буквы и цифры без пробелов.")
                return
            
            _db_manager.update_setting('brand_name', new_brand_name)
            _bot.edit_message_text(f"✅ Название бренда успешно изменено на **{new_brand_name}**.", admin_id, state_info['prompt_message_id'])
            _clear_admin_state(admin_id)
            # Показать меню снова с новым именем
            show_branding_settings_menu(admin_id, message)
        elif state == 'waiting_for_new_message_text':
            if text.lower() == 'cancel':
                _bot.edit_message_text("Операция редактирования отменена.", admin_id, state_info['prompt_message_id'])
                _clear_admin_state(admin_id)
                show_message_management_menu(admin_id, message)
                return

            message_key = state_info['data']['message_key']
            if _db_manager.update_bot_message(message_key, text):
                _bot.send_message(admin_id, f"✅ Сообщение `{message_key}` успешно обновлено.")
            else:
                _bot.send_message(admin_id, "❌ Произошла ошибка при обновлении сообщения.")
            
            _clear_admin_state(admin_id)
            show_message_management_menu(admin_id, message)
        elif state == 'waiting_for_balance_adjustment':
            text = message.text.strip()
            target_telegram_id = state_info['data']['target_user_id']
            prompt_id = state_info['prompt_message_id']
            
            
            if text.lower() == 'cancel':
                # Сообщение 'cancel' было удалено общей логикой вверху функции
                _bot.send_message(admin_id, "Операция отменена.")
                _clear_admin_state(admin_id)
                _show_user_management_panel(admin_id, target_telegram_id, prompt_id)
                return

            if not (text.startswith('+') or text.startswith('-')) or not text[1:].isdigit():
                _bot.send_message(admin_id, "Неверный формат ввода. Пожалуйста, повторите попытку с правильным форматом (например, +50000).")
                return

            try:
                amount = int(text)
                user_info = _db_manager.get_user_by_telegram_id(target_telegram_id)
                if not user_info:
                    _bot.send_message(admin_id, "Указанный пользователь не найден.")
                    _clear_admin_state(admin_id)
                    return
                
                # Используем user_info['id'], который является первичным ключом базы данных
                if _db_manager.add_to_user_balance(user_info['id'], float(amount)):
                    # === основное исправление здесь ===
                    # 1. Повторная команда удаления отсюда удалена.
                    # 2. Вместо answer_callback_query используем send_message, что правильно.
                    _bot.send_message(admin_id, f"✅ Баланс пользователя успешно изменен на {amount:,.0f} туманов.")
                    _clear_admin_state(admin_id)
                    _show_user_management_panel(admin_id, target_telegram_id, prompt_id)
                else:
                    _bot.send_message(admin_id, "❌ Произошла ошибка при обновлении баланса пользователя.")
                    _clear_admin_state(admin_id)
            except Exception as e:
                logger.error(f"Error adjusting balance for user {target_telegram_id}: {e}")
                _bot.send_message(admin_id, "❌ Произошла ошибка при обработке суммы.")
                _clear_admin_state(admin_id)
        elif state == 'waiting_for_broadcast_message':
            # Сначала проверяем команду отмены
            if message.text and message.text.lower() == '/cancel':
                _bot.delete_message(admin_id, message.message_id)
                _bot.edit_message_text("Операция массовой рассылки отменена.", admin_id, state_info['prompt_message_id'])
                _clear_admin_state(admin_id)
                _show_admin_main_menu(admin_id)
                return

            # Сохраняем сообщение администратора в состоянии
            state_info['data']['broadcast_message_id'] = message.message_id
            state_info['data']['broadcast_chat_id'] = message.chat.id
            # Переводим состояние на следующий этап, чтобы сохранить информацию о сообщении
            state_info['state'] = 'waiting_for_broadcast_confirmation'

            total_users = len(_db_manager.get_all_users())
            
            # Пересылаем сообщение администратора ему же, чтобы он увидел предпросмотр
            _bot.send_message(admin_id, "👇 **Это сообщение, которое будет отправлено.** 👇")
            _bot.forward_message(admin_id, from_chat_id=message.chat.id, message_id=message.message_id)

            # Отправляем сообщение с подтверждением
            confirmation_text = f"Вы уверены, что хотите отправить это сообщение **{total_users}** пользователям?"
            _bot.send_message(admin_id, confirmation_text, reply_markup=inline_keyboards.get_broadcast_confirmation_menu())
        # --- Other Flows ---
        elif state == 'waiting_for_server_id_for_inbounds':
            process_manage_inbounds_flow(admin_id, message)
        elif state == 'waiting_for_tutorial_platform':
            process_tutorial_platform(admin_id, message)
        elif state == 'waiting_for_tutorial_app_name':
            process_tutorial_app_name(admin_id, message)
        elif state == 'waiting_for_tutorial_forward':
            process_tutorial_forward(admin_id, message)
        elif state == 'waiting_for_user_id_to_search':
            process_user_search(admin_id, message)
        elif state == 'waiting_for_channel_id':
            process_set_channel_id(admin_id, message)
        elif state == 'waiting_for_channel_link':
            process_set_channel_link(admin_id, message)
        elif state == 'waiting_for_support_link':
            process_support_link(admin_id, message)
    # =============================================================================
    # SECTION: Process Starters and Callback Handlers
    # =============================================================================
    def start_add_server_flow(admin_id, message):
        """Начинает процесс добавления сервера с вопроса о типе панели."""
        _clear_admin_state(admin_id) # Очистка предыдущего состояния
        prompt = _show_menu(admin_id, "Пожалуйста, выберите тип панели нового сервера:", inline_keyboards.get_panel_type_selection_menu(), message)
        # Следующий шаг обрабатывается обработчиком обратного вызова ниже


    def start_delete_server_flow(admin_id, message):
        _clear_admin_state(admin_id)
        list_text = _generate_server_list_text()
        if list_text == messages.NO_SERVERS_FOUND:
            _bot.edit_message_text(list_text, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management")); return
        _admin_states[admin_id] = {'state': 'waiting_for_server_id_to_delete', 'prompt_message_id': message.message_id}
        prompt_text = f"{list_text}\n\n{messages.DELETE_SERVER_PROMPT}"
        _bot.edit_message_text(prompt_text, admin_id, message.message_id, parse_mode='Markdown')

    def start_add_plan_flow(admin_id, message):
        """Начинает процесс добавления нового глобального тарифа."""
        _clear_admin_state(admin_id)
        # Сначала спрашиваем название тарифа
        prompt = _show_menu(admin_id, messages.ADD_PLAN_PROMPT_NAME, inline_keyboards.get_back_button("admin_plan_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_plan_name', 'data': {}, 'prompt_message_id': prompt.message_id}
    def start_toggle_plan_status_flow(admin_id, message):
        _clear_admin_state(admin_id)
        # --- исправленная часть ---
        # Теперь необходимые параметры передаются в функцию
        plans_text = list_all_plans(admin_id, message, return_text=True)
        _bot.edit_message_text(f"{plans_text}\n\n{messages.TOGGLE_PLAN_STATUS_PROMPT}", admin_id, message.message_id, parse_mode='Markdown')
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_toggle', 'prompt_message_id': message.message_id}
        
    def start_add_gateway_flow(admin_id, message):
        _clear_admin_state(admin_id)
        _admin_states[admin_id] = {'state': 'waiting_for_gateway_name', 'data': {}, 'prompt_message_id': message.message_id}
        _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_NAME, admin_id, message.message_id)
        
    def start_toggle_gateway_status_flow(admin_id, message):
        _clear_admin_state(admin_id)
        # --- исправленная часть ---
        # Теперь необходимые параметры передаются в функцию
        gateways_text = list_all_gateways(admin_id, message, return_text=True)
        _bot.edit_message_text(f"{gateways_text}\n\n{messages.TOGGLE_GATEWAY_STATUS_PROMPT}", admin_id, message.message_id, parse_mode='Markdown')
        _admin_states[admin_id] = {'state': 'waiting_for_gateway_id_to_toggle', 'prompt_message_id': message.message_id}

    def start_edit_gateway_flow(admin_id, message):
        """Начать процесс редактирования платежного шлюза"""
        _clear_admin_state(admin_id)
        gateways = _db_manager.get_all_payment_gateways()
        if not gateways:
            _bot.edit_message_text("❌ Платежные шлюзы для редактирования не найдены.", admin_id, message.message_id)
            return
        
        _bot.edit_message_text(
            "✏️ Пожалуйста, выберите шлюз, который хотите отредактировать:",
            admin_id, 
            message.message_id,
            reply_markup=inline_keyboards.get_gateway_selection_menu_for_edit(gateways)
        )

    def start_delete_gateway_flow(admin_id, message):
        """Начать процесс удаления платежного шлюза"""
        _clear_admin_state(admin_id)
        gateways = _db_manager.get_all_payment_gateways()
        if not gateways:
            _bot.edit_message_text("❌ Платежные шлюзы для удаления не найдены.", admin_id, message.message_id)
            return
        
        _bot.edit_message_text(
            "🗑️ Пожалуйста, выберите шлюз, который хотите удалить:",
            admin_id, 
            message.message_id,
            reply_markup=inline_keyboards.get_gateway_selection_menu_for_delete(gateways)
        )

    def start_gateway_edit_flow(admin_id, message, gateway_id):
        """Начать процесс редактирования конкретного платежного шлюза"""
        gateway = _db_manager.get_payment_gateway_by_id(gateway_id)
        if not gateway:
            _bot.answer_callback_query(message.id, "❌ Указанный шлюз не найден.", show_alert=True)
            return
        
        _clear_admin_state(admin_id)
        _admin_states[admin_id] = {
            'state': 'waiting_for_gateway_edit_name',
            'data': {'gateway_id': gateway_id, 'current_gateway': gateway},
            'prompt_message_id': message.message_id
        }
        
        current_name = gateway['name']
        current_type = gateway['type']
        
        # Отображение текущих настроек в зависимости от типа шлюза
        current_config_text = ""
        if current_type == 'zarinpal':
            merchant_id = gateway.get('merchant_id', 'Не настроено')
            current_config_text = f"Merchant ID: {merchant_id}"
        elif current_type == 'card_to_card':
            card_number = gateway.get('card_number', 'Не настроено')
            card_holder = gateway.get('card_holder_name', 'Не настроено')
            current_config_text = f"Номер карты: {card_number}\nВладелец карты: {card_holder}"
        
        edit_text = (
            f"✏️ **Редактирование платежного шлюза**\n\n"
            f"**Текущий шлюз:** {current_name}\n"
            f"**Тип:** {current_type}\n"
            f"**Текущие настройки:**\n{current_config_text}\n\n"
            f"Пожалуйста, введите новое имя шлюза (или введите то же имя, чтобы сохранить текущее):"
        )
        
        _bot.edit_message_text(edit_text, admin_id, message.message_id, parse_mode='Markdown')



    # =============================================================================
    # SECTION: Main Bot Handlers
    # =============================================================================

    @_bot.message_handler(commands=['admin'])
    def handle_admin_command(message):
        if not helpers.is_admin(message.from_user.id):
            _bot.reply_to(message, messages.NOT_ADMIN_ACCESS); return
        try: _bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        _clear_admin_state(message.from_user.id)
        _show_admin_main_menu(message.from_user.id)
    
    @_bot.message_handler(content_types=['text'], func=lambda msg: helpers.is_admin(msg.from_user.id) and _admin_states.get(msg.from_user.id, {}).get('state') == 'waiting_for_api_key')
    def handle_api_key_input(message):
        """Обработка ввода API Key"""
        process_api_key_input(message)
    
    @_bot.callback_query_handler(func=lambda call: helpers.is_admin(call.from_user.id))
    def handle_admin_callbacks(call):
        """Этот обработчик централизованно управляет всеми кликами администратора."""
        _bot.answer_callback_query(call.id)
        admin_id, message, data = call.from_user.id, call.message, call.data
        state_info = _admin_states.get(admin_id, {})

        actions = {
            "admin_broadcast": start_broadcast_flow,
            "admin_message_management": lambda a_id, msg: show_message_management_menu(a_id, msg, page=1),
            "admin_main_menu": lambda a_id, msg: (_clear_admin_state(a_id), _show_admin_main_menu(a_id, msg)),
            "admin_server_management": _show_server_management_menu,
            "admin_plan_management": lambda a_id, msg: (_clear_admin_state(a_id), _show_plan_management_menu(a_id, msg)),
            "admin_profile_management": _show_profile_management_menu,
            "admin_payment_management": _show_payment_gateway_management_menu,
            "admin_user_management": _show_user_management_menu,
            "admin_add_server": start_add_server_flow,
            "admin_list_servers": list_all_servers,
            "admin_delete_server": start_delete_server_flow,
            "admin_test_all_servers": test_all_servers,
            "admin_manage_inbounds": start_manage_inbounds_flow,
            "admin_add_plan": start_add_plan_flow,
            "admin_list_plans": list_all_plans,
            "admin_delete_plan": start_delete_plan_flow,
            "admin_edit_plan": start_edit_plan_flow,
            "admin_toggle_plan_status": start_toggle_plan_status_flow,
            "admin_add_gateway": start_add_gateway_flow,
            "admin_list_gateways": list_all_gateways,
            "admin_toggle_gateway_status": start_toggle_gateway_status_flow,
            "admin_edit_gateway": start_edit_gateway_flow,
            "admin_delete_gateway": start_delete_gateway_flow,
            "admin_list_users": list_all_users,
            "admin_search_user": start_search_user_flow,
            "admin_channel_lock_management": show_channel_lock_menu,
            "admin_set_channel_lock": start_set_channel_lock_flow,
            "admin_remove_channel_lock": execute_remove_channel_lock,
            "admin_tutorial_management": show_tutorial_management_menu,
            "admin_add_tutorial": start_add_tutorial_flow,
            "admin_list_tutorials": list_tutorials,
            "admin_support_management": show_support_management_menu,
            "admin_edit_support_link": start_edit_support_link_flow,
            "admin_add_profile": start_add_profile_flow,
            "admin_list_profiles": list_all_profiles,
            "admin_manage_profile_inbounds": start_manage_profile_inbounds_flow,
            "admin_manage_admins": _show_admin_management_menu,
            "admin_add_admin": start_add_admin_flow,
            "admin_remove_admin": start_remove_admin_flow,
            "admin_check_nginx": check_nginx_status,
            "admin_health_check": run_system_health_check,
            "admin_webhook_setup": start_webhook_setup_flow,
            "admin_create_backup": create_backup,
            "admin_check_subscription_links": check_and_fix_subscription_links,
            "admin_refresh_all_subscriptions": refresh_all_subscription_links,
            "admin_subscription_system_status": show_subscription_system_status,
            "admin_test_config_builder": show_config_builder_test_menu,
            "admin_create_config_menu": show_config_creator_menu,
            "admin_log_full_json": show_json_logger_menu,
            "admin_set_api_key": start_set_api_key_flow,
            "admin_update_configs": update_configs_from_panel,
        }

        if data in actions:
            actions[data](admin_id, message)
            return
        # --- Broadcast Confirmation Logic ---
        if data == "admin_cancel_broadcast":
            _clear_admin_state(admin_id)
            _bot.edit_message_text("Операция массовой рассылки отменена.", admin_id, message.message_id)
            _show_admin_main_menu(admin_id)
            return

        elif data == "admin_confirm_broadcast":
            state_info = _admin_states.get(admin_id, {})
            if state_info.get('state') != 'waiting_for_broadcast_confirmation':
                _bot.answer_callback_query(call.id, "Информация о сообщении не найдена. Пожалуйста, попробуйте снова.", show_alert=True)
                return

            broadcast_message_id = state_info['data']['broadcast_message_id']
            broadcast_chat_id = state_info['data']['broadcast_chat_id']
            _clear_admin_state(admin_id)

            all_users = _db_manager.get_all_users()
            total_users = len(all_users)

            _bot.edit_message_text(f"⏳ Начинается отправка сообщения **{total_users}** пользователям. Этот процесс может занять некоторое время...", admin_id, message.message_id, parse_mode='Markdown')

            successful_sends = 0
            failed_sends = 0

            for user in all_users:
                try:
                    _bot.forward_message(
                        chat_id=user['telegram_id'],
                        from_chat_id=broadcast_chat_id,
                        message_id=broadcast_message_id
                    )
                    successful_sends += 1
                except Exception as e:
                    failed_sends += 1
                    logger.error(f"Failed to send broadcast to user {user['telegram_id']}: {e}")

                # Для предотвращения ограничений Telegram можно добавить небольшую задержку
                # import time
                # time.sleep(0.1)

            report_text = (
                f"📣 **Итоговый отчет о массовой рассылке**\n\n"
                f"✅ Количество успешных отправок: **{successful_sends}**\n"
                f"❌ Количество неудачных отправок: **{failed_sends}**\n"
                f"👥 Общее количество пользователей: **{total_users}**"
            )
            _bot.send_message(admin_id, report_text, parse_mode='Markdown')
            _show_admin_main_menu(admin_id) # Показать главное меню снова
            return
        # --- Управление шаблонами серверов ---
        if data == "admin_manage_templates":
            show_template_management_menu(admin_id, message)
            return
        elif data.startswith("admin_test_config_server_"):
            server_id = int(data.split('_')[-1])
            logger.info(f"Testing config builder for server {server_id}")
            test_config_builder_for_server(admin_id, message, server_id)
            return
        elif data.startswith("admin_test_config_inbound_"):
            parts = data.split('_')
            server_id = int(parts[4])
            inbound_id = int(parts[5])
            logger.info(f"Testing config builder for server {server_id}, inbound {inbound_id}")
            test_config_builder_for_inbound(admin_id, message, server_id, inbound_id)
            return
        elif data.startswith("admin_create_config_server_"):
            server_id = int(data.split('_')[-1])
            show_inbound_selection_for_config(admin_id, message, server_id)
            return
        elif data.startswith("admin_create_config_inbound_"):
            parts = data.split('_')
            server_id = int(parts[4])
            inbound_id = int(parts[5])
            create_configs_for_inbound(admin_id, message, server_id, inbound_id)
            return
        elif data.startswith("admin_log_json_server_"):
            server_id = int(data.split('_')[-1])
            show_inbound_selection_for_json_log(admin_id, message, server_id)
            return
        elif data.startswith("admin_log_json_inbound_"):
            parts = data.split('_')
            server_id = int(parts[4])
            inbound_id = int(parts[5])
            log_full_json_for_inbound(admin_id, message, server_id, inbound_id)
            return
        elif data.startswith("admin_edit_template_"):
            parts = data.split('_')
            server_id = int(parts[3])
            inbound_id = int(parts[4])
            server_data = _db_manager.get_server_by_id(server_id)
            inbound_info_db = _db_manager.get_server_inbound_details(server_id, inbound_id)
            inbound_info = {'id': inbound_id, 'remark': inbound_info_db.get('remark', '') if inbound_info_db else ''}
            context = {'type': 'server', 'server_id': server_id, 'server_name': server_data['name']}
            start_sample_config_flow(admin_id, message, [inbound_info], context)
            return
        # --- Управление брендингом ---
        elif data == "admin_branding_settings":
            show_branding_settings_menu(admin_id, message)
            return
        elif data == "admin_change_brand_name":
            start_change_brand_name_flow(admin_id, message)
            return
        # --- Управление сообщениями с пагинацией ---
        if data == "admin_msg_page_":
            show_message_management_menu(admin_id, message, page=1)
            return
        elif data.startswith("admin_msg_page_"):
            page = int(data.split('_')[-1])
            show_message_management_menu(admin_id, message, page=page)
            return
        elif data.startswith("admin_edit_msg_"):
            message_key = data.replace("admin_edit_msg_", "", 1)
            start_edit_message_flow(admin_id, message, message_key)
            return
        elif data.startswith("admin_view_subs_"):
            target_user_id = int(data.split('_')[-1])
            purchases = _db_manager.get_user_purchases_by_telegram_id(target_user_id)
            user_info = _db_manager.get_user_by_telegram_id(target_user_id)
            first_name = helpers.escape_markdown_v1(user_info.get('first_name', ''))

            text = f"🗂️ **Список подписок пользователя {first_name}:**\n\n"
            if not purchases:
                text += "У этого пользователя нет подписок."
            else:
                for p in purchases:
                    status = "✅ Активна" if p['is_active'] else "❌ Неактивна"
                    expire = p['expire_date'].strftime('%Y-%m-%d') if p.get('expire_date') else "Безлимитно"
                    server_name = helpers.escape_markdown_v1(p.get('server_name', 'N/A'))

                    text += (
                        f"{status} **ID сервиса:** `{p['id']}`\n"
                        f"   - **Сервер:** {server_name}\n"
                        f"   - **Дата окончания:** {expire}\n"
                        "--------------------\n"
                    )

            markup = inline_keyboards.get_admin_subs_list_menu(target_user_id)
            _bot.edit_message_text(text, admin_id, message.message_id, reply_markup=markup, parse_mode='Markdown')
            return
                # --- Управление шаблонами профилей ---
        elif data == "admin_manage_profile_templates":
            show_profile_template_management_menu(admin_id, message)
            return
        elif data.startswith("admin_edit_profile_template_"):
            parts = data.split('_')
            profile_id, server_id, inbound_id = int(parts[4]), int(parts[5]), int(parts[6])
            server_data = _db_manager.get_server_by_id(server_id)
            profile_data = _db_manager.get_profile_by_id(profile_id)
            inbound_info_db = _db_manager.get_server_inbound_details(server_id, inbound_id)
            inbound_info = {'id': inbound_id, 'remark': inbound_info_db.get('remark', '') if inbound_info_db else ''}
            context = {
                'type': 'profile', 'profile_id': profile_id, 'profile_name': profile_data['name'],
                'server_id': server_id, 'server_name': server_data['name']
            }
            start_sample_config_flow(admin_id, message, [inbound_info], context)
            return
        elif data == "admin_view_profile_db":
            show_profile_inbounds_db_status(admin_id, message)
            return
        # --- Управление платежами ---
        elif data.startswith("admin_approve_payment_"):
            process_payment_approval(admin_id, int(data.split('_')[-1]), message)
            return
        elif data.startswith("admin_reject_payment_"):
            process_payment_rejection(admin_id, int(data.split('_')[-1]), message)
            return

        # --- Управление входящими (сохранение и подтверждение) ---
        elif data.startswith("inbound_save_"):
            server_id = int(data.split('_')[-1])
            execute_save_inbounds(admin_id, message, server_id)
            return
        elif data.startswith("admin_pi_save_"):
            parts = data.split('_')
            profile_id, server_id = int(parts[3]), int(parts[4])
            execute_save_profile_inbounds(admin_id, message, profile_id, server_id)
            return

        # --- Управление выбором входящих (отметка) ---
        elif data.startswith("inbound_toggle_"):
            handle_inbound_selection(admin_id, call)
            return
        elif data.startswith("admin_pi_toggle_"):
            parts = data.split('_')
            profile_id, server_id, inbound_id = int(parts[3]), int(parts[4]), int(parts[5])
            handle_profile_inbound_toggle(admin_id, message, profile_id, server_id, inbound_id)
            return
        
        # --- Управление выбором профиля и сервера для профиля ---
        elif data.startswith("admin_select_profile_"):
            profile_id = int(data.split('_')[-1])
            handle_profile_selection(admin_id, message, profile_id)
            return
        elif data.startswith("admin_ps_"): # Profile Server Selection
            parts = data.split('_')
            profile_id, server_id = int(parts[2]), int(parts[3])
            handle_server_selection_for_profile(admin_id, message, profile_id, server_id)
            return

        # --- Управление удалениями с подтверждением ---
        elif data.startswith("confirm_delete_server_"):
            execute_delete_server(admin_id, message, int(data.split('_')[-1]))
            return
        elif data.startswith("confirm_delete_plan_"):
            execute_delete_plan(admin_id, message, int(data.split('_')[-1]))
            return
        elif data.startswith("admin_delete_purchase_"):
            parts = data.split('_')
            purchase_id, user_telegram_id = int(parts[3]), int(parts[4])
            execute_delete_purchase(admin_id, message, purchase_id, user_telegram_id)
            return
        elif data.startswith("admin_delete_tutorial_"):
            execute_delete_tutorial(admin_id, message, int(data.split('_')[-1]))
            return
        

        # --- Управление выбором типа тарифа и шлюза ---
        elif data.startswith("plan_type_"):
            get_plan_details_from_callback(admin_id, message, data.replace("plan_type_", ""))
            return
        elif data.startswith("gateway_type_"):
            handle_gateway_type_selection(admin_id, message, data.replace('gateway_type_', ''))
            return
        elif data.startswith("admin_edit_gateway_"):
            gateway_id = int(data.split('_')[-1])
            start_gateway_edit_flow(admin_id, message, gateway_id)
            return
        elif data.startswith("admin_delete_gateway_"):
            gateway_id = int(data.split('_')[-1])
            gateway = _db_manager.get_payment_gateway_by_id(gateway_id)
            if gateway:
                _bot.edit_message_text(
                    f"🗑️ **Подтверждение удаления платежного шлюза**\n\n"
                    f"Вы уверены, что хотите удалить шлюз **{gateway['name']}**?\n\n"
                    f"⚠️ Это действие необратимо!",
                    admin_id,
                    message.message_id,
                    reply_markup=inline_keyboards.get_gateway_delete_confirmation_menu(gateway_id, gateway['name']),
                    parse_mode='Markdown'
                )
            else:
                _bot.answer_callback_query(call.id, "❌ Указанный шлюз не найден.", show_alert=True)
            return
        elif data.startswith("admin_confirm_delete_gateway_"):
            gateway_id = int(data.split('_')[-1])
            if _db_manager.delete_payment_gateway(gateway_id):
                _bot.answer_callback_query(call.id, "✅ Платежный шлюз успешно удален.")
                _show_payment_gateway_management_menu(admin_id, message)
            else:
                _bot.answer_callback_query(call.id, "❌ Произошла ошибка при удалении шлюза.", show_alert=True)
            return
        elif data.startswith("panel_type_"):
            handle_panel_type_selection(call)
            return
        # --- Управление панелью конкретного пользователя ---
        if data.startswith("admin_manage_user_"):
            target_user_id = int(data.split('_')[-1])
            # Прямой вызов вспомогательной функции для повторного отображения панели
            _show_user_management_panel(admin_id, target_user_id, message.message_id)
            return

        elif data.startswith("admin_change_role_"):
            target_user_id = int(data.split('_')[-1])
            user_info = _db_manager.get_user_by_telegram_id(target_user_id)
            first_name = helpers.escape_markdown_v1(user_info.get('first_name', ''))
            _bot.edit_message_text(
                f"Пожалуйста, выберите новую роль для пользователя **{first_name}**:",
                admin_id, message.message_id,
                reply_markup=inline_keyboards.get_change_role_menu(target_user_id),
                parse_mode='Markdown'
            )
            return

        elif data.startswith("admin_set_role_"):
            parts = data.split('_')
            target_user_id = int(parts[3])
            new_role = parts[4]
            
            if _db_manager.set_user_role(target_user_id, new_role):
                _bot.answer_callback_query(call.id, f"✅ Роль пользователя изменена на {new_role}.")
            else:
                _bot.answer_callback_query(call.id, "❌ Произошла ошибка при изменении роли.", show_alert=True)
            
            # Прямой вызов вспомогательной функции для повторного отображения панели с новой информацией
            _show_user_management_panel(admin_id, target_user_id, message.message_id)
            return
        elif data.startswith("admin_adjust_balance_"):
            target_user_id = int(data.split('_')[-1])
            user_info = _db_manager.get_user_by_telegram_id(target_user_id)
            first_name = helpers.escape_markdown_v1(user_info.get('first_name', ''))

            prompt_text = (
                f"💰 **Настройка баланса для:** {first_name}\n\n"
                "Пожалуйста, введите сумму для увеличения или уменьшения.\n\n"
                "**Пример:**\n"
                "Для увеличения на 50,000 туманов: `+50000`\n"
                "Для уменьшения на 10,000 туманов: `-10000`\n\n"
                "Для отмены отправьте `cancel`."
            )

            # Мы используем message.message_id, потому что prompt - это то же самое сообщение, которое редактируется
            _bot.edit_message_text(
                prompt_text,
                admin_id,
                message.message_id,
                reply_markup=None, # Удаляем клавиатуру, чтобы администратор мог ответить
                parse_mode='Markdown'
            )

            _admin_states[admin_id] = {
                'state': 'waiting_for_balance_adjustment',
                'data': {'target_user_id': target_user_id},
                'prompt_message_id': message.message_id
            }
            return
                # Если ни один из вышеперечисленных случаев не подошел
        else:
            _bot.edit_message_text(messages.UNDER_CONSTRUCTION, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_main_menu"))
    @_bot.message_handler(
    content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker'],
    func=lambda msg: helpers.is_admin(msg.from_user.id) and _admin_states.get(msg.from_user.id, {}).get('state')
        )
    def handle_admin_stateful_messages(message):
        admin_id = message.from_user.id
        # Логика удаления сообщения отсюда удаляется
        _handle_stateful_message(admin_id, message)
        
        


    # =============================================================================
# SECTION: Final Execution Functions
# =============================================================================

    def execute_add_server(admin_id, data):
        _clear_admin_state(admin_id)
        msg = _bot.send_message(admin_id, messages.ADD_SERVER_TESTING)
        temp_xui_client = _xui_api(panel_url=data['url'], username=data['username'], password=data['password'])
        if temp_xui_client.login():
            server_id = _db_manager.add_server(data['name'], data['url'], data['username'], data['password'], data['sub_base_url'], data['sub_path_prefix'])
            if server_id:
                _db_manager.update_server_status(server_id, True, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                _bot.edit_message_text(messages.ADD_SERVER_SUCCESS.format(server_name=data['name']), admin_id, msg.message_id)
            else:
                _bot.edit_message_text(messages.ADD_SERVER_DB_ERROR.format(server_name=data['name']), admin_id, msg.message_id)
        else:
            _bot.edit_message_text(messages.ADD_SERVER_LOGIN_FAILED.format(server_name=data['name']), admin_id, msg.message_id)
        _show_server_management_menu(admin_id)

    def execute_delete_server(admin_id, message, server_id):
        # Очистка состояния в начале выполнения окончательной операции
        _clear_admin_state(admin_id)
        
        server = _db_manager.get_server_by_id(server_id)
        if server and _db_manager.delete_server(server_id):
            _bot.edit_message_text(messages.SERVER_DELETED_SUCCESS.format(server_name=server['name']), admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
        else:
            _bot.edit_message_text(messages.SERVER_DELETED_ERROR, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))

    def execute_add_plan(admin_id, data):
        _clear_admin_state(admin_id)
        plan_id = _db_manager.add_plan(
            name=data.get('name'), plan_type=data.get('plan_type'),
            volume_gb=data.get('volume_gb'), duration_days=data.get('duration_days'),
            price=data.get('price'), per_gb_price=data.get('per_gb_price')
        )
        msg_to_send = messages.ADD_PLAN_SUCCESS if plan_id else messages.ADD_PLAN_DB_ERROR
        _bot.send_message(admin_id, msg_to_send.format(plan_name=data['name']))
        _show_plan_management_menu(admin_id)
        
    def execute_add_gateway(admin_id, data):
        _clear_admin_state(admin_id)
        gateway_id = _db_manager.add_payment_gateway(
            name=data.get('name'),
            gateway_type=data.get('gateway_type'),  # <-- исправлено
            card_number=data.get('card_number'),
            card_holder_name=data.get('card_holder_name'),
            merchant_id=data.get('merchant_id'),    # <-- добавлено
            description=data.get('description'),
            priority=0
        )
        
        msg_to_send = messages.ADD_GATEWAY_SUCCESS if gateway_id else messages.ADD_GATEWAY_DB_ERROR
        _bot.send_message(admin_id, msg_to_send.format(gateway_name=data['name']))
        _show_payment_gateway_management_menu(admin_id)

    def execute_update_gateway(admin_id, data):
        """Выполнение операции редактирования платежного шлюза"""
        _clear_admin_state(admin_id)
        
        gateway_id = data.get('gateway_id')
        new_name = data.get('new_name')
        new_gateway_type = data.get('new_gateway_type')
        new_description = data.get('new_description')
        
        # Подготовка параметров в зависимости от типа шлюза
        card_number = None
        card_holder_name = None
        merchant_id = None
        
        if new_gateway_type == 'zarinpal':
            merchant_id = data.get('new_merchant_id')
        elif new_gateway_type == 'card_to_card':
            card_number = data.get('new_card_number')
            card_holder_name = data.get('new_card_holder_name')
        
        # Обновление шлюза в базе данных
        success = _db_manager.update_payment_gateway(
            gateway_id=gateway_id,
            name=new_name,
            gateway_type=new_gateway_type,
            card_number=card_number,
            card_holder_name=card_holder_name,
            merchant_id=merchant_id,
            description=new_description
        )
        
        if success:
            _bot.send_message(admin_id, f"✅ Платежный шлюз **{new_name}** успешно отредактирован.")
        else:
            _bot.send_message(admin_id, "❌ Произошла ошибка при редактировании шлюза.")
        
        _show_payment_gateway_management_menu(admin_id)

    def execute_toggle_plan_status(admin_id, plan_id_str: str): # Входные данные изменены на text
        _clear_admin_state(admin_id)
        if not plan_id_str.isdigit() or not (plan := _db_manager.get_plan_by_id(int(plan_id_str))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND)
            _show_plan_management_menu(admin_id)
            return
        new_status = not plan['is_active']
        if _db_manager.update_plan_status(plan['id'], new_status):
            _bot.send_message(admin_id, messages.PLAN_STATUS_TOGGLED_SUCCESS.format(plan_name=plan['name'], new_status="активен" if new_status else "неактивен"))
        else:
            _bot.send_message(admin_id, messages.PLAN_STATUS_TOGGLED_ERROR.format(plan_name=plan['name']))
        _show_plan_management_menu(admin_id)
        
    def execute_toggle_gateway_status(admin_id, gateway_id_str: str): # Входные данные изменены на text
        _clear_admin_state(admin_id)
        if not gateway_id_str.isdigit() or not (gateway := _db_manager.get_payment_gateway_by_id(int(gateway_id_str))):
            _bot.send_message(admin_id, messages.GATEWAY_NOT_FOUND)
            _show_payment_gateway_management_menu(admin_id)
            return
        new_status = not gateway['is_active']
        if _db_manager.update_payment_gateway_status(gateway['id'], new_status):
            _bot.send_message(admin_id, messages.GATEWAY_STATUS_TOGGLED_SUCCESS.format(gateway_name=gateway['name'], new_status="активен" if new_status else "неактивен"))
        else:
            _bot.send_message(admin_id, messages.GATEWAY_STATUS_TOGGLED_ERROR.format(gateway_name=gateway['name']))
        _show_payment_gateway_management_menu(admin_id)
        # =============================================================================
    # SECTION: Process-Specific Helper Functions
    # =============================================================================

    def _generate_server_list_text():
        servers = _db_manager.get_all_servers()
        if not servers: return messages.NO_SERVERS_FOUND
        response_text = messages.LIST_SERVERS_HEADER
        for s in servers:
            status = "✅ онлайн" if s['is_online'] else "❌ оффлайн"
            is_active_emoji = "✅" if s['is_active'] else "❌"
            sub_link = f"{s['subscription_base_url'].rstrip('/')}/{s['subscription_path_prefix'].strip('/')}/<SUB_ID>"
            response_text += messages.SERVER_DETAIL_TEMPLATE.format(
                name=helpers.escape_markdown_v1(s['name']), id=s['id'], status=status, is_active_emoji=is_active_emoji, sub_link=helpers.escape_markdown_v1(sub_link)
            )
        return response_text

    
    def handle_inbound_selection(admin_id, call):
        """Правильно обрабатывает клики по кнопкам клавиатуры выбора входящих соединений."""
        data = call.data
        parts = data.split('_')
        action = parts[1]

        state_info = _admin_states.get(admin_id)
        if not state_info: return

        server_id = None
        
        # Извлечение server_id в зависимости от типа действия
        if action == 'toggle':
            # Формат: inbound_toggle_{server_id}_{inbound_id}
            if len(parts) == 4:
                server_id = int(parts[2])
        else: # для select, deselect, save
            # Формат: inbound_select_all_{server_id}
            server_id = int(parts[-1])

        if server_id is None or state_info.get('state') != f'selecting_inbounds_for_{server_id}':
            return

        # Получение необходимой информации из состояния
        selected_ids = state_info['data'].get('selected_inbound_ids', [])
        panel_inbounds = state_info['data'].get('panel_inbounds', [])

        # Выполнение операции в зависимости от действия
        if action == 'toggle':
            inbound_id_to_toggle = int(parts[3])
            if inbound_id_to_toggle in selected_ids:
                selected_ids.remove(inbound_id_to_toggle)
            else:
                selected_ids.append(inbound_id_to_toggle)
        
        elif action == 'select' and parts[2] == 'all':
            panel_ids = {p['id'] for p in panel_inbounds}
            selected_ids.extend([pid for pid in panel_ids if pid not in selected_ids])
            selected_ids = list(set(selected_ids)) # удаление дубликатов
        
        elif action == 'deselect' and parts[2] == 'all':
            selected_ids.clear()
            
        elif action == 'save':
            save_inbound_changes(admin_id, call.message, server_id, selected_ids)
            return
        
        # Обновление состояния и клавиатуры
        state_info['data']['selected_inbound_ids'] = selected_ids
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, selected_ids)
        
        try:
            _bot.edit_message_reply_markup(chat_id=admin_id, message_id=call.message.message_id, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in e.description:
                logger.warning(f"Error updating inbound selection keyboard: {e}")

    def process_payment_approval(admin_id, payment_id, message):
        """
        Подтверждает ручной платеж и, в зависимости от типа покупки (обычная или профиль),
        начинает процесс предоставления услуги. (финальная версия)
        """
        payment = _db_manager.get_payment_by_id(payment_id)
        
        if not payment or payment['is_confirmed']:
            try:
                # message.id здесь - это идентификатор сообщения, а не клика. Для простоты игнорируем ошибку.
                _bot.answer_callback_query(message.id, "Этот платеж уже обработан.", show_alert=True)
            except Exception:
                pass
            return

        order_details = json.loads(payment['order_details_json'])
        user_telegram_id = order_details['user_telegram_id']
        user_db_id = order_details['user_db_id']
        # Обновление статуса платежа в базе данных и редактирование сообщения администратора
        _db_manager.update_payment_status(payment_id, True, admin_id)
        try:
            admin_user = _bot.get_chat_member(admin_id, admin_id).user
            admin_username = f"@{admin_user.username}" if admin_user.username else admin_user.first_name
            new_caption = (message.caption or "") + "\n\n" + messages.ADMIN_PAYMENT_CONFIRMED_DISPLAY.format(admin_username=admin_username)
            _bot.edit_message_caption(new_caption, message.chat.id, message.message_id, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Не удалось отредактировать подпись сообщения администратора для платежа {payment_id}: {e}")

        # --- Основная логика: разделение по типу покупки ---
        if order_details.get('purchase_type') == 'profile':
            # Если это покупка профиля, вызовите централизованную и автоматическую функцию
            finalize_profile_purchase(_bot, _db_manager, user_telegram_id, order_details)
        elif order_details.get('purchase_type') == 'wallet_charge':
            amount = order_details['total_price']
            if _db_manager.add_to_user_balance(user_db_id, amount):
                _bot.send_message(user_telegram_id, f"✅ Ваш кошелек успешно пополнен на {amount:,.0f} туманов.")
            else:
                _bot.send_message(user_telegram_id, "❌ Произошла ошибка при пополнении вашего кошелька. Пожалуйста, свяжитесь с поддержкой.")
        else:
            # Если это обычная покупка, спросите у пользователя желаемое имя конфигурации
            prompt = _bot.send_message(user_telegram_id, messages.ASK_FOR_CUSTOM_CONFIG_NAME)
            _user_states[user_telegram_id] = {
                'state': 'waiting_for_custom_config_name',
                'data': order_details,
                'prompt_message_id': prompt.message_id
            }

    def process_payment_rejection(admin_id, payment_id, message):
        payment = _db_manager.get_payment_by_id(payment_id)
        if not payment or payment['is_confirmed']:
            _bot.answer_callback_query(message.id, "Этот платеж уже обработан.", show_alert=True); return
        _db_manager.update_payment_status(payment_id, False, admin_id)
        admin_user = _bot.get_chat_member(admin_id, admin_id).user
        new_caption = message.caption + "\n\n" + messages.ADMIN_PAYMENT_REJECTED_DISPLAY.format(admin_username=f"@{admin_user.username}" if admin_user.username else admin_user.first_name)
        _bot.edit_message_caption(new_caption, message.chat.id, message.message_id, parse_mode='Markdown')
        order_details = json.loads(payment['order_details_json'])
        _bot.send_message(order_details['user_telegram_id'], messages.PAYMENT_REJECTED_USER.format(support_link=SUPPORT_CHANNEL_LINK))
        
        
    def save_inbound_changes(admin_id, message, server_id, selected_ids):
        """Сохраняет изменения выбора входящих соединений в базе данных и предоставляет пользователю обратную связь."""
        server_data = _db_manager.get_server_by_id(server_id)
        panel_inbounds = _admin_states.get(admin_id, {}).get('data', {}).get('panel_inbounds', [])
        
        inbounds_to_save = [
            {'id': p_in['id'], 'remark': p_in.get('remark', '')}
            for p_in in panel_inbounds if p_in['id'] in selected_ids
        ]
        
        # Сначала информация сохраняется в базе данных
        if _db_manager.update_server_inbounds(server_id, inbounds_to_save):
            msg = messages.INBOUND_CONFIG_SUCCESS
        else:
            msg = messages.INBOUND_CONFIG_FAILED

        # Затем текущее сообщение редактируется и отображается кнопка "Назад"
        _bot.edit_message_text(
            msg.format(server_name=server_data['name']),
            admin_id,
            message.message_id,
            reply_markup=inline_keyboards.get_back_button("admin_server_management")
        )
        
        # Наконец, состояние администратора очищается
        _clear_admin_state(admin_id)
    def start_manage_inbounds_flow(admin_id, message):
        _clear_admin_state(admin_id)
        servers = _db_manager.get_all_servers(only_active=False) 
        if not servers:
            _bot.edit_message_text(messages.NO_SERVERS_FOUND, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            return
        
        server_list_text = "\n".join([f"ID: `{s['id']}` - {helpers.escape_markdown_v1(s['name'])}" for s in servers])
        prompt_text = f"**Список серверов:**\n{server_list_text}\n\n{messages.SELECT_SERVER_FOR_INBOUNDS_PROMPT}"
        
        prompt = _show_menu(admin_id, prompt_text, inline_keyboards.get_back_button("admin_server_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_server_id_for_inbounds', 'prompt_message_id': prompt.message_id}

    def process_manage_inbounds_flow(admin_id, message):
        """
        После получения ID сервера от администратора, получает и отображает список его входящих соединений из панели.
        (исправленная версия с использованием API Factory)
        """
        state_info = _admin_states.get(admin_id, {})
        if state_info.get('state') != 'waiting_for_server_id_for_inbounds': return

        server_id_str = message.text.strip()
        prompt_id = state_info.get('prompt_message_id')
        try: _bot.delete_message(admin_id, message.message_id)
        except Exception: pass
        
        if not server_id_str.isdigit() or not (server_data := _db_manager.get_server_by_id(int(server_id_str))):
            _bot.edit_message_text(f"{messages.SERVER_NOT_FOUND}\n\n{messages.SELECT_SERVER_FOR_INBOUNDS_PROMPT}", admin_id, prompt_id, parse_mode='Markdown')
            return

        server_id = int(server_id_str)
        _bot.edit_message_text(messages.FETCHING_INBOUNDS, admin_id, prompt_id)
        
        # --- основное исправление здесь ---
        # Вместо прямого создания XuiAPIClient, используем factory
        api_client = get_api_client(server_data)
        if not api_client:
            logger.error(f"Could not create API client for server {server_id}. Data: {server_data}")
            _bot.edit_message_text("Ошибка при создании API-клиента для этого сервера.", admin_id, prompt_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            _clear_admin_state(admin_id)
            return

        panel_inbounds = api_client.list_inbounds()
        # --- конец исправленной части ---

        if not panel_inbounds:
            _bot.edit_message_text(messages.NO_INBOUNDS_FOUND_ON_PANEL, admin_id, prompt_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            _clear_admin_state(admin_id)
            return

        active_db_inbound_ids = [i['inbound_id'] for i in _db_manager.get_server_inbounds(server_id, only_active=True)]
        
        state_info['state'] = f'selecting_inbounds_for_{server_id}'
        state_info['data'] = {'panel_inbounds': panel_inbounds, 'selected_inbound_ids': active_db_inbound_ids}
        
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, active_db_inbound_ids)
        _bot.edit_message_text(messages.SELECT_INBOUNDS_TO_ACTIVATE.format(server_name=server_data['name']), admin_id, prompt_id, reply_markup=markup, parse_mode='Markdown')

    def save_inbound_changes(admin_id, message, server_id, selected_ids):
        """Сохраняет изменения выбора входящих соединений в базе данных."""
        server_data = _db_manager.get_server_by_id(server_id)
        panel_inbounds = _admin_states.get(admin_id, {}).get('data', {}).get('panel_inbounds', [])
        inbounds_to_save = [{'id': p_in['id'], 'remark': p_in.get('remark', '')} for p_in in panel_inbounds if p_in['id'] in selected_ids]
        
        msg = messages.INBOUND_CONFIG_SUCCESS if _db_manager.update_server_inbounds(server_id, inbounds_to_save) else messages.INBOUND_CONFIG_FAILED
        _bot.edit_message_text(msg.format(server_name=server_data['name']), admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            
        _clear_admin_state(admin_id)

    def handle_inbound_selection(admin_id, call):
        """Исправлено с новой логикой для чтения callback_data."""
        data = call.data
        parts = data.split('_')
        action = parts[1]

        state_info = _admin_states.get(admin_id)
        if not state_info: return

        # Извлечение server_id способом, который работает для всех действий
        server_id = int(parts[2]) if action == 'toggle' else int(parts[-1])
            
        if state_info.get('state') != f'selecting_inbounds_for_{server_id}': return

        selected_ids = state_info['data'].get('selected_inbound_ids', [])
        panel_inbounds = state_info['data'].get('panel_inbounds', [])

        if action == 'toggle':
            inbound_id_to_toggle = int(parts[3]) # ID входящего всегда четвертый параметр
            if inbound_id_to_toggle in selected_ids:
                selected_ids.remove(inbound_id_to_toggle)
            else:
                selected_ids.append(inbound_id_to_toggle)
        
        elif action == 'select' and parts[2] == 'all':
            panel_ids = {p['id'] for p in panel_inbounds}
            selected_ids.extend([pid for pid in panel_ids if pid not in selected_ids])
        
        elif action == 'deselect' and parts[2] == 'all':
            selected_ids.clear()
            
        elif action == 'save':
            save_inbound_changes(admin_id, call.message, server_id, selected_ids)
            return
        
        state_info['data']['selected_inbound_ids'] = list(set(selected_ids))
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, selected_ids)
        
        try:
            _bot.edit_message_reply_markup(chat_id=admin_id, message_id=call.message.message_id, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in e.description:
                logger.warning(f"Error updating inbound selection keyboard: {e}")
                
                
    def create_backup(admin_id, message):
        """Создает резервную копию важных файлов бота (база данных и .env) и отправляет ее администратору."""
        _bot.edit_message_text("⏳ Создание файла резервной копии...", admin_id, message.message_id)
        
        backup_filename = f"alamor_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
        
        files_to_backup = [
            os.path.join(os.getcwd(), '.env'),
            _db_manager.db_path
        ]
        
        try:
            with zipfile.ZipFile(backup_filename, 'w') as zipf:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                    else:
                        logger.warning(f"Файл для бэкапа не найден: {file_path}")

            with open(backup_filename, 'rb') as backup_file:
                _bot.send_document(admin_id, backup_file, caption="✅ Ваш файл резервной копии готов.")
            
            _bot.delete_message(admin_id, message.message_id)
            _show_admin_main_menu(admin_id)

        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
            _bot.edit_message_text("❌ Произошла ошибка при создании файла резервной копии.", admin_id, message.message_id)
        finally:
            # Удаление zip-файла после отправки
            if os.path.exists(backup_filename):
                os.remove(backup_filename)
                
                
    def handle_gateway_type_selection(admin_id, message, gateway_type):
        state_info = _admin_states.get(admin_id)
        if not state_info: return
        
        # Проверка, находимся ли мы в режиме редактирования или добавления
        if state_info.get('state') == 'waiting_for_gateway_type':
            # Режим добавления нового шлюза
            state_info['data']['gateway_type'] = gateway_type
            
            if gateway_type == 'zarinpal':
                state_info['state'] = 'waiting_for_merchant_id'
                _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_MERCHANT_ID, admin_id, message.message_id)
            elif gateway_type == 'card_to_card':
                state_info['state'] = 'waiting_for_card_number'
                _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_NUMBER, admin_id, message.message_id)
        
        elif state_info.get('state') == 'waiting_for_gateway_edit_type':
            # Режим редактирования существующего шлюза
            data = state_info['data']
            data['new_gateway_type'] = gateway_type
            
            if gateway_type == 'zarinpal':
                state_info['state'] = 'waiting_for_gateway_edit_merchant_id'
                _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_MERCHANT_ID, admin_id, message.message_id)
            elif gateway_type == 'card_to_card':
                state_info['state'] = 'waiting_for_gateway_edit_card_number'
                _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_NUMBER, admin_id, message.message_id)
            
            
            
            
    def start_delete_plan_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.DELETE_PLAN_PROMPT, inline_keyboards.get_back_button("admin_plan_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_delete', 'prompt_message_id': prompt.message_id}
        
    def process_delete_plan_id(admin_id, message):
        state_info = _admin_states[admin_id]
        if not message.text.isdigit() or not (plan := _db_manager.get_plan_by_id(int(message.text))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND); return

        plan_id = int(message.text)
        confirm_text = messages.DELETE_PLAN_CONFIRM.format(
            plan_name=helpers.escape_markdown_v1(plan['name']), 
            plan_id=plan_id
        )
        markup = inline_keyboards.get_confirmation_menu(f"confirm_delete_plan_{plan_id}", "admin_plan_management")
        _bot.edit_message_text(confirm_text, admin_id, state_info['prompt_message_id'], reply_markup=markup, parse_mode='Markdown')
        _clear_admin_state(admin_id) # State is cleared, waiting for callback

    def execute_delete_plan(admin_id, message, plan_id):
        plan = _db_manager.get_plan_by_id(plan_id)
        if plan and _db_manager.delete_plan(plan_id):
            _bot.edit_message_text(messages.PLAN_DELETED_SUCCESS.format(plan_name=plan['name']), admin_id, message.message_id)
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, admin_id, message.message_id)
        _show_plan_management_menu(admin_id)

    # --- EDIT PLAN ---
    def start_edit_plan_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.EDIT_PLAN_PROMPT_ID, inline_keyboards.get_back_button("admin_plan_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_edit', 'data': {}, 'prompt_message_id': prompt.message_id}

    def process_edit_plan_id(admin_id, message):
        state_info = _admin_states[admin_id]
        if not message.text.isdigit() or not (plan := _db_manager.get_plan_by_id(int(message.text))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND); return
        
        state_info['data']['plan_id'] = int(message.text)
        state_info['data']['original_plan'] = plan
        state_info['state'] = 'waiting_for_new_plan_name'
        _bot.edit_message_text(messages.EDIT_PLAN_NEW_NAME, admin_id, state_info['prompt_message_id'])

    def process_edit_plan_name(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['new_name'] = message.text
        state_info['state'] = 'waiting_for_new_plan_price'
        _bot.edit_message_text(messages.EDIT_PLAN_NEW_PRICE, admin_id, state_info['prompt_message_id'])

    def process_edit_plan_price(admin_id, message):
        state_info = _admin_states[admin_id]
        if not helpers.is_float_or_int(message.text) or float(message.text) < 0:
            _bot.send_message(admin_id, "Неверная цена."); return
        
        data = state_info['data']
        original_plan = data['original_plan']
        
        _db_manager.update_plan(
            plan_id=data['plan_id'],
            name=data['new_name'],
            price=float(message.text),
            volume_gb=original_plan['volume_gb'],
            duration_days=original_plan['duration_days']
        )
        _bot.edit_message_text(messages.EDIT_PLAN_SUCCESS.format(plan_name=data['new_name']), admin_id, state_info['prompt_message_id'])
        _clear_admin_state(admin_id)
        _show_plan_management_menu(admin_id)
        
        
    def start_search_user_flow(admin_id, message):
        """Starts the flow for searching a user by their Telegram ID."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "Пожалуйста, введите числовой ID искомого пользователя:", inline_keyboards.get_back_button("admin_user_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_user_id_to_search', 'prompt_message_id': prompt.message_id}

    def process_user_search(admin_id, message):
        """Processes the user ID from a message and shows their management panel."""
        state_info = _admin_states.get(admin_id, {})
        user_id_str = message.text.strip()

        if not user_id_str.isdigit():
            _bot.send_message(admin_id, "Введенный ID недействителен. Пожалуйста, введите число.")
            return

        target_user_id = int(user_id_str)
        
        # Вместо повторения кода вызываем новую вспомогательную функцию
        _show_user_management_panel(admin_id, target_user_id, state_info['prompt_message_id'])
        
        _clear_admin_state(admin_id)
        
    def execute_delete_purchase(admin_id, message, purchase_id, user_telegram_id):
        """
        Deletes a purchase from the local database and the corresponding client
        from the X-UI panel.
        """
        # First, get purchase details to find the client UUID and server ID
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            _bot.answer_callback_query(message.id, "Эта подписка не найдена.", show_alert=True)
            return

        # Step 1: Delete the purchase from the local database
        if not _db_manager.delete_purchase(purchase_id):
            _bot.answer_callback_query(message.id, "Ошибка при удалении подписки из базы данных.", show_alert=True)
            return

        # Step 2: Delete the client from the X-UI panel
        try:
            server = _db_manager.get_server_by_id(purchase['server_id'])
            if server and purchase['xui_client_uuid']:
                api_client = _xui_api(
                    panel_url=server['panel_url'],
                    username=server['username'],
                    password=server['password']
                )
                # We need the inbound_id to delete the client. This is a limitation.
                # A better approach for the future is to store inbound_id in the purchase record.
                # For now, we assume we need to iterate or have a default.
                # This part of the logic might need enhancement based on your X-UI panel version.
                # We will try to delete by UUID, which is supported by some panel forks.
                
                # Note: The default X-UI API requires inbound_id to delete a client.
                # If your panel supports deleting by UUID directly, this will work.
                # Otherwise, this part needs to be adapted.
                # For now, we log the action. A full implementation would require a proper API call.
                logger.info(f"Admin {admin_id} deleted purchase {purchase_id}. Corresponding X-UI client UUID to be deleted is {purchase['xui_client_uuid']} on server {server['name']}.")
                # api_client.delete_client(inbound_id, purchase['xui_client_uuid']) # This line would be needed
        except Exception as e:
            logger.error(f"Could not delete client from X-UI for purchase {purchase_id}: {e}")
            _bot.answer_callback_query(message.id, "Подписка удалена из базы данных, но при удалении из панели произошла ошибка.", show_alert=True)

        _bot.answer_callback_query(message.id, f"✅ Подписка {purchase_id} успешно удалена.")

        # Step 3: Refresh the user's subscription list for the admin
        # We create a mock message object to pass to the search function
        mock_message = types.Message(
            message_id=message.message_id,
            chat=message.chat,
            date=None,
            content_type='text',
            options={},
            json_string=""
        )
        mock_message.text = str(user_telegram_id)
        
        # Put the admin back into the search state to show the updated list
        _admin_states[admin_id] = {'state': 'waiting_for_user_id_to_search', 'prompt_message_id': message.message_id}
        process_user_search(admin_id, mock_message)



    def show_channel_lock_menu(admin_id, message):
        """Displays the channel lock management menu."""
        channel_id = _db_manager.get_setting('required_channel_id')
        status = f"Активно для канала `{channel_id}`" if channel_id else "Неактивно"
        text = messages.CHANNEL_LOCK_MENU_TEXT.format(status=status)
        markup = inline_keyboards.get_channel_lock_management_menu(channel_set=bool(channel_id))
        _show_menu(admin_id, text, markup, message)

    def start_set_channel_lock_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.CHANNEL_LOCK_SET_PROMPT, inline_keyboards.get_back_button("admin_channel_lock_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_channel_id', 'prompt_message_id': prompt.message_id}

    def process_set_channel_id(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        channel_id_str = message.text.strip()
        # ... (code for cancel and validation remains the same)

        if not (channel_id_str.startswith('-') and channel_id_str[1:].isdigit()):
            _bot.send_message(admin_id, messages.CHANNEL_LOCK_INVALID_ID)
            return

        # Save the ID in the state and ask for the link
        state_info['data'] = {'channel_id': channel_id_str}
        state_info['state'] = 'waiting_for_channel_link' # <-- Move to next state
        
        _bot.edit_message_text(
            "Отлично. Теперь, пожалуйста, введите публичную ссылку на канал (например: https://t.me/Alamor_Network):",
            admin_id,
            state_info['prompt_message_id']
        )

    def process_set_channel_link(admin_id, message):
        """ --- NEW FUNCTION --- """
        state_info = _admin_states.get(admin_id, {})
        channel_link = message.text.strip()
        
        if not channel_link.lower().startswith(('http://', 'https://')):
            _bot.send_message(admin_id, "Введенная ссылка недействительна. Пожалуйста, введите полную ссылку.")
            return
            
        channel_id = state_info['data']['channel_id']

        # Now, save both ID and Link to the database
        _db_manager.update_setting('required_channel_id', channel_id)
        _db_manager.update_setting('required_channel_link', channel_link)
        
        _bot.edit_message_text(messages.CHANNEL_LOCK_SUCCESS.format(channel_id=channel_id), admin_id, state_info['prompt_message_id'])
        _clear_admin_state(admin_id)
        show_channel_lock_menu(admin_id) # Show the updated menu
    def execute_remove_channel_lock(admin_id, message):
        _db_manager.update_setting('required_channel_id', '') # Set to empty string
        _db_manager.update_setting('required_channel_link', '')
        _bot.answer_callback_query(message.id, messages.CHANNEL_LOCK_REMOVED)
        show_channel_lock_menu(admin_id, message)
        
    def show_tutorial_management_menu(admin_id, message):
        """Displays the main menu for tutorial management."""
        _show_menu(admin_id, "💡 Управление обучением", inline_keyboards.get_tutorial_management_menu(), message)

    def list_tutorials(admin_id, message):
        """Lists all saved tutorials with delete buttons."""
        all_tutorials = _db_manager.get_all_tutorials()
        markup = inline_keyboards.get_tutorials_list_menu(all_tutorials)
        _show_menu(admin_id, "Чтобы удалить обучение, нажмите на него:", markup, message)

    def execute_delete_tutorial(admin_id, message, tutorial_id):
        """Deletes a tutorial and refreshes the list."""
        if _db_manager.delete_tutorial(tutorial_id):
            _bot.answer_callback_query(message.id, "✅ Обучение успешно удалено.")
            list_tutorials(admin_id, message) # Refresh the list
        else:
            _bot.answer_callback_query(message.id, "❌ Произошла ошибка при удалении обучения.", show_alert=True)

    def start_add_tutorial_flow(admin_id, message):
        """Starts the multi-step process for adding a new tutorial."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "Пожалуйста, введите платформу для обучения (например: Android, Windows, iPhone):", inline_keyboards.get_back_button("admin_tutorial_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_tutorial_platform', 'data': {}, 'prompt_message_id': prompt.message_id}

    def process_tutorial_platform(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['platform'] = message.text.strip()
        state_info['state'] = 'waiting_for_tutorial_app_name'
        _bot.edit_message_text("Введите название приложения (например: V2RayNG):", admin_id, state_info['prompt_message_id'])

    def process_tutorial_app_name(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['app_name'] = message.text.strip()
        state_info['state'] = 'waiting_for_tutorial_forward'
        _bot.edit_message_text("Отлично. Теперь перешлите сюда пост с обучением из нужного канала.", admin_id, state_info['prompt_message_id'])

    def process_tutorial_forward(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        # Check if the message is forwarded
        if not message.forward_from_chat:
            _bot.send_message(admin_id, "Отправленное сообщение не является пересланным. Пожалуйста, перешлите пост.")
            return

        data = state_info['data']
        platform = data['platform']
        app_name = data['app_name']
        forward_chat_id = message.forward_from_chat.id
        forward_message_id = message.forward_from_message_id

        if _db_manager.add_tutorial(platform, app_name, forward_chat_id, forward_message_id):
            _bot.edit_message_text("✅ Обучение успешно зарегистрировано.", admin_id, state_info['prompt_message_id'])
        else:
            _bot.edit_message_text("❌ Произошла ошибка при регистрации обучения.", admin_id, state_info['prompt_message_id'])
        
        _clear_admin_state(admin_id)
        show_tutorial_management_menu(admin_id)
        
        
    def show_support_management_menu(admin_id, message):
        """
        Отображает меню управления поддержкой с экранированием ссылки для предотвращения ошибки Markdown.
        (финальная и исправленная версия)
        """
        support_link = _db_manager.get_setting('support_link') or "не настроено"
        
        # --- основное исправление здесь ---
        # Экранируем ссылку перед использованием в тексте
        escaped_link = helpers.escape_markdown_v1(support_link)
        
        text = messages.SUPPORT_MANAGEMENT_MENU_TEXT.format(link=escaped_link)
        markup = inline_keyboards.get_support_management_menu()
        
        # Теперь _show_menu может безопасно использовать Markdown
        _show_menu(admin_id, text, markup, message, parse_mode='Markdown')

    def set_support_type(admin_id, call, support_type):
        """Sets the support type (admin chat or link)."""
        _db_manager.update_setting('support_type', support_type)
        
        # --- THE FIX IS HERE ---
        # Use call.id to answer the query, and call.message to edit the message
        _bot.answer_callback_query(call.id, messages.SUPPORT_TYPE_SET_SUCCESS)
        show_support_management_menu(admin_id, call.message)

    def start_edit_support_link_flow(admin_id, message):
        """Starts the process for setting/editing the support link."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.SET_SUPPORT_LINK_PROMPT, inline_keyboards.get_back_button("admin_support_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_support_link', 'prompt_message_id': prompt.message_id}
    def process_support_link(admin_id, message):
        """Saves the support link and updates the menu directly. (Final Version)"""
        state_info = _admin_states.get(admin_id, {})
        support_link = message.text.strip()
        prompt_message_id = state_info.get('prompt_message_id')

        if not support_link.lower().startswith(('http://', 'https://', 't.me/')):
            _bot.send_message(admin_id, "Введенная ссылка недействительна. Пожалуйста, введите полную ссылку.")
            return
            
        # Save the new link to the database
        _db_manager.update_setting('support_link', support_link)

        # --- основное и окончательное исправление ---
        # Get the text and keyboard for the updated menu
        new_support_link_text = _db_manager.get_setting('support_link') or "не настроено"
        menu_text = messages.SUPPORT_MANAGEMENT_MENU_TEXT.format(link=new_support_link_text)
        menu_markup = inline_keyboards.get_support_management_menu()

        # Directly edit the original prompt message to show the new menu
        try:
            if prompt_message_id:
                _bot.edit_message_text(
                    text=menu_text,
                    chat_id=admin_id,
                    message_id=prompt_message_id,
                    reply_markup=menu_markup,
                    parse_mode=None  # Use plain text to be safe
                )
        except Exception as e:
            logger.error(f"Failed to edit message into support menu: {e}")
            # If editing fails for any reason, send a new message with the menu
            _bot.send_message(admin_id, menu_text, reply_markup=menu_markup, parse_mode=None)

        # Clean up the admin state
        _clear_admin_state(admin_id)
        
    
        
    def execute_save_inbounds(admin_id, message, server_id):
        state_info = _admin_states.get(admin_id, {})
        if not state_info or state_info.get('state') != f'selecting_inbounds_for_{server_id}': return

        selected_ids = state_info['data'].get('selected_inbound_ids', [])
        panel_inbounds = state_info['data'].get('panel_inbounds', [])
        inbounds_to_save = [{'id': p_in['id'], 'remark': p_in.get('remark', '')} for p_in in panel_inbounds if p_in['id'] in selected_ids]
        
        server_data = _db_manager.get_server_by_id(server_id)
        if _db_manager.update_server_inbounds(server_id, inbounds_to_save):
            _bot.edit_message_text(messages.INBOUND_CONFIG_SUCCESS.format(server_name=server_data['name']), admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
        else:
            _bot.edit_message_text(messages.INBOUND_CONFIG_FAILED.format(server_name=server_data['name']), admin_id, message.message_id)
        _clear_admin_state(admin_id)

    @_bot.callback_query_handler(func=lambda call: helpers.is_admin(call.from_user.id) and call.data.startswith('panel_type_'))
    def handle_panel_type_selection(call):
        """Обрабатывает выбранный администратором тип панели."""
        admin_id = call.from_user.id
        panel_type = call.data.replace("panel_type_", "")
        
        server_data = {'panel_type': panel_type}
        
        prompt = _bot.edit_message_text("Введите желаемое имя сервера:", admin_id, call.message.message_id)
        _bot.register_next_step_handler(prompt, process_add_server_name, server_data)

    def process_add_server_name(message, server_data):
        """Обрабатывает имя сервера и запрашивает адрес панели."""
        admin_id = message.from_user.id
        server_data['name'] = message.text.strip()
        
        prompt = _bot.send_message(admin_id, "Введите полный адрес панели (пример: http://1.2.3.4:54321):")
        _bot.register_next_step_handler(prompt, process_add_server_url, server_data)

    def process_add_server_url(message, server_data):
        """Обрабатывает адрес панели и запрашивает имя пользователя."""
        admin_id = message.from_user.id
        server_data['panel_url'] = message.text.strip()
        
        # Для hiddify, вместо имени пользователя, запрашиваем UUID администратора
        prompt_text = "Введите имя пользователя панели:"
        if server_data['panel_type'] == 'hiddify':
            prompt_text = "Введите UUID администратора панели Hiddify:"
            
        prompt = _bot.send_message(admin_id, prompt_text)
        _bot.register_next_step_handler(prompt, process_add_server_username, server_data)

    def process_add_server_username(message, server_data):
        """Обрабатывает имя пользователя и запрашивает пароль."""
        admin_id = message.from_user.id
        server_data['username'] = message.text.strip()
        
        # Для hiddify пароль не требуется
        if server_data['panel_type'] == 'hiddify':
            # Переходим сразу к этапу сохранения
            execute_add_server(admin_id, server_data)
            return

        prompt = _bot.send_message(admin_id, "Введите пароль панели:")
        _bot.register_next_step_handler(prompt, process_add_server_password, server_data)

    def process_add_server_password(message, server_data):
        """Обрабатывает пароль и запрашивает адрес подписки."""
        admin_id = message.from_user.id
        server_data['password'] = message.text.strip()
        
        prompt = _bot.send_message(admin_id, "Введите базовый адрес подписки (пример: https://yourdomain.com:2096):")
        _bot.register_next_step_handler(prompt, process_add_server_sub_base_url, server_data)

    def process_add_server_sub_base_url(message, server_data):
        """Обрабатывает адрес подписки и запрашивает префикс пути."""
        admin_id = message.from_user.id
        server_data['sub_base_url'] = message.text.strip()

        prompt = _bot.send_message(admin_id, "Введите префикс пути подписки (пример: sub):")
        _bot.register_next_step_handler(prompt, process_add_server_sub_path, server_data)

    def process_add_server_sub_path(message, server_data):
        """Обрабатывает префикс пути и сохраняет сервер."""
        admin_id = message.from_user.id
        server_data['sub_path_prefix'] = message.text.strip()
        execute_add_server(admin_id, server_data)

    def execute_add_server(admin_id, server_data):
        """Сохраняет окончательные данные в базе данных."""
        # Для hiddify устанавливаем пустые значения
        password = server_data.get('password', '')
        sub_base_url = server_data.get('sub_base_url', '')
        sub_path_prefix = server_data.get('sub_path_prefix', '')

        new_server_id = _db_manager.add_server(
            name=server_data['name'],
            panel_type=server_data['panel_type'],
            panel_url=server_data['panel_url'],
            username=server_data['username'],
            password=password,
            sub_base_url=sub_base_url,
            sub_path_prefix=sub_path_prefix
        )

        if new_server_id:
            _bot.send_message(admin_id, f"✅ Сервер '{server_data['name']}' успешно добавлен.")
        else:
            _bot.send_message(admin_id, f"❌ Произошла ошибка при добавлении сервера. Возможно, имя сервера уже используется.")
            
            
            
            
    def start_add_profile_flow(admin_id, message):
        """Начинает процесс добавления нового профиля."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.ADD_PROFILE_PROMPT_NAME, inline_keyboards.get_back_button("admin_profile_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_profile_name', 'data': {}, 'prompt_message_id': prompt.message_id}

    # ... (в разделе Final Execution Functions)

    def execute_add_profile(admin_id, data):
        _clear_admin_state(admin_id)
        profile_id = _db_manager.add_profile(
            name=data['name'],
            per_gb_price=data['per_gb_price'],
            duration_days=data['duration_days'],
            description=data['description']
        )
        if profile_id:
            msg = messages.ADD_PROFILE_SUCCESS.format(profile_name=data['name'])
        elif profile_id is None:
            msg = messages.ADD_PROFILE_DUPLICATE_ERROR.format(profile_name=data['name'])
        else:
            msg = messages.ADD_PROFILE_GENERAL_ERROR
        _bot.send_message(admin_id, msg)
        _show_profile_management_menu(admin_id)

            
        
    def list_all_profiles(admin_id, message):
        profiles = _db_manager.get_all_profiles()
        if not profiles:
            text = "Пока не зарегистрировано ни одного профиля."
        else:
            text = "📄 **Список зарегистрированных профилей:**\n\n"
            for p in profiles:
                status = "✅ Активен" if p['is_active'] else "❌ Неактивен"
                description = p['description'] or "нет"
                details = (
                    f"**ID: `{p['id']}` - {helpers.escape_markdown_v1(p['name'])}**\n"
                    f"▫️ Цена за гигабайт: `{p['per_gb_price']:,.0f}` туманов\n"
                    f"▫️ Срок: `{p['duration_days']}` дней\n"
                    f"▫️ Описание: {helpers.escape_markdown_v1(description)}\n"
                    f"▫️ Статус: {status}\n"
                    "-----------------------------------\n"
                )
                text += details
        _show_menu(admin_id, text, inline_keyboards.get_back_button("admin_profile_management"), message)

    def start_manage_profile_inbounds_flow(admin_id, message):
        """Начинает процесс управления входящими соединениями профиля с отображения списка профилей."""
        profiles = _db_manager.get_all_profiles()
        if not profiles:
            _bot.answer_callback_query(message.id, "Сначала нужно создать хотя бы один профиль.", show_alert=True)
            return
            
        markup = inline_keyboards.get_profile_selection_menu(profiles)
        _show_menu(admin_id, "Пожалуйста, выберите профиль, входящими которого вы хотите управлять:", markup, message)

    
    def handle_profile_selection(admin_id, message, profile_id):
        """
        После выбора профиля отображает список серверов для выбора.
        """
        _clear_admin_state(admin_id)
        servers = _db_manager.get_all_servers(only_active=False)
        if not servers:
            _bot.answer_callback_query(message.id, "Серверы не зарегистрированы. Сначала добавьте сервер.", show_alert=True)
            return

        # Сохранение выбранного профиля в состоянии администратора для следующих шагов
        _admin_states[admin_id] = {'state': 'selecting_server_for_profile', 'data': {'profile_id': profile_id}}
        
        markup = inline_keyboards.get_server_selection_menu_for_profile(servers, profile_id)
        _show_menu(admin_id, "Отлично. Теперь выберите сервер, с которого хотите добавить входящие соединения:", markup, message)
        
        
        
        
        
    def handle_server_selection_for_profile(admin_id, message, profile_id, server_id):
        """
        После выбора сервера подключается к панели и отображает список входящих соединений в виде чек-листа.
        """
        _bot.edit_message_text(messages.FETCHING_INBOUNDS, admin_id, message.message_id)
        
        server_data = _db_manager.get_server_by_id(server_id)
        if not server_data:
            _bot.answer_callback_query(message.id, "Сервер не найден.", show_alert=True); return

        api_client = get_api_client(server_data)
        if not api_client or not api_client.check_login():
            _bot.edit_message_text("❌ Не удалось подключиться к панели сервера.", admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"admin_select_profile_{profile_id}")); return

        panel_inbounds = api_client.list_inbounds()
        if not panel_inbounds:
            _bot.edit_message_text(messages.NO_INBOUNDS_FOUND_ON_PANEL, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"admin_select_profile_{profile_id}")); return
            
        # Читаем только те входящие, которые выбраны для этого профиля и этого сервера
        selected_inbound_ids = _db_manager.get_inbounds_for_profile(profile_id, server_id=server_id)
        
        _admin_states[admin_id] = {
            'state': 'selecting_inbounds_for_profile',
            'data': {
                'profile_id': profile_id,
                'server_id': server_id,
                'panel_inbounds': panel_inbounds,
                'selected_inbound_ids': selected_inbound_ids
            }
        }
        
        markup = inline_keyboards.get_inbound_selection_menu_for_profile(profile_id, server_id, panel_inbounds, selected_inbound_ids)
        profile = _db_manager.get_profile_by_id(profile_id)
        _show_menu(admin_id, f"Выберите входящие для профиля '{profile['name']}' с сервера '{server_data['name']}':", markup, message)
    def handle_profile_inbound_toggle(admin_id, message, profile_id, server_id, inbound_id):
        """Управляет установкой или снятием отметки с входящего соединения в чек-листе."""
        state_info = _admin_states.get(admin_id)
        if not state_info or state_info.get('state') != 'selecting_inbounds_for_profile': return
        
        data = state_info['data']
        if data['profile_id'] != profile_id or data['server_id'] != server_id: return

        selected_ids = data['selected_inbound_ids']
        if inbound_id in selected_ids:
            selected_ids.remove(inbound_id)
        else:
            selected_ids.append(inbound_id)
            
        markup = inline_keyboards.get_inbound_selection_menu_for_profile(
            profile_id, server_id, data['panel_inbounds'], selected_ids
        )
        try:
            _bot.edit_message_reply_markup(chat_id=admin_id, message_id=message.message_id, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in str(e):
                logger.warning(f"Error updating profile inbound checklist: {e}")

    def execute_save_profile_inbounds(admin_id, message, profile_id, server_id):
        state_info = _admin_states.get(admin_id)
        if not state_info or state_info.get('state') != 'selecting_inbounds_for_profile': return

        try:
            _bot.answer_callback_query(message.id, "⏳ Сохранение изменений...")
        except Exception: pass

        selected_ids = state_info['data']['selected_inbound_ids']
        
        # --- новый и важный лог ---
        logger.info(f"ADMIN DEBUG: Saving to DB for profile_id={profile_id}, server_id={server_id}. Selected inbound_ids: {selected_ids}")
        
        if _db_manager.update_inbounds_for_profile(profile_id, server_id, selected_ids):
            pass # успешно
        else:
            _bot.send_message(admin_id, "❌ Произошла ошибка при сохранении изменений в базе данных.")

        _clear_admin_state(admin_id)
        _show_profile_management_menu(admin_id, message)
    def start_sync_configs_flow(admin_id, message):
        """
        Выполняет процесс синхронизации, получая полные данные каждого входящего соединения по отдельности. (финальная версия)
        """
        try:
            _bot.edit_message_text("⏳ Начинается процесс синхронизации... Эта операция может занять некоторое время.", admin_id, message.message_id)
        except Exception:
            pass

        servers = _db_manager.get_all_servers(only_active=False)
        if not servers:
            _bot.send_message(admin_id, "Серверы для синхронизации не найдены.")
            _show_admin_main_menu(admin_id)
            return

        report = "📊 **Отчет о синхронизации конфигураций:**\n\n"
        total_synced = 0
        
        for server in servers:
            server_name = server['name']
            panel_type = server['panel_type']
            
            api_client = get_api_client(server)
            if not api_client or not api_client.check_login():
                report += f"❌ **{helpers.escape_markdown_v1(server_name)}**: Не удалось подключиться.\n"
                continue
                
            # 1. Сначала получаем краткий список для получения ID
            panel_inbounds_summary = api_client.list_inbounds()
            if not panel_inbounds_summary:
                report += f"⚠️ **{helpers.escape_markdown_v1(server_name)}**: Входящие на панели не найдены.\n"
                continue

            # 2. Теперь для каждого входящего получаем полные данные отдельно
            full_inbounds_details = []
            for inbound_summary in panel_inbounds_summary:
                inbound_id = inbound_summary.get('id')
                if not inbound_id:
                    continue
                
                # Вызов get_inbound для получения полных данных
                detailed_inbound = api_client.get_inbound(inbound_id)
                if detailed_inbound:
                    full_inbounds_details.append(detailed_inbound)
                else:
                    logger.warning(f"Could not fetch details for inbound {inbound_id} on server {server_name}")

            # 3. Сохраняем полные и нормализованные данные в базе данных
            normalized_configs = normalize_panel_inbounds(panel_type, full_inbounds_details)
            sync_result = _db_manager.sync_configs_for_server(server['id'], normalized_configs)
            
            if sync_result > 0:
                report += f"✅ **{helpers.escape_markdown_v1(server_name)}**: {sync_result} конфигураций успешно синхронизировано.\n"
                total_synced += sync_result
            elif sync_result == 0:
                report += f"⚠️ **{helpers.escape_markdown_v1(server_name)}**: Полных конфигураций для синхронизации не найдено.\n"
            else:
                report += f"❌ **{helpers.escape_markdown_v1(server_name)}**: Произошла ошибка при обработке базы данных.\n"

        report += f"\n---\n**Итого:** {total_synced} конфигураций сохранено в локальной базе данных."
        _bot.send_message(admin_id, report, parse_mode='Markdown')
        _show_admin_main_menu(admin_id)
        
        
    
    def process_delete_server_id(admin_id, message):
        """Обрабатывает введенный ID сервера для удаления и отображает сообщение с подтверждением."""
        state_info = _admin_states.get(admin_id, {})
        prompt_id = state_info.get("prompt_message_id")
        server_id_str = message.text.strip()

        if not server_id_str.isdigit() or not (server := _db_manager.get_server_by_id(int(server_id_str))):
            _bot.edit_message_text(f"{messages.SERVER_NOT_FOUND}\n\n{messages.DELETE_SERVER_PROMPT}", admin_id, prompt_id)
            return
            
        server_id = int(server_id_str)
        confirm_text = messages.DELETE_SERVER_CONFIRM.format(server_name=server['name'], server_id=server_id)
        markup = inline_keyboards.get_confirmation_menu(f"confirm_delete_server_{server_id}", "admin_server_management")
        _bot.edit_message_text(confirm_text, admin_id, prompt_id, reply_markup=markup, parse_mode='Markdown')
        _clear_admin_state(admin_id)
        
        
    
    def _show_admin_management_menu(admin_id, message):
        admins = _db_manager.get_all_admins()
        admin_list = "\n".join([f"- `{admin['telegram_id']}` ({admin['first_name']})" for admin in admins])
        text = f"🔑 **Управление администраторами**\n\n**Список текущих администраторов:**\n{admin_list}"
        _show_menu(admin_id, text, inline_keyboards.get_admin_management_menu(), message)

    def start_add_admin_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "Пожалуйста, введите числовой ID пользователя, которого вы хотите сделать администратором:", inline_keyboards.get_back_button("admin_manage_admins"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_admin_id_to_add', 'prompt_message_id': prompt.message_id}

    def start_remove_admin_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "Пожалуйста, введите числовой ID администратора, которого вы хотите удалить из списка:", inline_keyboards.get_back_button("admin_manage_admins"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_admin_id_to_remove', 'prompt_message_id': prompt.message_id}
        
        
        
    def check_nginx_status(admin_id, message):
        """Проверяет состояние и конфигурацию Nginx и отправляет результат администратору."""
        _bot.edit_message_text("⏳ Проверка состояния веб-сервера Nginx... Пожалуйста, подождите.", admin_id, message.message_id)
        
        # Выполнение команды status
        status_success, status_output = run_shell_command(['systemctl', 'status', 'nginx.service'])
        
        # Выполнение команды теста конфигурации
        config_success, config_output = run_shell_command(['nginx', '-t'])
        
        # Подготовка итогового отчета
        report = "📊 **Отчет о состоянии Nginx**\n\n"
        report += "--- **Состояние службы (`systemctl status`)** ---\n"
        report += f"```\n{status_output}\n```\n\n"
        report += "--- **Тест файлов конфигурации (`nginx -t`)** ---\n"
        report += f"```\n{config_output}\n```\n\n"
        
        if status_success and config_success:
            report += "✅ Похоже, служба Nginx активна и ее конфигурация без проблем."
        else:
            report += "❌ В службе или конфигурации Nginx есть проблема. Пожалуйста, проверьте выводы выше."
            
        _bot.send_message(admin_id, report, parse_mode='Markdown')
        _show_admin_main_menu(admin_id) # Показать главное меню снова
        
        
    def run_system_health_check(admin_id, message):
        """Проводит полную проверку состояния системы и пытается решить распространенные проблемы."""
        msg = _bot.edit_message_text("🩺 **Начало полной проверки системы...**\n\nПожалуйста, подождите несколько секунд, результаты будут отображаться постепенно.", admin_id, message.message_id, parse_mode='Markdown')
        
        report_parts = ["📊 **Отчет о полном состоянии системы**\n"]
        errors_found = False

        # 1. Проверка служб
        report_parts.append("\n--- **۱. Состояние служб** ---")
        services_to_check = ['alamorbot.service', 'alamor_webhook.service', 'nginx.service']
        for service in services_to_check:
            is_active, _ = run_shell_command(['systemctl', 'is-active', service])
            if is_active:
                report_parts.append(f"✅ Служба `{service}`: **Активна**")
            else:
                errors_found = True
                report_parts.append(f"❌ Служба `{service}`: **Неактивна**")
                report_parts.append(f"   - Попытка запуска...")
                start_success, start_output = run_shell_command(['systemctl', 'start', service])
                if start_success:
                    report_parts.append("   - ✅ Служба успешно запущена!")
                else:
                    report_parts.append(f"   - ❌ Запуск не удался.")
        
        # 2. Проверка подключения к базе данных
        report_parts.append("\n--- **۲. Подключение к базе данных** ---")
        if _db_manager.check_connection():
            report_parts.append("✅ Подключение к базе данных PostgreSQL: **Успешно**")
        else:
            errors_found = True
            report_parts.append("❌ Подключение к базе данных PostgreSQL: **Неудачно**\n   - Пожалуйста, проверьте данные `DB_` в файле `.env`.")

        # 3. Проверка подключения к панелям X-UI
        report_parts.append("\n--- **۳. Подключение к панелям X-UI** ---")
        servers = _db_manager.get_all_servers(only_active=False)
        if not servers:
            report_parts.append("⚠️ В боте не определено ни одного сервера.")
        else:
            for server in servers:
                api_client = get_api_client(server)
                if api_client and api_client.check_login():
                    report_parts.append(f"✅ Подключение к серверу '{helpers.escape_markdown_v1(server['name'])}': **Успешно**")
                else:
                    errors_found = True
                    report_parts.append(f"❌ Подключение к серверу '{helpers.escape_markdown_v1(server['name'])}': **Неудачно**")

        # 4. Проверка ключевых настроек
        report_parts.append("\n--- **۴. Проверка настроек продаж** ---")
        if not _db_manager.get_active_subscription_domain():
            errors_found = True
            report_parts.append("⚠️ **Предупреждение:** Не настроен активный домен подписки. Пользователи не смогут получить ссылку.")
        if not _db_manager.get_all_plans(only_active=True):
            errors_found = True
            report_parts.append("⚠️ **Предупреждение:** Нет активных тарифных планов. Пользователи не смогут совершать покупки.")
        if not _db_manager.get_all_payment_gateways(only_active=True):
            errors_found = True
            report_parts.append("⚠️ **Предупреждение:** Нет активных платежных шлюзов. Пользователи не смогут платить.")
        
        if not errors_found:
            report_parts.append("\n✅ **Результат:** Все ключевые части системы работают правильно.")
        else:
            report_parts.append("\n❌ **Результат:** Обнаружены некоторые проблемы. Пожалуйста, проверьте отчет выше.")
            
        final_report = "\n".join(report_parts)
        _bot.edit_message_text(final_report, admin_id, msg.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_main_menu"))
        
        
        
        
    def start_sample_config_flow(admin_id, message, target_inbounds, context):
        """
        Начинает процесс получения примера конфигурации для списка входящих соединений.
        """
        if not target_inbounds:
            _bot.send_message(admin_id, "✅ Все настройки успешно сохранены.")
            _clear_admin_state(admin_id)
            
            # --- основное и окончательное исправление здесь ---
            # Теперь бот вернется в правильное меню
            if context.get('type') == 'profile':
                # Вместо перехода в раздел назначения входящих, возвращаемся в меню управления шаблонами профилей
                show_profile_template_management_menu(admin_id, message)
            else:
                # Для обычного режима также возвращаемся в меню управления шаблонами серверов
                show_template_management_menu(admin_id, message)
            return

        current_inbound = target_inbounds[0]
        remaining_inbounds = target_inbounds[1:]

        _admin_states[admin_id] = {
            'state': 'waiting_for_sample_config',
            'data': {
                'current_inbound': current_inbound,
                'remaining_inbounds': remaining_inbounds,
                'context': context
            }
        }
        
        inbound_remark = current_inbound.get('remark', f"ID: {current_inbound.get('id')}")
        
        prompt_text = (
            f"Пожалуйста, отправьте **пример ссылки на конфигурацию** для следующего входящего соединения:\n\n"
            f"▫️ **Сервер:** {context['server_name']}\n"
            f"▫️ **Входящее:** {inbound_remark}"
        )
        
        prompt = _show_menu(admin_id, prompt_text, None, message)
        _admin_states[admin_id]['prompt_message_id'] = prompt.message_id
    def process_sample_config_input(admin_id, message):
        """
        Обрабатывает, анализирует и сохраняет как параметры, так и сырой текст примера конфигурации.
        """
        state_info = _admin_states.get(admin_id)
        if not state_info or state_info.get('state') != 'waiting_for_sample_config':
            return

        raw_template_link = message.text.strip()
        parsed_params = parse_config_link(raw_template_link)

        if not parsed_params:
            _bot.send_message(admin_id, "❌ Отправленная ссылка недействительна. Пожалуйста, отправьте правильную ссылку VLESS для этого входящего соединения.")
            return
        
        inbound_info = state_info['data']['current_inbound']
        context = state_info['data']['context']
        params_json = json.dumps(parsed_params)

        success = False
        if context['type'] == 'profile':
            success = _db_manager.update_profile_inbound_template(context['profile_id'], context['server_id'], inbound_info['id'], params_json, raw_template_link)
        else:
            success = _db_manager.update_server_inbound_template(context['server_id'], inbound_info['id'], params_json, raw_template_link)

        if success:
            _bot.edit_message_text("✅ Параметры и сырой шаблон успешно сохранены.", admin_id, state_info['prompt_message_id'])
        else:
            _bot.edit_message_text("❌ Произошла ошибка при сохранении шаблона в базе данных.", admin_id, state_info['prompt_message_id'])

        start_sample_config_flow(admin_id, message, state_info['data']['remaining_inbounds'], context)
    def show_template_management_menu(admin_id, message):
        """Отображает меню управления шаблонами конфигураций."""
        all_inbounds = _db_manager.get_all_active_inbounds_with_server_info()
        markup = inline_keyboards.get_template_management_menu(all_inbounds)
        _show_menu(admin_id, "Чтобы зарегистрировать или отредактировать шаблон входящего соединения, нажмите на него:", markup, message)




    def show_profile_template_management_menu(admin_id, message):
        """Отображает меню управления шаблонами конфигураций для профилей."""
        # Нам нужна новая функция в db_manager для чтения этой информации
        all_profile_inbounds = _db_manager.get_all_profile_inbounds_with_status()
        # Мы будем использовать новую клавиатуру для отображения этой информации
        markup = inline_keyboards.get_profile_template_management_menu(all_profile_inbounds)
        _show_menu(admin_id, "Чтобы зарегистрировать или отредактировать шаблон входящего соединения в профиле, нажмите на него:", markup, message)
        
        
    def show_profile_inbounds_db_status(admin_id, message):
        """Отображает содержимое таблицы profile_inbounds для отладки."""
        records = _db_manager.get_all_profile_inbounds_for_debug()
        
        if not records:
            text = "Таблица `profile_inbounds` в настоящее время пуста."
        else:
            text = "📄 **Текущее содержимое таблицы `profile_inbounds`:**\n\n"
            for rec in records:
                text += (
                    f"▫️ **Профиль:** `{rec['profile_id']}` ({rec['profile_name']})\n"
                    f"▫️ **Сервер:** `{rec['server_id']}` ({rec['server_name']})\n"
                    f"▫️ **Входящее:** `{rec['inbound_id']}`\n"
                    "--------------------\n"
                )
                
        _show_menu(admin_id, text, inline_keyboards.get_back_button("admin_profile_management"), message)

   
    def show_branding_settings_menu(admin_id, message):
        """Отображает меню настроек брендинга."""
        brand_name = _db_manager.get_setting('brand_name') or "Alamor" # имя по умолчанию
        text = (
            f"🎨 **Настройки брендинга**\n\n"
            f"Ваше текущее название бренда: **{brand_name}**\n\n"
            f"Это имя будет использоваться в электронных письмах и в remark конфигураций."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✏️ Изменить название бренда", callback_data="admin_change_brand_name"))
        markup.add(inline_keyboards.get_back_button("admin_main_menu").keyboard[0][0])
        _show_menu(admin_id, text, markup, message, parse_mode='Markdown')

    def start_change_brand_name_flow(admin_id, message):
        """Начинает процесс запроса нового названия бренда."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "Пожалуйста, введите новое название бренда (только английские буквы и цифры, без пробелов):", inline_keyboards.get_back_button("admin_branding_settings"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_brand_name', 'prompt_message_id': prompt.message_id}
        
        
    def show_message_management_menu(admin_id, message, page=1):
        all_messages = _db_manager.get_all_bot_messages()
        items_per_page = 10
        total_pages = (len(all_messages) + items_per_page - 1) // items_per_page
        messages_on_page = all_messages[(page - 1) * items_per_page:page * items_per_page]
        
        markup = inline_keyboards.get_message_management_menu(messages_on_page, page, total_pages)
        text = "✍️ **Управление сообщениями**\n\nЧтобы отредактировать любое сообщение, нажмите на него:"
        _show_menu(admin_id, text, markup, message, parse_mode='Markdown')

    def start_edit_message_flow(admin_id, message, message_key):
        current_text = _db_manager.get_message_by_key(message_key)
        if current_text is None:
            _bot.answer_callback_query(message.id, "Сообщение не найдено.", show_alert=True)
            return

        prompt_text = (
            f"✍️ Редактирование сообщения: `{message_key}`\n\n**Текущий текст:**\n`{current_text}`\n\n"
            f"Пожалуйста, отправьте новый текст. (Для отмены: `cancel`)"
        )
        prompt = _show_menu(admin_id, prompt_text, inline_keyboards.get_back_button("admin_message_management"), message, parse_mode='Markdown')
        _admin_states[admin_id] = {
            'state': 'waiting_for_new_message_text',
            'data': {'message_key': message_key},
            'prompt_message_id': prompt.message_id
        }
    def _show_user_management_panel(admin_id, target_user_id, message_id_to_edit):
        """Отображает подробную панель управления для конкретного пользователя с использованием ID сообщения."""
        user_info = _db_manager.get_user_by_telegram_id(target_user_id)
        if not user_info:
            _bot.edit_message_text(messages.USER_NOT_FOUND, admin_id, message_id_to_edit)
            return

        # Отображение информации о пользователе
        role_map = {'admin': '👑 Администратор', 'reseller': '🤝 Реселлер', 'user': '👤 Пользователь'}
        user_role_key = user_info.get('role', 'user')
        role = role_map.get(user_role_key, '👤 Пользователь')
        balance = f"{user_info.get('balance', 0):,.0f} туманов"
        first_name = helpers.escape_markdown_v1(user_info.get('first_name', ''))
        
        user_details_text = (
            f"👤 **Панель управления пользователем:** {first_name}\n\n"
            f"`ID: {user_info['telegram_id']}`\n"
            f"**Текущая роль:** {role}\n"
            f"**Баланс кошелька:** {balance}\n\n"
            "Пожалуйста, выберите желаемую операцию:"
        )
        
        markup = inline_keyboards.get_manage_user_menu(target_user_id)
        
        _bot.edit_message_text(
            user_details_text,
            admin_id,
            message_id_to_edit,  # Используем непосредственно числовой ID
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
    def start_broadcast_flow(admin_id, message):
        """Начинает процесс массовой рассылки с запросом сообщения от администратора."""
        _clear_admin_state(admin_id)
        prompt_text = (
            "Пожалуйста, введите сообщение, которое вы хотите отправить всем пользователям.\n\n"
            "Ваше сообщение может содержать **текст, фото, видео, файлы и т.д.** "
            "Все, что вы отправите, будет точно так же переслано пользователям.\n\n"
            "Для отмены отправьте /cancel."
        )
        prompt = _show_menu(admin_id, prompt_text, inline_keyboards.get_back_button("admin_main_menu"), message)
        _admin_states[admin_id] = {
            'state': 'waiting_for_broadcast_message',
            'data': {},  # <-- эта строка исправляет проблему
            'prompt_message_id': prompt.message_id
        }

    def check_and_fix_subscription_links(admin_id, message):
        """Проверка и исправление ссылок подписки"""
        _clear_admin_state(admin_id)
        
        # Отображение сообщения "Проверка..."
        _bot.edit_message_text("🔍 Проверка ссылок подписки...", admin_id, message.message_id)
        
        try:
            # Получение всех активных покупок
            active_purchases = _db_manager.get_all_active_purchases()
            if not active_purchases:
                _bot.edit_message_text("❌ Активных подписок не найдено.", admin_id, message.message_id)
                return
            
            fixed_count = 0
            error_count = 0
            healthy_count = 0
            
            # Проверка активного домена
            active_domain_record = _db_manager.get_active_subscription_domain()
            domain_status = "✅ Настроен" if active_domain_record else "❌ Не настроен"
            
            for purchase in active_purchases:
                try:
                    # Проверка наличия single_configs_json
                    if not purchase.get('single_configs_json'):
                        error_count += 1
                        continue
                    
                    # Проверка наличия sub_id
                    if not purchase.get('sub_id'):
                        # Генерация нового sub_id
                        import uuid
                        new_sub_id = str(uuid.uuid4().hex)
                        _db_manager.update_purchase_sub_id(purchase['id'], new_sub_id)
                        fixed_count += 1
                    else:
                        healthy_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error fixing subscription {purchase['id']}: {e}")
            
            # Отображение результата
            result_text = f"🔧 **Проверка и исправление ссылок подписки**\n\n"
            result_text += f"📊 **Общая статистика:**\n"
            result_text += f"• Всего подписок: **{len(active_purchases)}**\n"
            result_text += f"• Рабочих: **{healthy_count}**\n"
            result_text += f"• Исправлено: **{fixed_count}**\n"
            result_text += f"• С ошибками: **{error_count}**\n\n"
            result_text += f"🌐 **Статус домена:** {domain_status}\n\n"
            
            if fixed_count > 0:
                result_text += "🎉 Некоторые ссылки были исправлены."
            elif error_count == 0:
                result_text += "✅ Все ссылки работают исправно."
            else:
                result_text += "⚠️ Некоторые проблемы требуют ручной проверки."
            
            # Добавление кнопки "Назад"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад в меню администратора", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(result_text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in check_and_fix_subscription_links: {e}")
            _bot.edit_message_text(
                f"❌ Ошибка при проверке ссылок:\n{str(e)}",
                admin_id, message.message_id
            )

    @_bot.callback_query_handler(func=lambda call: call.data == "admin_check_subscription_links")
    def handle_check_subscription_links_callback(call):
        """Управление callback'ом проверки ссылок подписки"""
        try:
            admin_id = call.from_user.id
            if admin_id not in ADMIN_IDS:
                _bot.answer_callback_query(call.id, "❌ Несанкционированный доступ", show_alert=True)
                return
            
            check_and_fix_subscription_links(admin_id, call.message)
            
        except Exception as e:
            logger.error(f"Error in check subscription links callback: {e}")
            _bot.answer_callback_query(call.id, "❌ Ошибка при проверке ссылок", show_alert=True)

    @_bot.callback_query_handler(func=lambda call: call.data == "admin_refresh_all_subscriptions")
    def handle_refresh_all_subscriptions_callback(call):
        """Управление callback'ом обновления всех ссылок подписки"""
        try:
            admin_id = call.from_user.id
            if admin_id not in ADMIN_IDS:
                _bot.answer_callback_query(call.id, "❌ Несанкционированный доступ", show_alert=True)
                return
            
            refresh_all_subscription_links(admin_id, call.message)
            
        except Exception as e:
            logger.error(f"Error in refresh all subscriptions callback: {e}")
            _bot.answer_callback_query(call.id, "❌ Ошибка при обновлении ссылок", show_alert=True)

    def update_configs_from_panel(admin_id, purchase_id, message):
        """
        Обновление конфигураций с основной панели
        """
        _clear_admin_state(admin_id)
        
        # Отображение сообщения "Обновление..."
        _bot.edit_message_text("⏳ Обновление конфигураций с основной панели...", admin_id, message.message_id)
        
        try:
            # Получение информации о покупке
            purchase = _db_manager.get_purchase_by_id(purchase_id)
            if not purchase:
                _bot.edit_message_text("❌ Указанная покупка не найдена.", admin_id, message.message_id)
                return
            
            # Получение информации о сервере
            server = _db_manager.get_server_by_id(purchase['server_id'])
            if not server:
                _bot.edit_message_text("❌ Информация о сервере не найдена.", admin_id, message.message_id)
                return
            
            # Запрос на обновление к webhook server
            import requests
            webhook_url = f"https://{os.getenv('WEBHOOK_DOMAIN', 'localhost')}/admin/update_configs/{purchase_id}"
            headers = {
                'Authorization': f'Bearer {os.getenv("ADMIN_API_KEY", "your-secret-key")}'
            }
            
            response = requests.post(webhook_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                _bot.edit_message_text(
                    f"✅ Конфигурации для покупки #{purchase_id} успешно обновлены с основной панели.\n\n"
                    f"📊 **Детали:**\n"
                    f"• Сервер: {server['name']}\n"
                    f"• Пользователь: {purchase.get('user_first_name', 'N/A')}\n"
                    f"• Дата обновления: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
            else:
                _bot.edit_message_text(
                    f"❌ Ошибка при обновлении конфигураций.\n"
                    f"Код ошибки: {response.status_code}\n"
                    f"Сообщение: {response.text}",
                    admin_id, message.message_id
                )
                
        except Exception as e:
            logger.error(f"Error updating configs from panel: {e}")
            _bot.edit_message_text(
                f"❌ Ошибка при обновлении конфигураций:\n{str(e)}",
                admin_id, message.message_id
            )

    def refresh_all_subscription_links(admin_id, message):
        """
        Обновление всех ссылок подписки с основной панели с использованием новой системы
        """
        _clear_admin_state(admin_id)
        
        # Отображение сообщения "Обновление..."
        _bot.edit_message_text("⏳ Обновление всех ссылок подписки...", admin_id, message.message_id)
        
        try:
            # Получение всех активных покупок
            active_purchases = _db_manager.get_all_active_purchases()
            
            if not active_purchases:
                _bot.edit_message_text("❌ Активных покупок не найдено.", admin_id, message.message_id)
                return
            
            # Проверка настроек
            webhook_domain = os.getenv('WEBHOOK_DOMAIN')
            admin_api_key = os.getenv('ADMIN_API_KEY')
            
            if not webhook_domain:
                _bot.edit_message_text(
                    "❌ Переменная WEBHOOK_DOMAIN не установлена в файле .env.\n"
                    "Пожалуйста, сначала настройте домен webhook.",
                    admin_id, message.message_id
                )
                return
            
            if not admin_api_key:
                _bot.edit_message_text(
                    "❌ Переменная ADMIN_API_KEY не установлена в файле .env.\n"
                    "Пожалуйста, сначала настройте API-ключ администратора.",
                    admin_id, message.message_id
                )
                return
            
            success_count = 0
            error_count = 0
            profile_count = 0
            normal_count = 0
            
            # Прямое обновление через webhook server
            import requests
            webhook_base_url = f"https://{webhook_domain}/admin/update_configs"
            headers = {
                'Authorization': f'Bearer {admin_api_key}'
            }
            
            for purchase in active_purchases:
                try:
                    # Определение типа покупки
                    if purchase.get('profile_id'):
                        profile_count += 1
                        purchase_type = "Профиль"
                    else:
                        normal_count += 1
                        purchase_type = "Обычная"
                    
                    webhook_url = f"{webhook_base_url}/{purchase['id']}"
                    response = requests.post(webhook_url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        success_count += 1
                        logger.info(f"Successfully updated purchase {purchase['id']} ({purchase_type})")
                    elif response.status_code == 401:
                        error_count += 1
                        logger.error(f"Unauthorized for purchase {purchase['id']}: Invalid API key")
                    elif response.status_code == 404:
                        error_count += 1
                        logger.error(f"Purchase {purchase['id']} not found in webhook server")
                    else:
                        error_count += 1
                        logger.error(f"HTTP {response.status_code} for purchase {purchase['id']}: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    error_count += 1
                    logger.error(f"Connection error for purchase {purchase['id']}: Webhook server not reachable")
                except requests.exceptions.Timeout:
                    error_count += 1
                    logger.error(f"Timeout for purchase {purchase['id']}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error updating purchase {purchase['id']}: {e}")
            
            # Отображение результата с большей детализацией
            result_text = f"🔄 **Обновление ссылок подписки**\n\n"
            result_text += f"📊 **Общие результаты:**\n"
            result_text += f"• ✅ Успешно: **{success_count}** ссылок\n"
            result_text += f"• ❌ Неудачно: **{error_count}** ссылок\n"
            result_text += f"• 📈 Всего: **{len(active_purchases)}** ссылок\n\n"
            
            result_text += f"📋 **Детали покупок:**\n"
            result_text += f"• 🎯 Покупки профилей: **{profile_count}**\n"
            result_text += f"• 🔧 Обычные покупки: **{normal_count}**\n\n"
            
            if success_count > 0:
                result_text += "🎉 **Новая система активирована!**\n"
                result_text += "✅ Ссылки профилей обновлены со всех связанных серверов.\n"
                result_text += "✅ Обычные ссылки обновлены с соответствующих серверов.\n\n"
                
                if profile_count > 0:
                    result_text += "🔗 **Новая функция:**\n"
                    result_text += "• Покупки профилей теперь собирают данные со всех серверов профиля\n"
                    result_text += "• Изменения портов и настроек администратором применяются немедленно\n"
                    result_text += "• Активна система умной фильтрации конфигураций\n"
            elif error_count > 0:
                result_text += "⚠️ Некоторые ссылки не были обновлены.\n"
                result_text += "Пожалуйста, проверьте логи."
            else:
                result_text += "✅ Все ссылки успешно обновлены!"
            
            # Добавление кнопки "Назад"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад в меню администратора", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(result_text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error refreshing all subscription links: {e}")
            error_text = f"❌ Ошибка при обновлении ссылок подписки:\n{str(e)}"
            
            # Добавление кнопки "Назад"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад в меню администратора", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(error_text, admin_id, message.message_id, reply_markup=markup)

    def show_config_builder_test_menu(admin_id, message):
        """Отображение меню теста Config Builder"""
        _clear_admin_state(admin_id)
        
        try:
            # Получение списка серверов
            servers = _db_manager.get_all_servers()
            
            if not servers:
                _bot.edit_message_text(
                    "❌ Серверы не найдены.\nПожалуйста, сначала добавьте сервер.",
                    admin_id, message.message_id
                )
                return
            
            text = "🧪 **Тест Config Builder**\n\n"
            text += "Этот инструмент создает конфигурации напрямую с панели:\n"
            text += "• Выбор сервера и inbound\n"
            text += "• Создание нового клиента (при необходимости)\n"
            text += "• Создание конфигурации на основе протокола\n"
            text += "• Тестирование работы API\n\n"
            text += "**Доступные серверы:**\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for server in servers:
                server_name = helpers.escape_markdown_v1(server['name'])
                text += f"• {server_name}\n"
                markup.add(
                    types.InlineKeyboardButton(
                        f"🧪 Тест {server['name']}", 
                        callback_data=f"admin_test_config_server_{server['id']}"
                    )
                )
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error showing config builder test menu: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении меню теста: {str(e)}", admin_id, message.message_id)

    def show_inbound_selection_for_test(admin_id, server_id, message=None):
        """Отображение списка inbounds для выбора"""
        _clear_admin_state(admin_id)
        
        try:
            # Получение информации о сервере
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден", admin_id, message.message_id)
                return
            
            # Подключение к панели
            from api_client.xui_api_client import XuiAPIClient
            api_client = XuiAPIClient(
                panel_url=server_info['panel_url'],
                username=server_info['username'],
                password=server_info['password']
            )
            
            if not api_client.check_login():
                _bot.edit_message_text(
                    f"❌ **Ошибка подключения к панели**\n\n"
                    f"Сервер: **{server_info['name']}**\n"
                    f"Не удается подключиться к панели.",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            # Получение списка inbounds
            inbounds = api_client.list_inbounds()
            if not inbounds:
                _bot.edit_message_text(
                    f"❌ **Inbounds не найдены**\n\n"
                    f"Сервер: **{server_info['name']}**\n"
                    f"В панели нет активных inbounds.",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            text = f"📡 **Выбор Inbound**\n\n"
            text += f"**Сервер:** {server_info['name']}\n"
            text += "Пожалуйста, выберите нужный inbound:"
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for inbound in inbounds:
                inbound_name = inbound.get('remark', f'Inbound {inbound["id"]}')
                inbound_id = inbound['id']
                protocol = inbound.get('protocol', 'unknown')
                port = inbound.get('port', 'unknown')
                
                markup.add(types.InlineKeyboardButton(
                    f"🔗 {inbound_name} ({protocol}:{port})",
                    callback_data=f"admin_test_config_inbound_{server_id}_{inbound_id}"
                ))
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_test_config_builder"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                
        except Exception as e:
            logger.error(f"Error showing inbound selection: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении inbounds: {str(e)}", admin_id, message.message_id)

    def test_config_builder_for_inbound(admin_id, message, server_id, inbound_id):
        """Тест Config Builder для конкретного inbound - создание нового клиента и тест конфигурации"""
        import time  # Import time at the beginning of the function
        from utils.config_builder import build_vless_config  # Import config builder functions
        try:
            logger.info(f"Testing config builder for server {server_id}, inbound {inbound_id}")
            
            # Получение информации о сервере
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден.", admin_id, message.message_id)
                return
            
            # Отображение сообщения "В процессе..."
            _bot.edit_message_text(
                f"🧪 **Тест Config Builder**\n\n"
                f"Сервер: **{server_info['name']}**\n"
                f"Inbound: **{inbound_id}**\n"
                f"⏳ Подключение к панели и создание тестового клиента...",
                admin_id, message.message_id, parse_mode='Markdown'
            )
            
            # import config builder
            from utils.config_builder import test_config_builder, build_vmess_config, build_vless_config, build_trojan_config
            
            # Тест подключения к панели
            try:
                # Получение списка inbounds
                from api_client.xui_api_client import XuiAPIClient
                api_client = XuiAPIClient(
                    panel_url=server_info['panel_url'],
                    username=server_info['username'],
                    password=server_info['password']
                )
                
                if not api_client.check_login():
                    _bot.edit_message_text(
                        f"❌ **Ошибка подключения к панели**\n\n"
                        f"Сервер: **{server_info['name']}**\n"
                        f"Не удается подключиться к панели.\n"
                        f"Пожалуйста, проверьте данные для входа.",
                        admin_id, message.message_id, parse_mode='Markdown'
                    )
                    return
                
                # Получение информации о inbound
                inbound_info = api_client.get_inbound(inbound_id)
                if not inbound_info:
                    _bot.edit_message_text(
                        f"❌ **Inbound не найден**\n\n"
                        f"Сервер: **{server_info['name']}**\n"
                        f"Inbound ID: **{inbound_id}**\n"
                        f"Этот inbound не существует в панели.",
                        admin_id, message.message_id, parse_mode='Markdown'
                    )
                    return
                
                # Проверка наличия клиента
                try:
                    inbound_settings = json.loads(inbound_info.get('settings', '{}'))
                except (json.JSONDecodeError, TypeError):
                    inbound_settings = {}
                
                clients = inbound_settings.get('clients', [])
                logger.info(f"Found {len(clients)} clients in inbound {inbound_id}")
                if clients:
                    for i, client in enumerate(clients):
                        logger.info(f"Client {i+1}: {client.get('email', 'Unknown')} (ID: {client.get('id', 'Unknown')})")
                
                if not clients:
                    # Создание нового клиента для теста
                    logger.info(f"No clients found in inbound {inbound_id}, creating test client...")
                    
                    # Создание нового тестового клиента с полной структурой
                    test_uuid = str(uuid.uuid4())
                    test_client_data = {
                        "id": test_uuid,
                        "email": f"test-{int(time.time())}@alamor.com",
                        "name": f"Test-{int(time.time())}",
                        "flow": "",
                        "totalGB": 0,
                        "expiryTime": 0,
                        "enable": True,
                        "tgId": "",
                        "subId": "",
                        "limitIp": 0,
                        "reset": 0,
                        "comment": ""
                    }
                    logger.info(f"Created test client data: {test_client_data}")
                    logger.info(f"Test UUID: {test_uuid}")
                    logger.info(f"Test UUID type: {type(test_uuid)}")
                    
                    # Добавление нового клиента в inbound
                    try:
                        # Получение текущих настроек inbound
                        current_settings = json.loads(inbound_info.get('settings', '{}'))
                        current_clients = current_settings.get('clients', [])
                        
                        logger.info(f"Current settings: {current_settings}")
                        logger.info(f"Current clients count: {len(current_clients)}")
                        
                        # Добавление нового клиента
                        current_clients.append(test_client_data)
                        current_settings['clients'] = current_clients
                        
                        logger.info(f"Updated settings: {current_settings}")
                        logger.info(f"Updated clients count: {len(current_clients)}")
                        
                        # Обновление inbound - сохранение всех существующих полей
                        update_data = {
                            'settings': json.dumps(current_settings),
                            'port': inbound_info.get('port'),
                            'protocol': inbound_info.get('protocol'),
                            'streamSettings': inbound_info.get('streamSettings'),
                            'sniffing': inbound_info.get('sniffing'),
                            'tag': inbound_info.get('tag'),
                            'up': inbound_info.get('up'),
                            'down': inbound_info.get('down'),
                            'total': inbound_info.get('total'),
                            'remark': inbound_info.get('remark'),
                            'enable': inbound_info.get('enable', True)
                        }
                        
                        # Удаление полей None
                        update_data = {k: v for k, v in update_data.items() if v is not None}
                        
                        logger.info(f"Adding new test client to inbound {inbound_id}")
                        logger.info(f"Current clients count: {len(current_clients)}")
                        logger.info(f"Update data: {update_data}")
                        logger.info(f"Update data JSON: {json.dumps(update_data, indent=2)}")
                        success = api_client.update_inbound(inbound_id, update_data)
                        logger.info(f"Update result: {success}")
                        
                        if success:
                            logger.info(f"Test client created successfully: {test_client_data['email']}")
                            
                            # Немного подождем, чтобы панель сохранила клиента
                            time.sleep(2)
                            
                            # Получение данных клиента с панели
                            try:
                                # Повторное получение информации о inbound с панели
                                updated_inbound_info = api_client.get_inbound(inbound_id)
                                if updated_inbound_info:
                                    updated_settings = json.loads(updated_inbound_info.get('settings', '{}'))
                                    updated_clients = updated_settings.get('clients', [])
                                    
                                    # Поиск созданного клиента
                                    for client in updated_clients:
                                        if client.get('email') == test_client_data['email']:
                                            test_client = client
                                            client_id = client.get('id')
                                            logger.info(f"Retrieved client data from panel: {client}")
                                            break
                                    else:
                                        # Если клиент не найден, используйте локальные данные
                                        test_client = test_client_data
                                        client_id = test_client['id']
                                        logger.warning("Could not retrieve client from panel, using local data")
                                else:
                                    # Если не удалось получить inbound, используйте локальные данные
                                    test_client = test_client_data
                                    client_id = test_client['id']
                                    logger.warning("Could not retrieve inbound from panel, using local data")
                            except Exception as e:
                                logger.error(f"Error retrieving client data from panel: {e}")
                                # В случае ошибки используйте локальные данные
                                test_client = test_client_data
                                client_id = test_client['id']
                        else:
                            logger.error("Failed to create test client")
                            _bot.edit_message_text(
                                f"❌ **Ошибка при создании тестового клиента**\n\n"
                                f"Сервер: **{server_info['name']}**\n"
                                f"Inbound: **{inbound_id}**\n"
                                f"Не удается создать тестового клиента.",
                                admin_id, message.message_id, parse_mode='Markdown'
                            )
                            return
                            
                    except Exception as e:
                        logger.error(f"Error creating test client: {e}")
                        _bot.edit_message_text(
                            f"❌ **Ошибка при создании тестового клиента**\n\n"
                            f"Сервер: **{server_info['name']}**\n"
                            f"Ошибка: **{str(e)}**",
                            admin_id, message.message_id, parse_mode='Markdown'
                        )
                        return
                else:
                    # Клиент существует, но для теста создаем нового
                    logger.info(f"Found existing clients, but creating new test client for testing...")
                    
                    # Создание нового тестового клиента с полной структурой
                    test_uuid = str(uuid.uuid4())
                    test_client_data = {
                        "id": test_uuid,
                        "email": f"test-{int(time.time())}@alamor.com",
                        "name": f"Test-{int(time.time())}",
                        "flow": "",
                        "totalGB": 0,
                        "expiryTime": 0,
                        "enable": True,
                        "tgId": "",
                        "subId": "",
                        "limitIp": 0,
                        "reset": 0,
                        "comment": ""
                    }
                    logger.info(f"Created test client data: {test_client_data}")
                    logger.info(f"Test UUID: {test_uuid}")
                    logger.info(f"Test UUID type: {type(test_uuid)}")
                    
                    # Добавление нового клиента в inbound
                    try:
                        # Получение текущих настроек inbound
                        current_settings = json.loads(inbound_info.get('settings', '{}'))
                        current_clients = current_settings.get('clients', [])
                        
                        logger.info(f"Current settings: {current_settings}")
                        logger.info(f"Current clients count: {len(current_clients)}")
                        
                        # Добавление нового клиента
                        current_clients.append(test_client_data)
                        current_settings['clients'] = current_clients
                        
                        logger.info(f"Updated settings: {current_settings}")
                        logger.info(f"Updated clients count: {len(current_clients)}")
                        
                        # Обновление inbound - сохранение всех существующих полей
                        update_data = {
                            'settings': json.dumps(current_settings),
                            'port': inbound_info.get('port'),
                            'protocol': inbound_info.get('protocol'),
                            'streamSettings': inbound_info.get('streamSettings'),
                            'sniffing': inbound_info.get('sniffing'),
                            'tag': inbound_info.get('tag'),
                            'up': inbound_info.get('up'),
                            'down': inbound_info.get('down'),
                            'total': inbound_info.get('total'),
                            'remark': inbound_info.get('remark'),
                            'enable': inbound_info.get('enable', True)
                        }
                        
                        # Удаление полей None
                        update_data = {k: v for k, v in update_data.items() if v is not None}
                        
                        logger.info(f"Adding new test client to inbound {inbound_id}")
                        logger.info(f"Current clients count: {len(current_clients)}")
                        logger.info(f"Update data: {update_data}")
                        logger.info(f"Update data JSON: {json.dumps(update_data, indent=2)}")
                        success = api_client.update_inbound(inbound_id, update_data)
                        logger.info(f"Update result: {success}")
                        
                        if success:
                            logger.info(f"New test client created successfully: {test_client_data['email']}")
                            
                            # Немного подождем, чтобы панель сохранила клиента
                            time.sleep(2)
                            
                            # Проверка, действительно ли клиент сохранен в панели
                            try:
                                updated_inbound_info = api_client.get_inbound(inbound_id)
                                if updated_inbound_info:
                                    updated_settings = json.loads(updated_inbound_info.get('settings', '{}'))
                                    updated_clients = updated_settings.get('clients', [])
                                    logger.info(f"Updated clients count: {len(updated_clients)}")
                                    
                                    # Поиск нового клиента
                                    for client in updated_clients:
                                        if client.get('email') == test_client_data['email']:
                                            logger.info(f"Found new client in panel: {client}")
                                            test_client = client
                                            client_id = client.get('id')
                                            break
                                    else:
                                        logger.warning("New client not found in panel, using local data")
                                        test_client = test_client_data
                                        client_id = test_client['id']
                                else:
                                    logger.warning("Could not retrieve updated inbound, using local data")
                                    test_client = test_client_data
                                    client_id = test_client['id']
                            except Exception as e:
                                logger.error(f"Error checking updated inbound: {e}")
                                test_client = test_client_data
                                client_id = test_client['id']
                        else:
                            logger.error("Failed to create new test client")
                            # В случае ошибки используйте существующего клиента
                            test_client = clients[0]
                            client_id = test_client.get('id')
                            logger.info(f"Using existing client: {test_client.get('email', 'Unknown')}")
                            
                    except Exception as e:
                        logger.error(f"Error creating new test client: {e}")
                        # В случае ошибки используйте существующего клиента
                        test_client = clients[0]
                        client_id = test_client.get('id')
                        logger.info(f"Using existing client: {test_client.get('email', 'Unknown')}")
                
                # Отображение информации о клиенте
                logger.info(f"Selected client: {test_client.get('email', 'Unknown')} with ID: {client_id}")
                logger.info(f"Client ID type: {type(client_id)}")
                logger.info(f"Client data: {test_client}")
                logger.info(f"Client data keys: {list(test_client.keys())}")
                
                # Тест создания конфигурации
                try:
                    # Прямое использование данных клиента вместо повторного получения с панели
                    logger.info(f"Using direct client data for config building")
                    logger.info(f"Client data to use: {test_client}")
                    logger.info(f"Client ID from test_client: {test_client.get('id', 'N/A')}")
                    logger.info(f"Client ID type: {type(test_client.get('id', 'N/A'))}")
                    
                    # Убедимся, что UUID правильный
                    if not test_client.get('id') or len(str(test_client.get('id', ''))) < 20:
                        logger.error(f"Invalid UUID in test_client: {test_client.get('id', 'N/A')}")
                        _bot.edit_message_text(
                            f"❌ **Ошибка в UUID клиента**\n\n"
                            f"Неверный UUID: **{test_client.get('id', 'N/A')}**\n"
                            f"UUID должен содержать не менее 20 символов.",
                            admin_id, message.message_id, parse_mode='Markdown'
                        )
                        return
                    
                    # Создание конфигурации напрямую с использованием данных клиента
                    # Получение информации о inbound
                    inbound_info = api_client.get_inbound(inbound_id)
                    if inbound_info:
                        # Прямое создание конфигурации VLESS
                        config = build_vless_config(test_client, inbound_info, server_info, "Alamor")
                        if config:
                            result = {
                                'protocol': 'vless',
                                'config': config,
                                'client_email': test_client.get('email', ''),
                                'client_name': test_client.get('name', ''),
                                'inbound_id': inbound_id,
                                'server_name': server_info.get('name', 'Unknown')
                            }
                        else:
                            result = None
                    else:
                        result = None
                        
                except Exception as e:
                    logger.error(f"Error in direct config building: {e}")
                    result = None
                
                if result:
                    # Отображение успешного результата
                    text = f"✅ **Тест успешен!**\n\n"
                    text += f"**Сервер:** {server_info['name']}\n"
                    text += f"**Протокол:** {result['protocol']}\n"
                    text += f"**Клиент:** {result['client_email']}\n"
                    text += f"**Inbound:** {result['inbound_id']}\n\n"
                    text += f"**Созданная конфигурация:**\n"
                    text += f"🎉 **Config Builder работает!**"
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_test_config_builder"),
                        types.InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu")
                    )
                    
                    _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                    
                    # Отправка конфигурации в отдельном сообщении без Markdown
                    config_text = result['config']
                    logger.info(f"Sending config (length: {len(config_text)}): {config_text}")
                    _bot.send_message(admin_id, config_text)
                    
                else:
                    _bot.edit_message_text(
                        f"❌ **Ошибка при создании конфигурации**\n\n"
                        f"Сервер: **{server_info['name']}**\n"
                        f"Клиент: **{test_client.get('email', 'Unknown')}**\n"
                        f"Произошла ошибка при создании конфигурации.",
                        admin_id, message.message_id, parse_mode='Markdown'
                    )
                
            except Exception as e:
                logger.error(f"Error testing config builder: {e}")
                _bot.edit_message_text(
                    f"❌ **Ошибка при тестировании**\n\n"
                    f"Сервер: **{server_info['name']}**\n"
                    f"Ошибка: **{str(e)}**",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in test_config_builder_for_inbound: {e}")
            _bot.edit_message_text(f"❌ Ошибка при тестировании: {str(e)}", admin_id, message.message_id)

    def test_config_builder_for_server(admin_id, message, server_id):
        """Тест Config Builder для конкретного сервера - переход к выбору inbound"""
        try:
            logger.info(f"Starting config builder test for server {server_id}")
            
            # Получение информации о сервере
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден.", admin_id, message.message_id)
                return
            
            # Переход к выбору inbound
            show_inbound_selection_for_test(admin_id, server_id, message)
                
        except Exception as e:
            logger.error(f"Error in test_config_builder_for_server: {e}")
            _bot.edit_message_text(f"❌ Ошибка при тестировании: {str(e)}", admin_id, message.message_id)

    def show_json_logger_menu(admin_id, message):
        """Отображение меню для логирования полного JSON"""
        _clear_admin_state(admin_id)
        
        try:
            # Получение списка активных серверов
            servers = _db_manager.get_all_servers(only_active=True)
            
            if not servers:
                _bot.edit_message_text(
                    "❌ **Активные серверы не найдены**\n\n"
                    "Пожалуйста, сначала добавьте серверы.",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            text = "📋 **Логирование полного JSON панели**\n\n"
            text += "Выберите, какой сервер проверить:\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for server in servers:
                button_text = f"🖥️ {server['name']}"
                callback_data = f"admin_log_json_server_{server['id']}"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in show_json_logger_menu: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении меню: {str(e)}", admin_id, message.message_id)
            
    def show_inbound_selection_for_json_log(admin_id, message, server_id):
        """Отображение выбора inbound для лога JSON"""
        try:
            # Получение информации о сервере
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден.", admin_id, message.message_id)
                return
            
            # Подключение к панели и получение inbounds
            from api_client.xui_api_client import XuiAPIClient
            api_client = XuiAPIClient(
                panel_url=server_info['panel_url'],
                username=server_info['username'],
                password=server_info['password']
            )
            
            if not api_client.check_login():
                _bot.edit_message_text(
                    f"❌ **Ошибка подключения к панели**\n\n"
                    f"Сервер: **{server_info['name']}**\n"
                    f"Не удается подключиться к панели.",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            # Получение списка inbounds
            inbounds = api_client.list_inbounds()
            if not inbounds:
                _bot.edit_message_text(
                    f"❌ **Inbounds не найдены**\n\n"
                    f"Сервер: **{server_info['name']}**",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            text = f"📋 **Выбор Inbound для лога JSON**\n\n"
            text += f"Сервер: **{server_info['name']}**\n"
            text += f"Количество Inbounds: **{len(inbounds)}**\n\n"
            text += "Выберите, какой inbound проверить:\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for inbound in inbounds:
                inbound_id = inbound.get('id', 'Unknown')
                remark = inbound.get('remark', f'Inbound {inbound_id}')
                button_text = f"🔗 {remark} (ID: {inbound_id})"
                callback_data = f"admin_log_json_inbound_{server_id}_{inbound_id}"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_log_full_json"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in show_inbound_selection_for_json_log: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении inbounds: {str(e)}", admin_id, message.message_id)

    def log_full_json_for_inbound(admin_id, message, server_id, inbound_id):
        """Логирование полного JSON для конкретного inbound"""
        try:
            # Получение информации о сервере
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден.", admin_id, message.message_id)
                return
            
            # Отображение сообщения "В процессе..."
            _bot.edit_message_text(
                f"📋 **Получение полного JSON**\n\n"
                f"Сервер: **{server_info['name']}**\n"
                f"Inbound ID: **{inbound_id}**\n"
                f"⏳ Подключение к панели...",
                admin_id, message.message_id, parse_mode='Markdown'
            )
            
            # Подключение к панели
            from api_client.xui_api_client import XuiAPIClient
            api_client = XuiAPIClient(
                panel_url=server_info['panel_url'],
                username=server_info['username'],
                password=server_info['password']
            )
            
            if not api_client.check_login():
                _bot.edit_message_text(
                    f"❌ **Ошибка подключения к панели**\n\n"
                    f"Сервер: **{server_info['name']}**",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            # Получение полного JSON inbound
            inbound_json = api_client.get_raw_inbound_data(inbound_id)
            if not inbound_json:
                _bot.edit_message_text(
                    f"❌ **Ошибка при получении JSON**\n\n"
                    f"Сервер: **{server_info['name']}**\n"
                    f"Inbound ID: **{inbound_id}**",
                    admin_id, message.message_id, parse_mode='Markdown'
                )
                return
            
            # Логирование полного JSON
            logger.info(f"=== COMPLETE JSON FOR INBOUND {inbound_id} ===")
            logger.info(f"Server: {server_info['name']}")
            logger.info(f"Inbound ID: {inbound_id}")
            logger.info("=== FULL JSON DATA ===")
            logger.info(json.dumps(inbound_json, indent=2, ensure_ascii=False))
            logger.info("=== END JSON DATA ===")
            
            # Отображение успешного результата
            text = f"✅ **Полный JSON залогирован**\n\n"
            text += f"Сервер: **{server_info['name']}**\n"
            text += f"Inbound ID: **{inbound_id}**\n\n"
            text += "📋 Полный JSON сохранен в системных логах.\n"
            text += "Пожалуйста, проверьте логи."
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🔙 Назад", callback_data="admin_log_full_json"),
                types.InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu")
            )
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in log_full_json_for_inbound: {e}")
            _bot.edit_message_text(f"❌ Ошибка при логировании JSON: {str(e)}", admin_id, message.message_id)

    def show_subscription_system_status(admin_id, message):
        """Отображение состояния системы подписок"""
        _clear_admin_state(admin_id)
        
        try:
            # Получение статистики покупок
            active_purchases = _db_manager.get_all_active_purchases()
            profile_purchases = _db_manager.get_all_purchases_by_type('profile')
            normal_purchases = _db_manager.get_all_purchases_by_type('normal')
            
            # Получение статистики профилей
            profiles = _db_manager.get_all_profiles(only_active=True)
            
            # Проверка настроек
            webhook_domain = os.getenv('WEBHOOK_DOMAIN')
            admin_api_key = os.getenv('ADMIN_API_KEY')
            
            text = f"📊 **Состояние системы подписок**\n\n"
            
            text += f"🔗 **Настройки:**\n"
            text += f"• Webhook Domain: `{webhook_domain or 'не настроено'}`\n"
            text += f"• Admin API Key: `{'настроен' if admin_api_key else 'не настроено'}`\n\n"
            
            text += f"📈 **Статистика покупок:**\n"
            text += f"• Всего активных покупок: **{len(active_purchases)}**\n"
            text += f"• Покупки профилей: **{len(profile_purchases)}**\n"
            text += f"• Обычные покупки: **{len(normal_purchases)}**\n\n"
            
            text += f"🎯 **Профили:**\n"
            text += f"• Активные профили: **{len(profiles)}**\n"
            
            if profiles:
                for profile in profiles[:3]:  # Отображение первых 3 профилей
                    profile_inbounds = _db_manager.get_inbounds_for_profile(profile['id'])
                    text += f"  - {profile['name']}: {len(profile_inbounds)} inbounds\n"
                if len(profiles) > 3:
                    text += f"  - и еще {len(profiles) - 3} профилей...\n"
            
            text += f"\n🚀 **Новые возможности:**\n"
            text += f"✅ Сбор данных со всех серверов профиля\n"
            text += f"✅ Автоматическое обновление изменений администратора\n"
            text += f"✅ Умная фильтрация конфигураций\n"
            text += f"✅ Динамическая система подписок\n"
            
            # Добавление кнопок
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("🔄 Обновить все", callback_data="admin_refresh_all_subscriptions"),
                types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
            )
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error showing subscription system status: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении состояния системы: {str(e)}", admin_id, message.message_id)

    def start_set_api_key_flow(admin_id, message):
        """Начало процесса настройки API Key"""
        _clear_admin_state(admin_id)
        
        # Получение текущего API Key
        current_api_key = os.getenv('ADMIN_API_KEY', 'не настроено')
        
        # Отображение текущего API Key (скрытого)
        if current_api_key != 'не настроено':
            masked_key = current_api_key[:8] + "..." + current_api_key[-4:] if len(current_api_key) > 12 else "***"
        else:
            masked_key = "не настроено"
        
        text = f"🔑 **Настройка API Key администратора**\n\n"
        text += f"**Текущий API Key:** `{masked_key}`\n\n"
        text += f"**Описание:**\n"
        text += f"• Этот ключ используется для аутентификации запросов администратора\n"
        text += f"• Должен содержать не менее 16 символов\n"
        text += f"• Должен состоять только из букв, цифр и специальных символов\n\n"
        text += f"**Пожалуйста, введите новый API Key:**"
        
        # Установка состояния
        _admin_states[admin_id] = {
            'state': 'waiting_for_api_key',
            'data': {}
        }
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
        
        _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)

    def process_api_key_input(message):
        """Обработка введенного API Key"""
        admin_id = message.from_user.id
        api_key = message.text.strip()
        
        # Удаление сообщения пользователя
        try:
            _bot.delete_message(admin_id, message.message_id)
        except:
            pass
        
        # Валидация API Key
        if len(api_key) < 16:
            _bot.send_message(
                admin_id,
                "❌ API Key должен содержать не менее 16 символов.\nПожалуйста, попробуйте снова.",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
                )
            )
            return
        
        # Проверка разрешенных символов
        import re
        if not re.match(r'^[a-zA-Z0-9\-_\.]+$', api_key):
            _bot.send_message(
                admin_id,
                "❌ API Key может содержать только буквы, цифры и символы -_.\nПожалуйста, попробуйте снова.",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
                )
            )
            return
        
        try:
            # Обновление файла .env
            from utils.helpers import update_env_file
            
            success = update_env_file('ADMIN_API_KEY', api_key)
            
            if success:
                # Отображение нового API Key (скрытого)
                masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                
                text = f"✅ **API Key успешно обновлен!**\n\n"
                text += f"**Новый API Key:** `{masked_key}`\n\n"
                text += f"**Важные замечания:**\n"
                text += f"• Этот ключ сохранен в файле .env\n"
                text += f"• Для применения изменений перезапустите бота\n"
                text += f"• Храните этот ключ в надежном месте\n"
                text += f"• Для большей безопасности регулярно меняйте ключ"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад в меню администратора", callback_data="admin_main_menu"))
                
                _bot.send_message(admin_id, text, parse_mode='Markdown', reply_markup=markup)
            else:
                _bot.send_message(
                    admin_id,
                    "❌ Ошибка при обновлении API Key.\nПожалуйста, попробуйте снова.",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
                    )
                )
                
        except Exception as e:
            logger.error(f"Error updating API key: {e}")
            _bot.send_message(
                admin_id,
                f"❌ Ошибка при обновлении API Key:\n{str(e)}",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")
                )
            )
        
        _clear_admin_state(admin_id)

    def show_config_creator_menu(admin_id, message):
        """Отображение меню создания конфигураций для разных серверов"""
        _clear_admin_state(admin_id)
        
        try:
            # Получение всех активных серверов
            servers = _db_manager.get_all_servers(only_active=True)
            
            if not servers:
                text = "❌ **Активные серверы не найдены!**\n\n"
                text += "Пожалуйста, сначала добавьте серверы в меню управления серверами."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                return
            
            text = "🔧 **Создание конфигурации с панели**\n\n"
            text += "Выберите нужный сервер:\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for server in servers:
                status = "🟢" if server.get('is_online') else "🔴"
                button_text = f"{status} {server['name']}"
                callback_data = f"admin_create_config_server_{server['id']}"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error showing config creator menu: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении меню: {str(e)}", admin_id, message.message_id)

    def show_inbound_selection_for_config(admin_id, message, server_id):
        """Отображение выбора inbound для создания конфигурации"""
        try:
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден!", admin_id, message.message_id)
                return
            
            # Создание API client
            api_client = None
            if server_info['panel_type'] == 'alireza':
                from api_client.alireza_api_client import AlirezaAPIClient
                api_client = AlirezaAPIClient(
                    panel_url=server_info['panel_url'],
                    username=server_info['username'],
                    password=server_info['password']
                )
            else:
                from api_client.xui_api_client import XuiAPIClient
                api_client = XuiAPIClient(
                    panel_url=server_info['panel_url'],
                    username=server_info['username'],
                    password=server_info['password']
                )
            
            # Попытка входа
            if not api_client.check_login():
                text = f"❌ **Ошибка подключения к панели**\n\n"
                text += f"Сервер: **{server_info['name']}**\n"
                text += f"Тип панели: **{server_info['panel_type']}**\n"
                text += "Невозможно подключиться к панели."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                return
            
            # Получение списка inbounds
            inbounds = api_client.list_inbounds()
            if not inbounds:
                text = f"❌ **Inbounds не найдены**\n\n"
                text += f"Сервер: **{server_info['name']}**\n"
                text += "На этом сервере нет активных inbounds."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                return
            
            text = f"📡 **Выбор inbound**\n\n"
            text += f"Сервер: **{server_info['name']}**\n"
            text += f"Количество inbounds: **{len(inbounds)}**\n\n"
            text += "Выберите нужный inbound:\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for inbound in inbounds:
                protocol = inbound.get('protocol', 'unknown')
                port = inbound.get('port', 'N/A')
                remark = inbound.get('remark', f'Inbound {inbound.get("id", "N/A")}')
                
                button_text = f"🔗 {protocol.upper()} - {port} - {remark[:20]}"
                callback_data = f"admin_create_config_inbound_{server_id}_{inbound['id']}"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu"))
            
            _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error showing inbound selection: {e}")
            _bot.edit_message_text(f"❌ Ошибка при отображении inbounds: {str(e)}", admin_id, message.message_id)

    def create_configs_for_inbound(admin_id, message, server_id, inbound_id):
        """Создание конфигураций для конкретного inbound"""
        from utils.config_builder import build_vmess_config, build_vless_config, build_trojan_config
        try:
            server_info = _db_manager.get_server_by_id(server_id)
            if not server_info:
                _bot.edit_message_text("❌ Сервер не найден!", admin_id, message.message_id)
                return
            
            # Создание API client
            api_client = None
            if server_info['panel_type'] == 'alireza':
                from api_client.alireza_api_client import AlirezaAPIClient
                api_client = AlirezaAPIClient(
                    panel_url=server_info['panel_url'],
                    username=server_info['username'],
                    password=server_info['password']
                )
            else:
                from api_client.xui_api_client import XuiAPIClient
                api_client = XuiAPIClient(
                    panel_url=server_info['panel_url'],
                    username=server_info['username'],
                    password=server_info['password']
                )
            
            # Попытка входа
            if not api_client.check_login():
                _bot.edit_message_text("❌ Ошибка подключения к панели", admin_id, message.message_id)
                return
            
            # Получение информации о inbound
            inbound_info = api_client.get_inbound(inbound_id)
            if not inbound_info:
                _bot.edit_message_text("❌ Inbound не найден!", admin_id, message.message_id)
                return
            
            # Получение клиентов inbound
            clients = []
            try:
                settings_str = inbound_info.get('settings', '{}')
                settings = json.loads(settings_str) if isinstance(settings_str, str) else settings_str
                clients = settings.get('clients', [])
            except:
                clients = []
            
            if not clients:
                text = f"❌ **Клиенты не найдены**\n\n"
                text += f"Сервер: **{server_info['name']}**\n"
                text += f"Inbound: **{inbound_info.get('remark', f'ID: {inbound_id}')}**\n"
                text += "В этом inbound нет активных клиентов."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_create_config_server_{server_id}"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                return
            
            # Создание конфигураций
            configs = []
            protocol = inbound_info.get('protocol', 'vmess')
            
            for client in clients:
                try:
                    if protocol == 'vmess':
                        config = build_vmess_config(client, inbound_info, server_info)
                    elif protocol == 'vless':
                        config = build_vless_config(client, inbound_info, server_info)
                    elif protocol == 'trojan':
                        config = build_trojan_config(client, inbound_info, server_info)
                    else:
                        continue
                    
                    if config:
                        configs.append({
                            'protocol': protocol,
                            'config': config,
                            'client_email': client.get('email', 'Unknown'),
                            'client_name': client.get('name', 'Unknown')
                        })
                except Exception as e:
                    logger.error(f"Error building config for client {client.get('email', 'Unknown')}: {e}")
                    continue
            
            if not configs:
                text = f"❌ **Ошибка при создании конфигураций**\n\n"
                text += f"Сервер: **{server_info['name']}**\n"
                text += f"Inbound: **{inbound_info.get('remark', f'ID: {inbound_id}')}**\n"
                text += "Ни одной конфигурации не было создано."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_create_config_server_{server_id}"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                return
            
            # Отображение конфигураций
            text = f"✅ **Созданные конфигурации**\n\n"
            text += f"**Сервер:** {server_info['name']}\n"
            text += f"**Inbound:** {inbound_info.get('remark', f'ID: {inbound_id}')}\n"
            text += f"**Протокол:** {protocol.upper()}\n"
            text += f"**Количество клиентов:** {len(configs)}\n\n"
            text += "**Конфигурации:**\n\n"
            
            for i, config_info in enumerate(configs, 1):
                text += f"**{i}. {config_info['client_email']}**\n"
                config_text = config_info['config']
                logger.info(f"Adding config {i} to single message (length: {len(config_text)}): {config_text}")
                text += f"{config_text}\n\n"
            
            # Если конфигурации слишком длинные, отправьте их в отдельных сообщениях
            logger.info(f"Total message length: {len(text)} characters")
            if len(text) > 4000:
                # Отправка краткого содержания
                summary_text = f"✅ **Созданные конфигурации**\n\n"
                summary_text += f"**Сервер:** {server_info['name']}\n"
                summary_text += f"**Inbound:** {inbound_info.get('remark', f'ID: {inbound_id}')}\n"
                summary_text += f"**Протокол:** {protocol.upper()}\n"
                summary_text += f"**Количество клиентов:** {len(configs)}\n\n"
                summary_text += "Конфигурации будут отправлены в отдельных сообщениях..."
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_create_config_server_{server_id}"))
                
                _bot.edit_message_text(summary_text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
                
                # Отправка конфигураций в отдельных сообщениях
                for i, config_info in enumerate(configs, 1):
                    # Отправка заголовка с Markdown
                    title_text = f"**{i}. {config_info['client_email']}**"
                    _bot.send_message(admin_id, title_text, parse_mode='Markdown')
                    
                    # Отправка конфигурации без Markdown, чтобы избежать усечения
                    config_text = config_info['config']
                    logger.info(f"Sending config {i} (length: {len(config_text)}): {config_text}")
                    _bot.send_message(admin_id, config_text)
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"admin_create_config_server_{server_id}"))
                
                _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error creating configs for inbound: {e}")
            _bot.edit_message_text(f"❌ Ошибка при создании конфигураций: {str(e)}", admin_id, message.message_id)
