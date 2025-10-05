# api_client/factory.py

from api_client.xui_api_client import XuiAPIClient
from api_client.alireza_api_client import AlirezaAPIClient
# Когда мы добавим другие панели, их также импортируем сюда
# from api_client.hiddify_api_client import HiddifyAPIClient

import logging

logger = logging.getLogger(__name__)

def get_api_client(server_info: dict):
    """
    Этот метод принимает информацию о сервере и,
    в зависимости от типа панели, возвращает соответствующий API-клиент.
    """
    panel_type = server_info.get('panel_type', 'x-ui').lower()
    panel_url = server_info.get('panel_url')
    username = server_info.get('username')
    password = server_info.get('password')

    if not all([panel_url, username, password]):
        logger.error("Информация о сервере неполная. Невозможно создать API-клиент.")
        return None

    if panel_type == 'alireza':
        logger.info(f"Создание AlirezaAPIClient для сервера: {server_info.get('name')}")
        return AlirezaAPIClient(panel_url=panel_url, username=username, password=password)
    
    # elif panel_type == 'hiddify':
    #     # В Hiddify 'username' — это UUID администратора
    #     return HiddifyAPIClient(panel_url=panel_url, admin_uuid=username)

    elif panel_type == 'x-ui':
        logger.info(f"Создание XuiAPIClient по умолчанию для сервера: {server_info.get('name')}")
        return XuiAPIClient(panel_url=panel_url, username=username, password=password)
    
    else:
        logger.error(f"Неизвестный тип панели: '{panel_type}'. Используется XuiAPIClient по умолчанию.")
        # Fallback to the default client if the type is unknown
        return XuiAPIClient(panel_url=panel_url, username=username, password=password)