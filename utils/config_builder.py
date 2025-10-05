#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Config Builder - Построение конфигураций напрямую из данных панели
Полная поддержка всех протоколов и параметров
"""

import json
import base64
import logging
from urllib.parse import quote
from api_client.xui_api_client import XuiAPIClient
from api_client.alireza_api_client import AlirezaAPIClient

logger = logging.getLogger(__name__)

def get_api_client(server_info):
    """
    Построение API client на основе типа панели
    """
    panel_type = server_info.get('panel_type', 'xui')
    
    if panel_type == 'alireza':
        return AlirezaAPIClient(
            panel_url=server_info['panel_url'],
            username=server_info['username'],
            password=server_info['password']
        )
    else:  # xui
        return XuiAPIClient(
            panel_url=server_info['panel_url'],
            username=server_info['username'],
            password=server_info['password']
        )

def detect_protocol(inbound_info):
    """
    Определение протокола из информации inbound
    """
    try:
        # Проверка различных полей для определения протокола
        protocol = inbound_info.get('protocol', '').lower()
        proxy_type = inbound_info.get('proxy_type', '').lower()
        proxyType = inbound_info.get('proxyType', '').lower()
        
        # Список поддерживаемых протоколов
        supported_protocols = [
            'vless', 'vmess', 'trojan', 'shadowsocks', 'dokodemo-door',
            'tcp', 'httpupgrade', 'ws', 'grpc', 'mkcp', 'quic', 'http', 'h2'
        ]
        
        # Определение основного протокола
        detected_protocol = None
        
        # Приоритет 1: поле protocol
        if protocol in supported_protocols:
            detected_protocol = protocol
        # Приоритет 2: поле proxy_type
        elif proxy_type in supported_protocols:
            detected_protocol = proxy_type
        # Приоритет 3: поле proxyType
        elif proxyType in supported_protocols:
            detected_protocol = proxyType
        
        # Если протокол не определён, по умолчанию VLESS
        if not detected_protocol:
            detected_protocol = 'vless'
            logger.warning(f"Protocol not detected, defaulting to VLESS")
        
        logger.info(f"Detected protocol: {detected_protocol}")
        return detected_protocol
        
    except Exception as e:
        logger.error(f"Error detecting protocol: {e}")
        return 'vless'  # По умолчанию

def extract_stream_parameters(stream_settings):
    """
    Извлечение всех параметров stream settings
    """
    try:
        if isinstance(stream_settings, str):
            stream_settings = json.loads(stream_settings)
        
        params = {}
        
        # Тип сети
        params['network'] = stream_settings.get('network', 'tcp')
        
        # Тип безопасности
        params['security'] = stream_settings.get('security', 'none')
        
        # Настройки TLS
        if params['security'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            params['tls'] = {
                'serverName': tls_settings.get('serverName', ''),
                'alpn': tls_settings.get('alpn', []),
                'fingerprint': tls_settings.get('settings', {}).get('fingerprint', ''),
                'echConfigList': tls_settings.get('settings', {}).get('echConfigList', ''),
                'allowInsecure': tls_settings.get('settings', {}).get('allowInsecure', False),
                'utls': tls_settings.get('settings', {}).get('utls', False),
                'externalProxy': tls_settings.get('externalProxy', False)
            }
        
        # Настройки Reality
        elif params['security'] == 'reality':
            reality_settings = stream_settings.get('realitySettings', {})
            params['reality'] = {
                'dest': reality_settings.get('dest', ''),
                'fingerprint': reality_settings.get('settings', {}).get('fingerprint', ''),
                'publicKey': reality_settings.get('settings', {}).get('publicKey', ''),
                'shortIds': reality_settings.get('shortIds', []),
                'spiderX': reality_settings.get('spiderX', ''),
                'serverNames': reality_settings.get('serverNames', [])
            }
        
        # Настройки WebSocket
        if params['network'] == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            params['ws'] = {
                'path': ws_settings.get('path', ''),
                'host': ws_settings.get('host', ''),  # Сначала прямой host
                'headers': ws_settings.get('headers', {})
            }
            # Если host в headers, заменить им
            if ws_settings.get('headers', {}).get('Host', ''):
                params['ws']['host'] = ws_settings.get('headers', {}).get('Host', '')
        
        # Настройки HTTP/HTTPUpgrade
        elif params['network'] in ['http', 'httpupgrade', 'h2']:
            http_settings = stream_settings.get('httpSettings', {})
            params['http'] = {
                'path': http_settings.get('path', ''),
                'host': http_settings.get('host', ''),
                'method': http_settings.get('method', 'GET')
            }
        
        # Настройки gRPC
        elif params['network'] == 'grpc':
            grpc_settings = stream_settings.get('grpcSettings', {})
            params['grpc'] = {
                'serviceName': grpc_settings.get('serviceName', ''),
                'multiMode': grpc_settings.get('multiMode', False)
            }
        
        # Настройки mKCP
        elif params['network'] == 'mkcp':
            mkcp_settings = stream_settings.get('kcpSettings', {})
            params['mkcp'] = {
                'mtu': mkcp_settings.get('mtu', 1350),
                'tti': mkcp_settings.get('tti', 50),
                'uplinkCapacity': mkcp_settings.get('uplinkCapacity', 5),
                'downlinkCapacity': mkcp_settings.get('downlinkCapacity', 20),
                'congestion': mkcp_settings.get('congestion', False),
                'readBufferSize': mkcp_settings.get('readBufferSize', 2),
                'writeBufferSize': mkcp_settings.get('writeBufferSize', 2),
                'header': mkcp_settings.get('header', {})
            }
        
        # Настройки QUIC
        elif params['network'] == 'quic':
            quic_settings = stream_settings.get('quicSettings', {})
            params['quic'] = {
                'security': quic_settings.get('security', 'none'),
                'key': quic_settings.get('key', ''),
                'header': quic_settings.get('header', {})
            }
        
        # Настройки TCP
        elif params['network'] == 'tcp':
            tcp_settings = stream_settings.get('tcpSettings', {})
            params['tcp'] = {
                'header': tcp_settings.get('header', {})
            }
        
        return params
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing stream_settings: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error in extract_stream_parameters: {e}")
        return {}

def build_vless_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    Построение конфигурации VLESS
    """
    try:
        # Извлечение параметров stream
        stream_params = extract_stream_parameters(inbound_info.get('streamSettings', {}))
        
        # Основные параметры
        uuid = client_info.get('id', '')
        address = server_info.get('panel_url', '').split('://')[1].split(':')[0]  # Извлечение хоста
        port = inbound_info.get('port', '')
        client_email = client_info.get('email', '')
        client_name = f"{brand_name}_{client_email}"
        
        # Базовый URL
        base_url = f"vless://{uuid}@{address}:{port}"
        
        # Параметры запроса
        params = []
        
        # Тип сети
        network = stream_params.get('network', 'tcp')
        if network != 'tcp':
            params.append(f"type={network}")
        
        # Тип безопасности
        security = stream_params.get('security', 'none')
        if security != 'none':
            params.append(f"security={security}")
        
        # Настройки TLS
        if 'tls' in stream_params:
            tls_params = stream_params['tls']
            sni = tls_params.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
            
            alpn = ','.join(tls_params.get('alpn', []))
            if alpn:
                params.append(f"alpn={alpn}")
            
            fp = tls_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            if tls_params.get('allowInsecure', False):
                params.append("allowInsecure=1")
            
            if tls_params.get('utls', False):
                params.append("utls=1")
            
            if tls_params.get('externalProxy', False):
                params.append("externalProxy=1")
        
        # Настройки Reality
        elif 'reality' in stream_params:
            reality_params = stream_params['reality']
            dest = reality_params.get('dest', '')
            if dest:
                params.append(f"dest={dest}")
            
            fp = reality_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            pbk = reality_params.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
            
            short_ids = ','.join(reality_params.get('shortIds', []))
            if short_ids:
                params.append(f"sid={short_ids}")
            
            spider_x = reality_params.get('spiderX', '')
            if spider_x:
                params.append(f"spx={spider_x}")
            
            server_names = ','.join(reality_params.get('serverNames', []))
            if server_names:
                params.append(f"sni={server_names}")
        
        # Настройки WebSocket
        if network == 'ws':
            ws_params = stream_params.get('ws', {})
            path = ws_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = ws_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # Настройки HTTP/HTTPUpgrade
        elif network in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            path = http_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = http_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # Настройки gRPC
        elif network == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            service_name = grpc_params.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # Настройки mKCP
        elif network == 'mkcp':
            mkcp_params = stream_params.get('mkcp', {})
            # Добавление параметров mKCP, если нужно
            pass
        
        # Настройки QUIC
        elif network == 'quic':
            quic_params = stream_params.get('quic', {})
            # Добавление параметров QUIC, если нужно
            pass
        
        # Добавление flow для XTLS
        flow = client_info.get('flow', '')
        if flow:
            params.append(f"flow={flow}")
        
        # Построение финального URL
        if params:
            base_url += "?" + "&".join(params)
        
        # Добавление фрагмента (имя клиента)
        final_url = f"{base_url}#{quote(client_name)}"
        
        logger.info(f"Built VLESS config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error building VLESS config: {e}")
        return None

def build_vmess_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    Построение конфигурации VMess
    """
    try:
        # Извлечение параметров stream
        stream_params = extract_stream_parameters(inbound_info.get('streamSettings', {}))
        
        # Основные параметры
        uuid = client_info.get('id', '')
        address = server_info.get('panel_url', '').split('://')[1].split(':')[0]  # Извлечение хоста
        port = inbound_info.get('port', '')
        client_email = client_info.get('email', '')
        client_name = f"{brand_name}_{client_email}"
        
        # VMess конфигурация
        vmess_obj = {
            "v": "2",
            "ps": client_name,
            "add": address,
            "port": port,
            "id": uuid,
            "aid": "0",
            "scy": "auto",
            "net": stream_params.get('network', 'tcp'),
            "type": "none",
            "host": "",
            "path": "",
            "tls": stream_params.get('security', 'none'),
            "sni": "",
            "alpn": "",
            "fp": ""
        }
        
        # Настройки сети
        network = vmess_obj["net"]
        
        # Настройки TLS
        if vmess_obj["tls"] == 'tls':
            tls_params = stream_params.get('tls', {})
            vmess_obj["sni"] = tls_params.get('serverName', '')
            vmess_obj["alpn"] = ','.join(tls_params.get('alpn', []))
            vmess_obj["fp"] = tls_params.get('fingerprint', '')
        
        # Настройки WebSocket
        if network == 'ws':
            ws_params = stream_params.get('ws', {})
            vmess_obj["path"] = ws_params.get('path', '')
            vmess_obj["host"] = ws_params.get('host', '')
        
        # Настройки HTTP/HTTPUpgrade
        elif network in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            vmess_obj["path"] = http_params.get('path', '')
            vmess_obj["host"] = http_params.get('host', '')
        
        # Настройки gRPC
        elif network == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            vmess_obj["path"] = grpc_params.get('serviceName', '')
        
        # Кодирование в Base64
        vmess_json = json.dumps(vmess_obj)
        vmess_b64 = base64.b64encode(vmess_json.encode('utf-8')).decode('utf-8')
        final_url = f"vmess://{vmess_b64}"
        
        logger.info(f"Built VMess config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error building VMess config: {e}")
        return None

def build_trojan_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    Построение конфигурации Trojan
    """
    try:
        # Извлечение параметров stream
        stream_params = extract_stream_parameters(inbound_info.get('streamSettings', {}))
        
        # Основные параметры
        password = client_info.get('password', '') or client_info.get('id', '')
        address = server_info.get('panel_url', '').split('://')[1].split(':')[0]  # Извлечение хоста
        port = inbound_info.get('port', '')
        client_email = client_info.get('email', '')
        client_name = f"{brand_name}_{client_email}"
        
        # Базовый URL
        base_url = f"trojan://{password}@{address}:{port}"
        
        # Параметры запроса
        params = []
        
        # Тип сети
        network = stream_params.get('network', 'tcp')
        if network != 'tcp':
            params.append(f"type={network}")
        
        # Тип безопасности
        security = stream_params.get('security', 'none')
        if security != 'none':
            params.append(f"security={security}")
        
        # Настройки TLS
        if 'tls' in stream_params:
            tls_params = stream_params['tls']
            sni = tls_params.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
            
            alpn = ','.join(tls_params.get('alpn', []))
            if alpn:
                params.append(f"alpn={alpn}")
            
            fp = tls_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            if tls_params.get('allowInsecure', False):
                params.append("allowInsecure=1")
            
            if tls_params.get('utls', False):
                params.append("utls=1")
            
            if tls_params.get('externalProxy', False):
                params.append("externalProxy=1")
        
        # Настройки Reality
        elif 'reality' in stream_params:
            reality_params = stream_params['reality']
            dest = reality_params.get('dest', '')
            if dest:
                params.append(f"dest={dest}")
            
            fp = reality_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            pbk = reality_params.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
            
            short_ids = ','.join(reality_params.get('shortIds', []))
            if short_ids:
                params.append(f"sid={short_ids}")
            
            spider_x = reality_params.get('spiderX', '')
            if spider_x:
                params.append(f"spx={spider_x}")
            
            server_names = ','.join(reality_params.get('serverNames', []))
            if server_names:
                params.append(f"sni={server_names}")
        
        # Настройки WebSocket
        if network == 'ws':
            ws_params = stream_params.get('ws', {})
            path = ws_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = ws_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # Настройки HTTP/HTTPUpgrade
        elif network in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            path = http_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = http_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # Настройки gRPC
        elif network == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            service_name = grpc_params.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # Настройки mKCP
        elif network == 'mkcp':
            mkcp_params = stream_params.get('mkcp', {})
            # Добавление параметров mKCP, если нужно
            pass
        
        # Настройки QUIC
        elif network == 'quic':
            quic_params = stream_params.get('quic', {})
            # Добавление параметров QUIC, если нужно
            pass
        
        # Добавление flow для XTLS
        flow = client_info.get('flow', '')
        if flow:
            params.append(f"flow={flow}")
        
        # Построение финального URL
        if params:
            base_url += "?" + "&".join(params)
        
        # Добавление фрагмента (имя клиента)
        final_url = f"{base_url}#{quote(client_name)}"
        
        logger.info(f"Built Trojan config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error building Trojan config: {e}")
        return None

def build_config_from_panel(server_info, inbound_id, client_id, brand_name="Alamor"):
    """
    Построение конфигурации из данных панели с автоматическим определением протокола
    """
    try:
        logger.info(f"Building config for client {client_id} in inbound {inbound_id}")
        
        # Построение API client
        api_client = get_api_client(server_info)
        if not api_client.check_login():
            logger.error(f"Failed to login to panel {server_info.get('name', 'Unknown')}")
            return None
        
        # Получение информации inbound
        inbound_info = api_client.get_inbound(inbound_id)
        if not inbound_info:
            logger.error(f"Failed to get inbound {inbound_id}")
            return None
        
        # Получение информации клиента
        client_info = api_client.get_client_info(client_id)
        if not client_info:
            logger.error(f"Failed to get client {client_id}")
            logger.error(f"Client ID type: {type(client_id)}")
            logger.error(f"Client ID value: {client_id}")
            return None
        
        logger.info(f"Retrieved client info: {client_info.get('email', 'N/A')}")
        logger.info(f"Client info keys: {list(client_info.keys())}")
        logger.info(f"Client ID from panel: {client_info.get('id', 'N/A')}")
        logger.info(f"Client ID type from panel: {type(client_info.get('id', 'N/A'))}")
        logger.info(f"Full client info: {json.dumps(client_info, indent=2)}")
        
        # Определение типа протокола
        protocol = detect_protocol(inbound_info)
        logger.info(f"Detected protocol: {protocol}")
        logger.info(f"Inbound info keys: {list(inbound_info.keys())}")
        logger.info(f"Full inbound info: {inbound_info}")
        
        # Построение конфигурации на основе протокола
        config = None
        
        if protocol == 'vless':
            logger.info("Building VLESS config...")
            config = build_vless_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ VLESS config built successfully!")
            else:
                logger.error("❌ Failed to build VLESS config")
        
        elif protocol == 'vmess':
            logger.info("Building VMess config...")
            config = build_vmess_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ VMess config built successfully!")
            else:
                logger.error("❌ Failed to build VMess config")
        
        elif protocol == 'trojan':
            logger.info("Building Trojan config...")
            config = build_trojan_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ Trojan config built successfully!")
            else:
                logger.error("❌ Failed to build Trojan config")
        
        else:
            logger.error(f"Unsupported protocol: {protocol}")
            return None
        
        if not config:
            logger.error(f"Failed to build {protocol} config")
            return None
        
        if config:
            logger.info(f"Successfully built {protocol} config for client {client_id}")
            return {
                'protocol': protocol,
                'config': config,
                'client_email': client_info.get('email', ''),
                'client_name': client_info.get('name', ''),
                'inbound_id': inbound_id,
                'server_name': server_info.get('name', 'Unknown')
            }
        else:
            logger.error(f"Failed to build config for client {client_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error building config from panel: {e}")
        return None

def test_config_builder(server_info, inbound_id, client_id):
    """
    Тестирование функции построения конфигурации
    """
    try:
        logger.info(f"Testing config builder for server: {server_info.get('name', 'Unknown')}")
        
        result = build_config_from_panel(server_info, inbound_id, client_id)
        
        if result:
            logger.info("✅ Config built successfully!")
            logger.info(f"Protocol: {result['protocol']}")
            logger.info(f"Client: {result['client_email']}")
            logger.info(f"Server: {result['server_name']}")
            logger.info(f"Config length: {len(result['config'])} characters")
            logger.info(f"Full config: {result['config']}")
            return result
        else:
            logger.error("❌ Failed to build config")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error in test_config_builder: {e}")
        return None