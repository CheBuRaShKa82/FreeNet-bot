# webhook_server.py (Финальная версия с сервером подписки и логикой разделения покупок)

from flask import Flask, request, render_template, Response
import requests
import json
import logging
import os
import sys
import datetime
import base64
import telebot
from urllib.parse import quote
from utils import messages

# Добавление пути проекта к sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# Импорт модулей проекта
from config import BOT_TOKEN, BOT_USERNAME
from database.db_manager import DatabaseManager
from utils.bot_helpers import send_subscription_info, finalize_profile_purchase
from utils.config_generator import ConfigGenerator
from api_client.xui_api_client import XuiAPIClient # Для обычной покупки

# Начальные настройки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
db_manager = DatabaseManager()
bot = telebot.TeleBot(BOT_TOKEN)
# Экземпляр генератора конфигураций для обычной покупки
config_gen_normal = ConfigGenerator(db_manager)

ZARINPAL_VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
BOT_USERNAME = BOT_USERNAME

# --- Вспомогательная функция для построения конфигурации ---
def build_config_link(synced_config, client_uuid, client_remark):
    """
    С использованием сырых синхронизированных данных и основного адреса сервера строит финальную ссылку конфигурации.
    """
    try:
        # --- Основное исправление здесь ---
        # Читаем адрес из данных самой конфигурации, а не из антифильтр-домена
        server_address = synced_config['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
        
        port = synced_config['port']
        remark = f"{client_remark} - {synced_config['remark']}"
        
        if synced_config['protocol'] == 'vless':
            stream_settings = json.loads(synced_config['stream_settings'])
            protocol_settings = json.loads(synced_config['settings'])
            
            params = {
                'type': stream_settings.get('network', 'tcp'),
                'security': stream_settings.get('security', 'none')
            }

            flow = protocol_settings.get('clients', [{}])[0].get('flow', '')
            if flow:
                params['flow'] = flow

            if params['security'] == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                nested_tls_settings = tls_settings.get('settings', {})
                params['fp'] = nested_tls_settings.get('fingerprint', '')
                params['sni'] = tls_settings.get('serverName', server_address)

            if params['security'] == 'reality':
                reality_settings = stream_settings.get('realitySettings', {})
                nested_reality_settings = reality_settings.get('settings', {})
                params['pbk'] = nested_reality_settings.get('publicKey', '')
                params['fp'] = nested_reality_settings.get('fingerprint', '')
                params['sni'] = reality_settings.get('serverName', server_address)
                params['sid'] = reality_settings.get('shortId', '')

            if params['type'] == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                params['path'] = ws_settings.get('path', '/')
                params['host'] = ws_settings.get('headers', {}).get('Host', server_address)

            if params['type'] == 'grpc':
                grpc_settings = stream_settings.get('grpcSettings', {})
                params['serviceName'] = grpc_settings.get('serviceName', '')

            # Построение строки параметров
            param_str = '&'.join([f"{k}={quote(v)}" for k, v in params.items() if v])

            return f"vless://{client_uuid}@{server_address}:{port}?{param_str}#{quote(remark)}"

        elif synced_config['protocol'] == 'vmess':
            # Логика для VMess
            pass

        elif synced_config['protocol'] == 'trojan':
            # Логика для Trojan
            pass

        return None

    except Exception as e:
        logger.error(f"Error building config link: {e}")
        return None

# --- Endpoint для проверки платежа ---
@app.route('/payment/verify', methods=['GET'])
def payment_verify():
    """
    Обработка подтверждения платежа от ZarinPal и уведомление пользователя.
    """
    authority = request.args.get('Authority')
    status = request.args.get('Status')

    if status != 'OK':
        logger.error(f"Payment verification failed for authority {authority}: Status={status}")
        return render_template('payment_status.html', status='failed', message='پرداخت لغو شد یا ناموفق بود.')

    try:
        purchase = db_manager.get_purchase_by_authority(authority)
        if not purchase:
            logger.error(f"No purchase found for authority {authority}")
            return render_template('payment_status.html', status='failed', message='خرید مرتبط یافت نشد.')

        payment = db_manager.get_payment_by_authority(authority)
        if not payment:
            logger.error(f"No payment found for authority {authority}")
            return render_template('payment_status.html', status='failed', message='پرداخت مرتبط یافت نشد.')

        # Проверка платежа через ZarinPal
        verify_data = {
            "merchant_id": ZARINPAL_MERCHANT_ID,
            "authority": authority,
            "amount": payment['amount'] * 10  # Конвертация в риалы
        }

        response = requests.post(ZARINPAL_VERIFY_URL, json=verify_data)
        verify_result = response.json()

        if verify_result['data']['code'] == 100:
            ref_id = verify_result['data']['ref_id']
            
            # Обновление статуса платежа
            db_manager.confirm_payment(payment['id'], ref_id)

            # Финализация покупки
            if purchase['profile_id']:
                finalize_profile_purchase(purchase, bot)
            else:
                # Для обычной покупки
                configs, client_details = config_gen_normal.create_subscription_for_server(
                    purchase['user_id'],
                    purchase['server_id'],
                    purchase['initial_volume_gb'],
                    purchase['duration_days']
                )
                if configs:
                    db_manager.update_purchase_client_details(purchase['id'], client_details)
                    send_subscription_info(bot, purchase['user_id'], configs)

            logger.info(f"Payment verified successfully for authority {authority}, ref_id={ref_id}")
            return render_template('payment_status.html', status='success', ref_id=ref_id)

        else:
            logger.error(f"Payment verification failed for authority {authority}: {verify_result}")
            return render_template('payment_status.html', status='failed', message='تایید پرداخت ناموفق بود.')

    except Exception as e:
        logger.error(f"Error in payment verification: {e}")
        return render_template('payment_status.html', status='failed', message='خطا در پردازش پرداخت.')

# --- Endpoint для обновления конфигураций ---
@app.route('/update_configs/<int:purchase_id>', methods=['POST'])
def user_update_configs(purchase_id):
    """
    Endpoint для обновления конфигураций пользователем.
    """
    try:
        logger.info(f"User requested config update for purchase {purchase_id}")
        success = update_cached_configs_from_panel(purchase_id)
        
        if success:
            logger.info(f"User successfully updated configs for purchase {purchase_id}")
            return Response("Configs updated successfully", status=200)
        else:
            logger.error(f"User failed to update configs for purchase {purchase_id}")
            return Response("Failed to update configs", status=500)
            
    except Exception as e:
        logger.error(f"Error in user_update_configs: {e}")
        return Response("Internal server error", status=500)

# --- Функция для обновления кэшированных конфигураций из панели ---
def update_cached_configs_from_panel(purchase_id):
    """
    Обновление кэшированных конфигураций из панели.
    """
    try:
        purchase = db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            logger.error(f"Purchase {purchase_id} not found")
            return False

        if purchase['profile_id']:
            # Для профиля
            profile_inbounds = db_manager.get_inbounds_for_profile(purchase['profile_id'])
            configs = []
            for inbound in profile_inbounds:
                synced_config = db_manager.get_synced_config(inbound['server_id'], inbound['inbound_id'])
                if synced_config:
                    config_link = build_config_link(synced_config, purchase['client_uuid'], purchase['client_remark'])
                    if config_link:
                        configs.append(config_link)
            if configs:
                db_manager.update_purchase_configs(purchase_id, json.dumps(configs))
                return True
        else:
            # Для обычной покупки
            server = db_manager.get_server_by_id(purchase['server_id'])
            if server:
                api_client = get_api_client(server)
                if api_client:
                    inbound = api_client.get_inbound(purchase['inbound_id'])
                    if inbound:
                        config_link = build_config_link(inbound, purchase['client_uuid'], purchase['client_remark'])
                        if config_link:
                            db_manager.update_purchase_configs(purchase_id, json.dumps([config_link]))
                            return True

        return False

    except Exception as e:
        logger.error(f"Error updating configs from panel: {e}")
        return False

# --- Endpoint для подписки ---
@app.route('/sub/<sub_id>', methods=['GET'])
def get_subscription(sub_id):
    """
    Endpoint для получения конфигураций подписки.
    """
    try:
        logger.info(f"Subscription request for sub_id {sub_id}")
        purchase = db_manager.get_purchase_by_sub_id(sub_id)
        if not purchase:
            logger.error(f"No purchase found for sub_id {sub_id}")
            return Response("Subscription not found", status=404)

        configs_json = purchase.get('single_configs_json')
        if configs_json:
            configs = json.loads(configs_json)
            subscription_content = '\n'.join(configs)
            return Response(subscription_content, status=200, mimetype='text/plain')
        else:
            logger.warning(f"No configs found for purchase {purchase['id']}. Fetching from panel.")
            success = update_cached_configs_from_panel(purchase['id'])
            if success:
                return get_subscription(sub_id)  # Рекурсивный вызов для получения обновлённых конфигураций
            else:
                return Response("Failed to fetch configs", status=500)

    except Exception as e:
        logger.error(f"Error in get_subscription: {e}")
        return Response("Internal server error", status=500)

# --- Административный endpoint для обновления всех конфигураций ---
@app.route('/admin/update_all_configs', methods=['POST'])
def admin_update_all_configs():
    """
    Endpoint для обновления всех конфигураций администратором.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != 'Bearer your-secret-key':  # Замените на реальный ключ
            logger.error("Unauthorized access to admin_update_all_configs")
            return Response("Unauthorized", status=401)

        logger.info("Admin requested update for all configs")
        purchases = db_manager.get_all_active_purchases()
        updated_count = 0
        for purchase in purchases:
            success = update_cached_configs_from_panel(purchase['id'])
            if success:
                updated_count += 1

        logger.info(f"Admin updated {updated_count}/{len(purchases)} configs")
        return Response(f"Updated {updated_count} configs", status=200)

    except Exception as e:
        logger.error(f"Error in admin_update_all_configs: {e}")
        return Response("Internal server error", status=500)

# --- Административный endpoint для обновления конфигурации конкретной покупки ---
@app.route('/admin/update_configs/<purchase_id>', methods=['POST'])
def admin_update_configs(purchase_id):
    """
    Endpoint для обновления конфигурации конкретной покупки администратором.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != 'Bearer your-secret-key':  # Замените на реальный ключ
            logger.error(f"Unauthorized access to admin_update_configs for purchase {purchase_id}")
            return Response("Unauthorized", status=401)

        logger.info(f"Starting config update for purchase {purchase_id} (type: {'profile' if purchase.get('profile_id') else 'normal'})")
        success = update_cached_configs_from_panel(int(purchase_id))
        
        if success:
            logger.info(f"Successfully updated configs for purchase {purchase_id}")
            return Response("Configs updated successfully", status=200)
        else:
            logger.error(f"Failed to update configs for purchase {purchase_id}")
            return Response("Failed to update configs", status=500)
            
    except ValueError as e:
        logger.error(f"Invalid purchase_id format: {purchase_id}, error: {e}")
        return Response("Invalid purchase ID format", status=400)
    except Exception as e:
        logger.error(f"Unexpected error in admin_update_configs for purchase {purchase_id}: {e}")
        return Response("Internal server error", status=500)

# --- Endpoint для тестирования статуса покупки ---
@app.route('/admin/test/<purchase_id>', methods=['GET'])
def admin_test_purchase(purchase_id):
    """
    Endpoint для тестирования статуса покупки.
    """
    try:
        logger.info(f"🔍 Testing purchase {purchase_id}")
        purchase = db_manager.get_purchase_by_id(int(purchase_id))
        if not purchase:
            logger.error(f"❌ Purchase {purchase_id} not found")
            return Response("Purchase not found", status=404)
        
        result = {
            'purchase_id': purchase['id'],
            'user_id': purchase['user_id'],
            'profile_id': purchase.get('profile_id'),
            'server_id': purchase.get('server_id'),
            'sub_id': purchase.get('sub_id'),
            'is_active': purchase['is_active'],
            'has_configs': bool(purchase.get('single_configs_json'))
        }
        
        logger.info(f"✅ Purchase {purchase_id} test successful: {result}")
        return Response(json.dumps(result, indent=2), status=200, mimetype='application/json')
        
    except Exception as e:
        logger.error(f"❌ Error in admin_test_purchase: {e}")
        return Response("Internal server error", status=500)

# --- Простой endpoint для тестирования ---
@app.route('/test', methods=['GET'])
def simple_test():
    """
    Простой endpoint для проверки работы webhook-сервера.
    """
    try:
        logger.info("🔍 Simple test endpoint called")
        result = {
            'status': 'ok',
            'message': 'Webhook server is working',
            'timestamp': datetime.datetime.now().isoformat()
        }
        logger.info("✅ Simple test successful")
        return Response(json.dumps(result, indent=2), status=200, mimetype='application/json')
        
    except Exception as e:
        logger.error(f"❌ Error in simple_test: {e}")
        return Response("Internal server error", status=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)