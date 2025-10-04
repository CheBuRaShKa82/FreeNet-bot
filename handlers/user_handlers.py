import telebot
from telebot import types
import logging
import json
import qrcode
import datetime
import os
from io import BytesIO
import uuid
import requests
from config import SUPPORT_CHANNEL_LINK, ADMIN_IDS
from database.db_manager import DatabaseManager
from api_client.xui_api_client import XuiAPIClient
from utils import messages, helpers
from keyboards import inline_keyboards
from utils.config_generator import ConfigGenerator
from utils.helpers import is_float_or_int , escape_markdown_v1
from config import ZARINPAL_MERCHANT_ID, WEBHOOK_DOMAIN , ZARINPAL_SANDBOX
from utils.bot_helpers import send_subscription_info , finalize_profile_purchase

logger = logging.getLogger(__name__)

# Глобальные модули
_bot: telebot.TeleBot = None
_db_manager: DatabaseManager = None
_xui_api: XuiAPIClient = None
_config_generator: ConfigGenerator = None
# Переменные состояния
_user_menu_message_ids = {} # {user_id: message_id}
_user_states = {} # {user_id: {'state': '...', 'data': {...}}}
def _show_menu(user_id, text, markup, message=None, parse_mode='Markdown'):
    """
    Эта функция интеллектуально обрабатывает ошибки разбора Markdown.
    """
    try:
        if message:
            return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=parse_mode)
        else:
            return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)

    except telebot.apihelper.ApiTelegramException as e:
        if "can't parse entities" in str(e):
            logger.warning(f"Ошибка разбора Markdown для пользователя {user_id}. Повторная попытка с обычным текстом.")
            try:
                if message:
                    return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=None)
                else:
                    return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=None)
            except telebot.apihelper.ApiTelegramException as retry_e:
                logger.error(f"Не удалось отправить меню даже как обычный текст для пользователя {user_id}: {retry_e}")

        elif 'message to edit not found' in str(e):
            return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)
        elif 'message is not modified' not in str(e):
            logger.warning(f"Ошибка меню для {user_id}: {e}")
            
    return message


ZARINPAL_API_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_STARTPAY_URL = "https://www.zarinpal.com/pg/StartPay/"

def register_user_handlers(bot_instance, db_manager_instance, xui_api_instance):
    global _bot, _db_manager, _xui_api, _config_generator
    _bot = bot_instance
    _db_manager = db_manager_instance
    _xui_api = xui_api_instance
    _config_generator = ConfigGenerator(db_manager_instance)

    # --- Основные обработчики ---
    @_bot.callback_query_handler(func=lambda call: not call.from_user.is_bot and call.data.startswith('user_'))
    def handle_main_callbacks(call):
        """Обработка кнопок главного меню пользователя"""
        user_id = call.from_user.id
        _bot.answer_callback_query(call.id)
        # Очищать состояние пользователя только если выбран пункт из главного меню
        if call.data in ["user_main_menu", "user_buy_service", "user_my_services", "user_free_test", "user_support"]:
            _clear_user_state(user_id)

        data = call.data
        if data == "user_main_menu":
            _show_user_main_menu(user_id, message_to_edit=call.message)
        elif data == "user_buy_service":
            start_purchase(user_id, call.message)
        elif data == "user_my_services":
            show_my_services_list(user_id, call.message)
        elif data == "user_add_balance":
            start_add_balance_flow(user_id, call.message)
        # --- Измененный раздел ---
        elif data == "user_free_test":
            # Теперь вызывается функция создания тестового аккаунта
            handle_free_test_request(user_id, call.message)
        # --- Конец измененного раздела ---

        elif data == "user_buy_profile": # <-- Добавьте этот блок
            start_profile_purchase(user_id, call.message)
        elif data == "user_support":
            _bot.edit_message_text(f"📞 Для поддержки свяжитесь с нами: {SUPPORT_CHANNEL_LINK}", user_id, call.message.message_id)
        elif data.startswith("user_service_details_"):
            purchase_id = int(data.replace("user_service_details_", ""))
            show_service_details_with_traffic(user_id, purchase_id, call.message)
        elif data.startswith("user_refresh_traffic_"):
            purchase_id = int(data.replace("user_refresh_traffic_", ""))
            refresh_traffic_info(user_id, purchase_id, call.message, call.id)
        elif data.startswith("user_get_single_configs_"):
            purchase_id = int(data.replace("user_get_single_configs_", ""))
            send_single_configs(user_id, purchase_id)
        
        elif data == "user_how_to_connect":
            show_platform_selection(user_id, call.message)
        elif data.startswith("user_select_platform_"):
            platform = data.replace("user_select_platform_", "")
            show_apps_for_platform(user_id, platform, call.message)
        elif data.startswith("user_select_tutorial_"):
            tutorial_id = int(data.replace("user_select_tutorial_", ""))
            send_tutorial_to_user(user_id, tutorial_id, call.message)
        elif data == "user_account": 
            show_user_account_menu(user_id, call.message) 
        elif data == "user_check_join_status":
            required_channel_id_str = _db_manager.get_setting('required_channel_id')
            if required_channel_id_str:
                required_channel_id = int(required_channel_id_str)
                if helpers.is_user_member_of_channel(_bot, required_channel_id, call.from_user.id):
                    # User has joined, delete the message and show the main menu
                    _bot.delete_message(call.message.chat.id, call.message.message_id)
                    # We call the /start logic again, which will now succeed
                    from main import send_welcome 
                    send_welcome(call.message)
                else:
                    # User has not joined yet, show an alert
                    _bot.answer_callback_query(call.id, "❌ Вы еще не подписались на канал.", show_alert=True)
            else:
                # Channel lock is not set, just show the main menu
                _bot.delete_message(call.message.chat.id, call.message.message_id)
                from main import send_welcome 
                send_welcome(call.message)
    @_bot.callback_query_handler(func=lambda call: not call.from_user.is_bot and call.data.startswith(('buy_', 'select_', 'confirm_', 'cancel_', 'pay_', 'show_')))

    def handle_purchase_callbacks(call):
        """Обработка кнопок процесса покупки"""
        _bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        data = call.data
        messages = call.data
        # Удаление предыдущего сообщения
        try:
            _bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        if data.startswith("buy_select_server_"):
            server_id = int(data.replace("buy_select_server_", ""))
            select_server_for_purchase(user_id, server_id, call.message)
        elif data.startswith("buy_plan_type_"):
            select_plan_type(user_id, data.replace("buy_plan_type_", ""), call.message)
        elif data.startswith("buy_select_plan_"):
            plan_id = int(data.replace("buy_select_plan_", ""))
            select_fixed_plan(user_id, plan_id, call.message)
        elif data == "confirm_and_pay":
            display_payment_gateways(user_id, call.message)
        elif data.startswith("select_gateway_"):
            gateway_id = int(data.replace("select_gateway_", ""))
            select_payment_gateway(user_id, gateway_id, call.message)
        elif data.startswith("buy_select_profile_"):
            profile_id = int(data.replace("buy_select_profile_", ""))
            select_profile_for_purchase(user_id, profile_id, call.message)
        elif data == "pay_with_wallet":
            process_wallet_payment(user_id, call.message)
        elif data == "show_order_summary":
            # Возврат к сводке заказа
            show_order_summary(user_id, call.message)

        elif data == "cancel_order":
            logger.info(f"User {user_id} cancelled order")
            _clear_user_state(user_id)
            try:
                _bot.edit_message_text(messages.ORDER_CANCELED, user_id, call.message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            except Exception as e:
                # Если редактирование не удалось, отправляем новое сообщение
                logger.warning(f"Could not edit message for cancel order: {e}")
                _bot.send_message(user_id, messages.ORDER_CANCELED, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            finally:
                # Ответ на callback query
                _bot.answer_callback_query(call.id, "Заказ отменен")


    @_bot.message_handler(content_types=['text', 'photo'], func=lambda msg: _user_states.get(msg.from_user.id))
    def handle_stateful_messages(message):
        """Обработка текстовых или фото сообщений, которые пользователь отправляет в определенном состоянии"""
        user_id = message.from_user.id
        state_info = _user_states[user_id]
        current_state = state_info.get('state')

        # Удаление входящего сообщения пользователя для чистоты чата
        try: _bot.delete_message(user_id, message.message_id)
        except Exception: pass

        if current_state == 'waiting_for_gigabytes_input':
            process_gigabyte_input(message)
        elif current_state == 'waiting_for_payment_receipt':
            process_payment_receipt(message)
        elif current_state == 'waiting_for_profile_gigabytes_input': 
            process_profile_gigabyte_input(message)
        elif current_state == 'waiting_for_payment_receipt':
            process_payment_receipt(message)
        elif current_state == 'waiting_for_custom_config_name':
            process_custom_config_name(message)
        elif current_state == 'waiting_for_charge_amount':
            process_charge_amount(message)
    # --- Вспомогательные и основные функции ---
    def show_how_to_connect(user_id, message):
        """Sends the guide on how to connect to the services."""
        _bot.edit_message_text(
            messages.HOW_TO_CONNECT_TEXT,
            user_id,
            message.message_id,
            reply_markup=inline_keyboards.get_back_button("user_main_menu"),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    def _clear_user_state(user_id):
        if user_id in _user_states:
            del _user_states[user_id]
        _bot.clear_step_handler_by_chat_id(chat_id=user_id)

    def _show_user_main_menu(user_id, message_to_edit=None):
        """ --- SIMPLIFIED: Fetches only the support link --- """
        _clear_user_state(user_id)
        menu_text = messages.USER_MAIN_MENU_TEXT
        
        # Fetch only the support link from the database
        support_link = _db_manager.get_setting('support_link')

        # Pass the link to the keyboard function
        menu_markup = inline_keyboards.get_user_main_inline_menu(support_link)
        
        if message_to_edit:
            try:
                _bot.edit_message_text(menu_text, user_id, message_to_edit.message_id, reply_markup=menu_markup)
            except telebot.apihelper.ApiTelegramException: pass
        else:
            _bot.send_message(user_id, menu_text, reply_markup=menu_markup)

    # --- Процесс покупки ---
    def start_purchase(user_id, message):
        active_servers = [s for s in _db_manager.get_all_servers() if s['is_active'] and s['is_online']]
        if not active_servers:
            _bot.edit_message_text(messages.NO_ACTIVE_SERVERS_FOR_BUY, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        
        _user_states[user_id] = {'state': 'selecting_server', 'data': {}}
        _bot.edit_message_text(messages.SELECT_SERVER_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_server_selection_menu(active_servers))

    def select_server_for_purchase(user_id, server_id, message):
        _user_states[user_id]['data']['server_id'] = server_id
        _user_states[user_id]['state'] = 'selecting_plan_type'
        _bot.edit_message_text(messages.SELECT_PLAN_TYPE_PROMPT_USER, user_id, message.message_id, reply_markup=inline_keyboards.get_plan_type_selection_menu_user(server_id))
    
    def select_plan_type(user_id, plan_type, message):
        _user_states[user_id]['data']['plan_type'] = plan_type
        if plan_type == 'fixed_monthly':
            active_plans = [p for p in _db_manager.get_all_plans(only_active=True) if p['plan_type'] == 'fixed_monthly']
            if not active_plans:
                _bot.edit_message_text(messages.NO_FIXED_PLANS_AVAILABLE, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
                return
            _user_states[user_id]['state'] = 'selecting_fixed_plan'
            _bot.edit_message_text(messages.SELECT_FIXED_PLAN_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_fixed_plan_selection_menu(active_plans))
        
        elif plan_type == 'gigabyte_based':
            gb_plan = next((p for p in _db_manager.get_all_plans(only_active=True) if p['plan_type'] == 'gigabyte_based'), None)
            if not gb_plan or not gb_plan.get('per_gb_price'):
                _bot.edit_message_text(messages.GIGABYTE_PLAN_NOT_CONFIGURED, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
                return
            _user_states[user_id]['data']['gb_plan_details'] = gb_plan
            _user_states[user_id]['state'] = 'waiting_for_gigabytes_input'
            sent_msg = _bot.edit_message_text(messages.ENTER_GIGABYTES_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
            _user_states[user_id]['prompt_message_id'] = sent_msg.message_id

    def select_fixed_plan(user_id, plan_id, message):
        plan = _db_manager.get_plan_by_id(plan_id)
        if not plan:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
        _user_states[user_id]['data']['plan_details'] = plan
        show_order_summary(user_id, message)
        
    def process_gigabyte_input(message):
        user_id = message.from_user.id
        state_data = _user_states[user_id]
        
        if not is_float_or_int(message.text) or float(message.text) <= 0:
            _bot.edit_message_text(messages.INVALID_GIGABYTE_INPUT + "\n" + messages.ENTER_GIGABYTES_PROMPT, user_id, state_data['prompt_message_id'])
            return
            
        state_data['data']['requested_gb'] = float(message.text)
        show_order_summary(user_id, message)

    def show_order_summary(user_id, message):
        _user_states[user_id]['state'] = 'confirming_order'
        order_data = _user_states[user_id]['data']
        
        server_info = _db_manager.get_server_by_id(order_data['server_id'])
        summary_text = messages.ORDER_SUMMARY_HEADER
        summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info['name'])
        
        total_price = 0
        plan_details_for_admin = ""
        
        if order_data['plan_type'] == 'fixed_monthly':
            plan = order_data['plan_details']
            summary_text += messages.ORDER_SUMMARY_FIXED_PLAN.format(
                plan_name=plan['name'],
                volume_gb=plan['volume_gb'],
                duration_days=plan['duration_days']
            )
            total_price = plan['price']
            plan_details_for_admin = f"{plan['name']} ({plan['volume_gb']}ГБ, {plan['duration_days']} дней)"

        elif order_data['plan_type'] == 'gigabyte_based':
            gb_plan = order_data['gb_plan_details']
            requested_gb = order_data['requested_gb']
            total_price = requested_gb * gb_plan['per_gb_price']
            summary_text += messages.ORDER_SUMMARY_GIGABYTE_PLAN.format(gigabytes=requested_gb)
            plan_details_for_admin = f"{requested_gb} гигабайт"

        summary_text += messages.ORDER_SUMMARY_TOTAL_PRICE.format(total_price=total_price)
        summary_text += messages.ORDER_SUMMARY_CONFIRM_PROMPT
        
        order_data['total_price'] = total_price
        order_data['plan_details_for_admin'] = plan_details_for_admin
        
        prompt_id = _user_states[user_id].get('prompt_message_id', message.message_id)
        _bot.edit_message_text(summary_text, user_id, prompt_id, reply_markup=inline_keyboards.get_order_confirmation_menu())

    # --- Процесс оплаты ---
    def display_payment_gateways(user_id, message):
        _user_states[user_id]['state'] = 'selecting_gateway'
        active_gateways = _db_manager.get_all_payment_gateways(only_active=True)
        
        user_info = _db_manager.get_user_by_telegram_id(user_id)
        wallet_balance = user_info.get('balance', 0.0)
        order_price = _user_states[user_id]['data']['total_price']
        
        if not active_gateways and wallet_balance < order_price:
            _bot.edit_message_text(messages.NO_ACTIVE_PAYMENT_GATEWAYS, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("show_order_summary"))
            return
        
        # --- Добавьте эту новую строку для отладки ---
        logger.info(f"DEBUG_WALLET: User={user_id}, Balance={wallet_balance}, OrderPrice={order_price}, OrderData={_user_states[user_id]['data']}")
        
        markup = inline_keyboards.get_payment_gateway_selection_menu(active_gateways, wallet_balance, order_price)
        _bot.edit_message_text(messages.SELECT_PAYMENT_GATEWAY_PROMPT, user_id, message.message_id, reply_markup=markup)
    def select_payment_gateway(user_id, gateway_id, message):
        gateway = _db_manager.get_payment_gateway_by_id(gateway_id)
        if not gateway:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return

        order_data = _user_states[user_id]['data']
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            logger.error(f"Could not find user with telegram_id {user_id} in the database.")
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
        # --- Логика разделения по типу шлюза ---
        if gateway['type'] == 'zarinpal':
            _bot.edit_message_text("⏳ Создание безопасной ссылки для оплаты... Пожалуйста, подождите.", user_id, message.message_id)
            
            amount_toman = int(order_data['total_price'])
            
            # FIX: Добавляем данные шлюза в заказ, чтобы они были доступны в веб-хуке
            order_data['gateway_details'] = gateway
            
            order_details_for_db = json.dumps(order_data)
            payment_id = _db_manager.add_payment(user_db_info['id'], amount_toman, message.message_id, order_details_for_db)
            
            if not payment_id:
                _bot.edit_message_text("❌ Произошла ошибка при создании счета.", user_id, message.message_id)
                return

            callback_url = f"https://{WEBHOOK_DOMAIN}/zarinpal/verify"
            
            payload = {
                "merchant_id": gateway['merchant_id'],
                "amount": amount_toman * 10, # FIX: Конвертация тумана в риал
                "callback_url": callback_url,
                "description": f"Покупка услуги в боте - Заказ № {payment_id}",
                "metadata": {"user_id": str(user_id), "payment_id": str(payment_id)}
            }
            
            try:
                response = requests.post(ZARINPAL_API_URL, json=payload, timeout=20)
                response.raise_for_status()
                result = response.json()

                if result.get("data") and result.get("data", {}).get("code") == 100:
                    authority = result['data']['authority']
                    payment_url = f"{ZARINPAL_STARTPAY_URL}{authority}"
                    _db_manager.set_payment_authority(payment_id, authority)
                    
                    # FIX: Правильное создание клавиатуры с двумя отдельными кнопками
                    markup = types.InlineKeyboardMarkup()
                    btn_pay = types.InlineKeyboardButton("🚀 Оплатить онлайн", url=payment_url)
                    btn_back = types.InlineKeyboardButton("❌ Отмена и возврат", callback_data="user_main_menu")
                    markup.add(btn_pay)
                    markup.add(btn_back)
                    
                    _bot.edit_message_text("Ваша ссылка для оплаты создана. Пожалуйста, перейдите по кнопке ниже.", user_id, message.message_id, reply_markup=markup)
                    _clear_user_state(user_id)
                else:
                    error_code = result.get("errors", {}).get("code", "неизвестно")
                    error_message = result.get("errors", {}).get("message", "неизвестная ошибка от платежного шлюза")
                    _bot.edit_message_text(f"❌ Ошибка при создании ссылки на оплату: {error_message} (код: {error_code})", user_id, message.message_id)

            except requests.exceptions.HTTPError as http_err:
                logger.error(f"HTTP error occurred: {http_err} - Response: {http_err.response.text}")
                _bot.edit_message_text("❌ Платежный шлюз столкнулся с внутренней ошибкой. Пожалуйста, попробуйте позже.", user_id, message.message_id)
            except requests.exceptions.RequestException as e:
                logger.error(f"Error connecting to Zarinpal: {e}")
                _bot.edit_message_text("❌ В данный момент невозможно подключиться к платежному шлюзу.", user_id, message.message_id)

        # --- Логика для перевода с карты на карту ---
        elif gateway['type'] == 'card_to_card':
            _user_states[user_id]['data']['gateway_details'] = gateway
            _user_states[user_id]['state'] = 'waiting_for_payment_receipt'
            total_price = order_data['total_price']
            payment_text = messages.PAYMENT_GATEWAY_DETAILS.format(
                name=gateway['name'], card_number=gateway['card_number'],
                card_holder_name=gateway['card_holder_name'],
                description_line=f"**Описание:** {gateway['description']}\n" if gateway.get('description') else "",
                amount=total_price
            )
            sent_msg = _bot.edit_message_text(payment_text, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("show_order_summary"))
            _user_states[user_id]['prompt_message_id'] = sent_msg.message_id

    def process_payment_receipt(message):
        user_id = message.from_user.id
        state_data = _user_states.get(user_id)

        if not state_data or state_data.get('state') != 'waiting_for_payment_receipt':
            return

        if not message.photo:
            _bot.send_message(user_id, messages.INVALID_RECEIPT_FORMAT)
            return

        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.send_message(user_id, messages.OPERATION_FAILED)
            _clear_user_state(user_id)
            return

        order_data = state_data['data']
        
        server_id = None
        server_name = ""
        purchase_type = order_data.get('purchase_type')

        # --- Основное исправление здесь: разделение на три разных случая ---
        if purchase_type == 'profile':
            profile_details = order_data['profile_details']
            server_name = f"Профиль: {profile_details['name']}"
            profile_inbounds = _db_manager.get_inbounds_for_profile(profile_details['id'], with_server_info=True)
            if profile_inbounds:
                server_id = profile_inbounds[0]['server']['id']
            else:
                _bot.send_message(user_id, "Ошибка: у выбранного профиля нет серверов. Пожалуйста, сообщите администратору.")
                _clear_user_state(user_id)
                return
        
        elif purchase_type == 'wallet_charge':
            # Для пополнения кошелька сервер не имеет значения
            server_id = None 
            server_name = "Пополнение кошелька"

        else: # Случай по умолчанию: покупка обычной услуги
            server_id = order_data['server_id']
            server_info = _db_manager.get_server_by_id(server_id)
            server_name = server_info['name'] if server_info else "Неизвестный сервер"

        # Создание полного словаря для сохранения в базе данных
        order_details_for_db = {
            'user_telegram_id': user_id,
            'user_db_id': user_db_info['id'],
            'user_first_name': message.from_user.first_name,
            'server_id': server_id,
            'server_name': server_name,
            'purchase_type': purchase_type,
            'plan_type': order_data.get('plan_type'),
            'profile_details': order_data.get('profile_details'),
            'plan_details': order_data.get('plan_details'),
            'gb_plan_details': order_data.get('gb_plan_details'),
            'requested_gb': order_data.get('requested_gb'),
            'total_price': order_data['total_price'],
            'gateway_name': order_data['gateway_details']['name'],
            'plan_details_text_display': order_data['plan_details_for_admin'],
            'receipt_file_id': message.photo[-1].file_id
        }

        payment_id = _db_manager.add_payment(
            user_db_info['id'],
            order_data['total_price'],
            message.message_id,
            json.dumps(order_details_for_db)
        )

        if not payment_id:
            _bot.send_message(user_id, "Произошла ошибка при сохранении вашего платежа. Пожалуйста, попробуйте еще раз.")
            _clear_user_state(user_id)
            return

        # Отправка уведомления администраторам
        caption = messages.ADMIN_NEW_PAYMENT_NOTIFICATION_DETAILS.format(
            user_first_name=helpers.escape_markdown_v1(order_details_for_db['user_first_name']),
            user_telegram_id=order_details_for_db['user_telegram_id'],
            amount=order_details_for_db['total_price'],
            server_name=helpers.escape_markdown_v1(order_details_for_db['server_name']),
            plan_details=helpers.escape_markdown_v1(order_details_for_db['plan_details_text_display']),
            gateway_name=helpers.escape_markdown_v1(order_details_for_db['gateway_name'])
        )
        markup = inline_keyboards.get_admin_payment_action_menu(payment_id)
        
        for admin_id in ADMIN_IDS:
            try:
                sent_msg = _bot.send_photo(
                    admin_id,
                    order_details_for_db['receipt_file_id'],
                    caption=messages.ADMIN_NEW_PAYMENT_NOTIFICATION_HEADER + caption,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                # Сохраняем в базе данных только первое сообщение администратору
                if admin_id == ADMIN_IDS[0]:
                    _db_manager.update_payment_admin_notification_id(payment_id, sent_msg.message_id)
            except Exception as e:
                logger.error(f"Failed to send payment notification to admin {admin_id}: {e}")

        _bot.send_message(user_id, messages.RECEIPT_RECEIVED_USER)
        _clear_user_state(user_id)
        _show_user_main_menu(user_id)

    def show_service_details(user_id, purchase_id, message):
        """
        Shows the details of a specific subscription, without the single config button.
        """
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
            
        sub_link = ""
        if purchase['sub_id']: # Use sub_id which is correct
            # Использование активного домена вместо домена сервера
            active_domain_record = _db_manager.get_active_subscription_domain()
            active_domain = active_domain_record['domain_name'] if active_domain_record else None
            
            if not active_domain:
                # Если активного домена нет, используем домен сервера
                server = _db_manager.get_server_by_id(purchase['server_id'])
                if server:
                    sub_base = server['subscription_base_url'].rstrip('/')
                    sub_path = server['subscription_path_prefix'].strip('/')
                    sub_link = f"{sub_base}/{sub_path}/{purchase['sub_id']}"
            else:
                # Использование активного домена
                sub_link = f"https://{active_domain}/sub/{purchase['sub_id']}"
        
        if sub_link:
            text = messages.CONFIG_DELIVERY_HEADER + \
                messages.CONFIG_DELIVERY_SUB_LINK.format(sub_link=sub_link)
            
            # --- REMOVED: The button for single configs is gone ---
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🔙 Назад к услугам", callback_data="user_my_services")
            markup.add(btn_back)

            _bot.edit_message_text(text, user_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
            # Send QR Code as a new message
            try:
                import qrcode
                from io import BytesIO
                qr_image = qrcode.make(sub_link)
                bio = BytesIO()
                bio.name = 'qrcode.jpeg'
                qr_image.save(bio, 'JPEG')
                bio.seek(0)
                _bot.send_photo(user_id, bio, caption=messages.QR_CODE_CAPTION)
            except Exception as e:
                logger.error(f"Failed to generate QR code in service details: {e}")
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
    def send_single_configs(user_id, purchase_id):
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase or not purchase['single_configs_json']:
            _bot.send_message(user_id, messages.NO_SINGLE_CONFIGS_AVAILABLE)
            return
            
        configs = purchase['single_configs_json']
        text = messages.SINGLE_CONFIG_HEADER
        for config in configs:
            text += f"**{config['remark']} ({config['protocol']}/{config['network']})**:\n`{config['url']}`\n\n"
        
        _bot.send_message(user_id, text, parse_mode='Markdown')
    
    def send_configs_to_user(user_id, configs, config_type="конфиг"):
        """Отправка конфигураций пользователю"""
        if not configs:
            _bot.send_message(user_id, "❌ Ошибка при создании конфигураций")
            return
            
        text = f"📄 **Ваш {config_type}:**\n\n"
        for i, config in enumerate(configs, 1):
            text += f"**{config_type} {i}:**\n`{config}`\n\n"
        
        # Если текст слишком длинный, разделяем его на части
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                _bot.send_message(user_id, part, parse_mode='Markdown')
        else:
            _bot.send_message(user_id, text, parse_mode='Markdown')
        
        
    # в файле handlers/user_handlers.py

    def show_order_summary(user_id, message):
        """
        Отображает сводку заказа для обычной услуги или профиля. (финальная версия)
        """
        _user_states[user_id]['state'] = 'confirming_order'
        order_data = _user_states[user_id]['data']
        purchase_type = order_data.get('purchase_type')

        summary_text = messages.ORDER_SUMMARY_HEADER
        total_price = 0
        plan_details_for_admin = ""
        duration_text = ""

        if purchase_type == 'profile':
            profile = order_data['profile_details']
            requested_gb = order_data['requested_gb']
            server_info = "Несколько серверов"
            summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info)
            summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=profile['name'])
            summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=requested_gb)
            duration_text = f"{profile['duration_days']} дней"
            total_price = requested_gb * profile['per_gb_price']
            plan_details_for_admin = f"Профиль: {profile['name']} ({requested_gb}ГБ)"

        else: # Покупка обычной услуги
            server_info = _db_manager.get_server_by_id(order_data['server_id'])
            summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info['name'])
            
            if order_data['plan_type'] == 'fixed_monthly':
                plan = order_data['plan_details']
                summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=plan['name'])
                summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=plan['volume_gb'])
                duration_text = f"{plan['duration_days']} дней"
                total_price = plan['price']
                plan_details_for_admin = f"{plan['name']} ({plan['volume_gb']}ГБ, {plan['duration_days']} дней)"

            elif order_data['plan_type'] == 'gigabyte_based':
                gb_plan = order_data['gb_plan_details']
                requested_gb = order_data['requested_gb']
                summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=gb_plan['name'])
                summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=requested_gb)
                duration_days = gb_plan.get('duration_days')
                duration_text = f"{duration_days} дней" if duration_days and duration_days > 0 else "Безлимитно"
                total_price = requested_gb * gb_plan['per_gb_price']
                plan_details_for_admin = f"{gb_plan['name']} ({requested_gb}ГБ, {duration_text})"
        
        summary_text += messages.ORDER_SUMMARY_DURATION.format(duration_days=duration_text)
        summary_text += messages.ORDER_SUMMARY_TOTAL_PRICE.format(total_price=total_price)
        summary_text += messages.ORDER_SUMMARY_CONFIRM_PROMPT
        
        order_data['total_price'] = total_price
        order_data['plan_details_for_admin'] = plan_details_for_admin
        
        prompt_id = _user_states[user_id].get('prompt_message_id', message.message_id)
        _bot.edit_message_text(summary_text, user_id, prompt_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_order_confirmation_menu())
    def handle_free_test_request(user_id, message):
        _bot.edit_message_text(messages.PLEASE_WAIT, user_id, message.message_id)
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id); return

        if _db_manager.check_free_test_usage(user_db_info['id']):
            _bot.edit_message_text(messages.FREE_TEST_ALREADY_USED, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu")); return

        active_servers = [s for s in _db_manager.get_all_servers() if s['is_active'] and s['is_online']]
        if not active_servers:
            _bot.edit_message_text(messages.NO_ACTIVE_SERVERS_FOR_BUY, user_id, message.message_id); return
        
        test_server_id = active_servers[0]['id']
        test_volume_gb = 0.1 # 100 MB
        test_duration_days = 1 # 1 day

        from utils.config_generator import ConfigGenerator
        config_gen = ConfigGenerator(_db_manager)
        configs, client_details = config_gen.create_subscription_for_server(user_id, test_server_id, test_volume_gb, test_duration_days)

        if configs and client_details:
            print("Free test subscription created successfully.")
            _db_manager.record_free_test_usage(user_db_info['id'])
            _bot.delete_message(user_id, message.message_id)
            _bot.send_message(user_id, messages.GET_FREE_TEST_SUCCESS)
            send_configs_to_user(user_id, configs, "Бесплатный тестовый аккаунт")
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)



    def show_my_services_list(user_id, message):
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return

        purchases = _db_manager.get_user_purchases(user_db_info['id'])
        
        _bot.edit_message_text(
            messages.MY_SERVICES_HEADER,
            user_id,
            message.message_id,
            reply_markup=inline_keyboards.get_my_services_menu(purchases),
            parse_mode='Markdown'
        )
        
        
    def process_custom_config_name(message):
        """
        Обрабатывает произвольное имя, создает конфигурацию, регистрирует покупку и предоставляет ссылку. (финальная версия)
        """
        user_id = message.from_user.id
        state_info = _user_states.get(user_id, {})
        if not state_info or state_info.get('state') != 'waiting_for_custom_config_name':
            return

        custom_name = message.text.strip()
        if custom_name.lower() == 'skip':
            custom_name = None

        order_details = state_info['data']
        prompt_id = state_info['prompt_message_id']
        _bot.edit_message_text(messages.PLEASE_WAIT, user_id, prompt_id)

        server_id = order_details['server_id']
        plan_type = order_details['plan_type']
        total_gb, duration_days, plan_id = 0, 0, None

        if plan_type == 'fixed_monthly':
            plan = order_details['plan_details']
            total_gb, duration_days, plan_id = plan.get('volume_gb'), plan.get('duration_days'), plan.get('id')
        elif plan_type == 'gigabyte_based':
            gb_plan = order_details['gb_plan_details']
            total_gb = order_details['requested_gb']
            duration_days = gb_plan.get('duration_days', 0)
            plan_id = gb_plan.get('id')
        
        config_gen = ConfigGenerator(_db_manager)
        generated_configs, client_details = config_gen.create_subscription_for_server(
            user_telegram_id=user_id,
            server_id=server_id,
            total_gb=total_gb,
            duration_days=duration_days,
            custom_remark=custom_name
        )

        if not generated_configs:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, prompt_id)
            _clear_user_state(user_id)
            return

        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)) if duration_days and duration_days > 0 else None
        
        new_sub_id = str(uuid.uuid4().hex)

        # --- Основное исправление здесь ---
        # Имя параметра изменено на 'single_configs_json'
        _db_manager.add_purchase(
            user_id=user_db_info['id'],
            server_id=server_id,
            plan_id=plan_id,
            profile_id=None,
            expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S") if expire_date else None,
            initial_volume_gb=total_gb,
            client_uuids=client_details['uuids'],
            client_email=client_details['email'],
            sub_id=new_sub_id,
            single_configs_json=json.dumps(generated_configs)
        )

        _bot.delete_message(user_id, prompt_id)
        _bot.send_message(user_id, messages.SERVICE_ACTIVATION_SUCCESS_USER)
        
        active_domain_record = _db_manager.get_active_subscription_domain()
        active_domain = active_domain_record['domain_name'] if active_domain_record else os.getenv("WEBHOOK_DOMAIN")

        if not active_domain:
            _bot.send_message(user_id, "❌ Активный домен для ссылки подписки не настроен. Пожалуйста, сообщите в поддержку.")
            return

        final_sub_link = f"https://{active_domain}/sub/{new_sub_id}"
        send_subscription_info(_bot, user_id, final_sub_link)
        
        _clear_user_state(user_id)
    def show_platform_selection(user_id, message):
        """Shows the platform selection menu to the user."""
        platforms = _db_manager.get_distinct_platforms()
        if not platforms:
            _bot.edit_message_text("На данный момент нет зарегистрированных инструкций.", user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        markup = inline_keyboards.get_platforms_menu(platforms)
        _bot.edit_message_text("Пожалуйста, выберите вашу платформу:", user_id, message.message_id, reply_markup=markup)

    def show_apps_for_platform(user_id, platform, message):
        """Shows the list of apps for the selected platform."""
        tutorials = _db_manager.get_tutorials_by_platform(platform)
        markup = inline_keyboards.get_apps_for_platform_menu(tutorials, platform)
        _bot.edit_message_text(f"Инструкцию для какого приложения на {platform} вы хотите получить?", user_id, message.message_id, reply_markup=markup)

    def send_tutorial_to_user(user_id, tutorial_id, message):
        """Forwards the selected tutorial message to the user."""
        tutorial = _db_manager.get_tutorial_by_id(tutorial_id) # You need to create this function in db_manager
        if not tutorial:
            _bot.answer_callback_query(message.id, "Инструкция не найдена.", show_alert=True)
            return
        
        try:
            _bot.forward_message(
                chat_id=user_id,
                from_chat_id=tutorial['forward_chat_id'],
                message_id=tutorial['forward_message_id']
            )
            _bot.answer_callback_query(message.id)
        except Exception as e:
            logger.error(f"Failed to forward tutorial {tutorial_id} to user {user_id}: {e}")
            _bot.answer_callback_query(message.id, "Ошибка при отправке инструкции. Пожалуйста, сообщите администратору.", show_alert=True)
            
            
            
    def start_profile_purchase(user_id, message):
        """Начинает процесс покупки профиля с отображения списка активных профилей."""
        active_profiles = _db_manager.get_all_profiles(only_active=True)
        if not active_profiles:
            _bot.edit_message_text(messages.NO_PROFILES_AVAILABLE, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        
        # Очистка предыдущего состояния пользователя
        _clear_user_state(user_id)
        
        markup = inline_keyboards.get_profile_selection_menu_for_user(active_profiles)
        _bot.edit_message_text(messages.SELECT_PROFILE_PROMPT, user_id, message.message_id, reply_markup=markup)
        
        
    def select_profile_for_purchase(user_id, profile_id, message):
        """
        Подготавливает информацию о выбранном профиле и запрашивает у пользователя объем.
        """
        
        profile = _db_manager.get_profile_by_id(profile_id)
        if not profile:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
            
        # Очистка предыдущего состояния и установка нового для получения объема
        _clear_user_state(user_id)
        _user_states[user_id] = {
            'state': 'waiting_for_profile_gigabytes_input',
            'data': {
                'purchase_type': 'profile',
                'profile_details': dict(profile)
            }
        }
        
        # Запрос объема у пользователя
        sent_msg = _bot.edit_message_text(
            messages.ENTER_PROFILE_GIGABYTES_PROMPT, 
            user_id, 
            message.message_id, 
            reply_markup=inline_keyboards.get_back_button("user_buy_profile")
        )
        _user_states[user_id]['prompt_message_id'] = sent_msg.message_id
    def process_profile_gigabyte_input(message):
        user_id = message.from_user.id
        state_data = _user_states[user_id]
        
        if not is_float_or_int(message.text) or float(message.text) <= 0:
            _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ENTER_PROFILE_GIGABYTES_PROMPT}", user_id, state_data['prompt_message_id'])
            return
                
        # --- Основное исправление здесь ---
        # Мы правильно сохраняем purchase_type в состоянии
        state_data['data']['purchase_type'] = 'profile'
        state_data['data']['requested_gb'] = float(message.text)
        
        # Теперь переходим к отображению сводки заказа
        show_order_summary(user_id, message)
        
        
    def show_user_account_menu(user_id, message):
        """Отображает пользователю информацию об учетной записи."""
        user_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_info:
            _bot.edit_message_text("Произошла ошибка при получении вашей информации.", user_id, message.message_id)
            return

        balance = user_info.get('balance', 0.0)
        is_verified = user_info.get('is_verified', False)
        
        status_text = "Подтвержден ✅" if is_verified else "Требуется заполнение профиля ⚠️"
        
        # TODO: В будущем будем считывать количество рефералов из базы данных
        referral_count = 0 
        
        account_text = (
            f"👤 **Ваш аккаунт**\n\n"
            f"▫️ **Имя:** {helpers.escape_markdown_v1(user_info.get('first_name', ''))}\n"
            f"▫️ **Числовой ID:** `{user_id}`\n"
            f"▫️ **Баланс кошелька:** `{balance:,.0f}` туманов\n"
            f"▫️ **Статус аккаунта:** {status_text}\n\n"
            f"🔗 **Ваша пригласительная ссылка:**\n`t.me/{_bot.get_me().username}?start=ref_{user_id}`\n"
            f"👥 **Количество рефералов:** {referral_count} чел."
        )
        
        markup = inline_keyboards.get_user_account_menu()
        _show_menu(user_id, account_text, markup, message, parse_mode='Markdown')
        
        
        
    def start_add_balance_flow(user_id, message):
        """Начинает процесс пополнения кошелька с запроса суммы."""
        _clear_user_state(user_id)
        prompt_text = "Пожалуйста, введите сумму в туманах, на которую хотите пополнить свой кошелек (например: 50000):"
        prompt = _show_menu(user_id, prompt_text, inline_keyboards.get_back_button("user_account"), message)
        _user_states[user_id] = {'state': 'waiting_for_charge_amount', 'prompt_message_id': prompt.message_id}

    def process_charge_amount(message):
        """Обрабатывает введенную пользователем сумму и отображает сводку заказа."""
        user_id = message.from_user.id
        state_info = _user_states.get(user_id, {})
        
        amount_str = message.text.strip()
        if not amount_str.isdigit() or int(amount_str) <= 0:
            _bot.send_message(user_id, "Введенная сумма недействительна. Пожалуйста, введите целое положительное число.")
            return

        amount = int(amount_str)
        
        # Создание временной сводки заказа для отображения пользователю и использования в процессе оплаты
        state_info['data'] = {
            'purchase_type': 'wallet_charge',
            'total_price': amount,
            'plan_details_for_admin': f"Пополнение кошелька на сумму {amount:,.0f} туманов"
        }
        
        summary_text = (
            f"📝 **Подтверждение транзакции**\n\n"
            f"Вы пополняете свой кошелек на сумму **{amount:,.0f} туманов**.\n\n"
            f"Вы подтверждаете?"
        )
        
        markup = inline_keyboards.get_confirmation_menu("confirm_and_pay", "user_account")
        _bot.edit_message_text(summary_text, user_id, state_info['prompt_message_id'], reply_markup=markup, parse_mode='Markdown')
        
        
        
    def process_wallet_payment(user_id, message):
        """Обрабатывает платеж через кошелек и активирует услугу."""
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        order_details = _user_states[user_id]['data']
        order_price = order_details['total_price']

        if not user_db_info or user_db_info.get('balance', 0) < order_price:
            _bot.answer_callback_query(message.id, "Недостаточно средств на вашем кошельке.", show_alert=True)
            return
        
        if _db_manager.deduct_from_user_balance(user_db_info['id'], order_price):
            _bot.edit_message_text("✅ Ваш платеж через кошелек успешно выполнен. Пожалуйста, подождите...", user_id, message.message_id)
            
            # --- Основная логика здесь ---
            if order_details.get('purchase_type') == 'profile':
                finalize_profile_purchase(_bot, _db_manager, user_id, order_details)
            else: # Обычная покупка
                prompt = _bot.send_message(user_id, messages.ASK_FOR_CUSTOM_CONFIG_NAME)
                _user_states[user_id] = {
                    'state': 'waiting_for_custom_config_name',
                    'data': order_details,
                    'prompt_message_id': prompt.message_id
                }
        else:
            _bot.edit_message_text("❌ Произошла ошибка при списании средств с кошелька. Пожалуйста, свяжитесь с поддержкой.", user_id, message.message_id)
            _clear_user_state(user_id)

    def show_service_details_with_traffic(user_id, purchase_id, message):
        """
        Отображение деталей услуги вместе с информацией о трафике и оставшемся времени
        """
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
        
        # Расчет оставшегося времени
        days_remaining = helpers.calculate_days_remaining(purchase.get('expire_date'))
        
        # Получение информации о трафике
        traffic_info = None
        if purchase.get('client_uuid'):
            traffic_info = _db_manager.get_client_traffic_info(purchase['client_uuid'])
        
        # Создание текста для отображения
        text = f"📊 **Детали услуги {purchase_id}**\n\n"
        
        # Основная информация
        server_name = purchase.get('server_name', 'N/A')
        text += f"🏠 **Сервер:** {server_name}\n"
        
        # Оставшееся время
        if days_remaining is not None and isinstance(days_remaining, (int, float)):
            if days_remaining > 0:
                text += f"⏰ **Оставшееся время:** {days_remaining} дней\n"
            elif days_remaining == 0:
                text += f"⚠️ **Оставшееся время:** истекает сегодня\n"
            else:
                text += f"❌ **Статус:** истек\n"
        else:
            text += f"⚠️ **Оставшееся время:** неизвестно\n"
        
        # Информация о трафике
        if traffic_info:
            # Преобразование байтов в читаемый формат
            up_formatted = helpers.format_traffic_size(traffic_info.get('up', 0))
            down_formatted = helpers.format_traffic_size(traffic_info.get('down', 0))
            total_bytes = traffic_info.get('up', 0) + traffic_info.get('down', 0)
            total_formatted = helpers.format_traffic_size(total_bytes)
            
            # Общий объем (если сохранен в базе данных)
            total_volume = purchase.get('initial_volume_gb', 0)
            if total_volume > 0:
                total_volume_bytes = total_volume * (1024**3)
                remaining_bytes = total_volume_bytes - total_bytes
                remaining_formatted = helpers.format_traffic_size(remaining_bytes)
            
            text += f"\n📈 **Статистика трафика:**\n"
            text += f"⬆️ Выгружено: {up_formatted}\n"
            text += f"⬇️ Загружено: {down_formatted}\n"
            text += f"📊 Всего использовано: {total_formatted}\n"
            
            if total_volume > 0:
                text += f"💾 Оставшийся объем: {remaining_formatted}\n"
                if remaining_bytes <= 0:
                    text += f"⚠️ **Предупреждение:** объем исчерпан!\n"
        else:
            text += f"\n⚠️ **Информация о трафике:** недоступна\n"
        
        # Ссылка на подписку
        sub_link = ""
        if purchase['sub_id']:
            active_domain_record = _db_manager.get_active_subscription_domain()
            active_domain = active_domain_record['domain_name'] if active_domain_record else None
            
            if not active_domain:
                server = _db_manager.get_server_by_id(purchase['server_id'])
                if server:
                    sub_base = server['subscription_base_url'].rstrip('/')
                    sub_path = server['subscription_path_prefix'].strip('/')
                    sub_link = f"{sub_base}/{sub_path}/{purchase['sub_id']}"
            else:
                sub_link = f"https://{active_domain}/sub/{purchase['sub_id']}"
        
        if sub_link:
            text += f"\n🔗 **Ссылка на подписку:**\n`{sub_link}`\n"
        
        # Кнопки действий
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 Обновить трафик", callback_data=f"user_refresh_traffic_{purchase_id}"),
            types.InlineKeyboardButton("🔄 Обновить ссылку", callback_data=f"user_refresh_subscription_{purchase_id}")
        )
        markup.add(
            types.InlineKeyboardButton("📄 Отдельные конфиги", callback_data=f"user_get_single_configs_{purchase_id}")
        )
        markup.add(types.InlineKeyboardButton("🔙 Назад к услугам", callback_data="user_my_services"))
        
        _bot.edit_message_text(text, user_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        # Отправка QR-кода
        if sub_link:
            try:
                import qrcode
                from io import BytesIO
                qr_image = qrcode.make(sub_link)
                bio = BytesIO()
                bio.name = 'qrcode.jpeg'
                qr_image.save(bio, 'JPEG')
                bio.seek(0)
                _bot.send_photo(user_id, bio, caption=messages.QR_CODE_CAPTION)
            except Exception as e:
                logger.error(f"Failed to generate QR code: {e}")

    def refresh_subscription_link(user_id, purchase_id, message):
        """
        Обновление ссылки на подписку из основной панели
        """
        try:
            # Отображение сообщения об обновлении
            _bot.edit_message_text("⏳ Обновление ссылки на подписку из основной панели...", user_id, message.message_id)
            
            # Получение информации о покупке
            purchase = _db_manager.get_purchase_by_id(purchase_id)
            if not purchase:
                _bot.edit_message_text("❌ Указанная покупка не найдена.", user_id, message.message_id)
                return
            
            # Получение информации о сервере
            server = _db_manager.get_server_by_id(purchase['server_id'])
            if not server:
                _bot.edit_message_text("❌ Информация о сервере не найдена.", user_id, message.message_id)
                return
            
            # Запрос на обновление к серверу веб-хуков
            import requests
            webhook_url = f"https://{os.getenv('WEBHOOK_DOMAIN', 'localhost')}/admin/update_configs/{purchase_id}"
            headers = {
                'Authorization': f'Bearer {os.getenv("ADMIN_API_KEY", "your-secret-key")}'
            }
            
            response = requests.post(webhook_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                _bot.edit_message_text(
                    f"✅ Ссылка на подписку успешно обновлена!\n\n"
                    f"📊 **Детали:**\n"
                    f"• Сервер: {server['name']}\n"
                    f"• Дата обновления: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"🔄 Ваша ссылка теперь содержит последние настройки панели.",
                    user_id, message.message_id, parse_mode='Markdown'
                )
                
                # Повторное отображение деталей услуги
                show_service_details_with_traffic(user_id, purchase_id, message)
            else:
                _bot.edit_message_text(
                    f"❌ Ошибка при обновлении ссылки на подписку.\n"
                    f"Код ошибки: {response.status_code}\n"
                    f"Сообщение: {response.text}",
                    user_id, message.message_id
                )
                
        except Exception as e:
            logger.error(f"Error refreshing subscription link: {e}")
            _bot.edit_message_text(
                f"❌ Ошибка при обновлении ссылки на подписку:\n{str(e)}",
                user_id, message.message_id
            )

    def refresh_traffic_info(user_id, purchase_id, message, call_id=None):
        """
        Обновление информации о трафике
        """
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            if call_id:
                _bot.answer_callback_query(call_id, "❌ Услуга не найдена", show_alert=True)
            return
        
        if not purchase.get('client_uuid'):
            if call_id:
                _bot.answer_callback_query(call_id, "❌ Информация о клиенте недоступна", show_alert=True)
            return
        
        # Получение новой информации о трафике
        traffic_info = _db_manager.get_client_traffic_info(purchase['client_uuid'])
        
        if traffic_info:
            if call_id:
                _bot.answer_callback_query(call_id, "✅ Информация о трафике обновлена")
            # Повторное отображение с новой информацией
            show_service_details_with_traffic(user_id, purchase_id, message)
        else:
            if call_id:
                _bot.answer_callback_query(call_id, "❌ Ошибка при получении информации о трафике", show_alert=True)

    @_bot.callback_query_handler(func=lambda call: call.data.startswith('user_refresh_subscription_'))
    def handle_refresh_subscription_callback(call):
        """Обработка callback-запроса на обновление ссылки подписки"""
        try:
            user_id = call.from_user.id
            purchase_id = int(call.data.split('_')[3])
            
            refresh_subscription_link(user_id, purchase_id, call.message)
            
        except Exception as e:
            logger.error(f"Error in refresh subscription callback: {e}")
            _bot.answer_callback_query(call.id, "❌ Ошибка при обновлении ссылки", show_alert=True)