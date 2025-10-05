# utils/system_helpers.py
import subprocess
import logging
import os

logger = logging.getLogger(__name__)

def run_shell_command(command):
    """Выполняет команду оболочки и возвращает её успех или неудачу."""
    try:
        # Мы используем sudo, так как nginx и certbot требуют прав root
        full_command = ['sudo'] + command
        result = subprocess.run(full_command, check=True, capture_output=True, text=True)
        logger.info(f"Command successful: {' '.join(command)}\nOutput: {result.stdout}")
        return True, ""
    except subprocess.CalledProcessError as e:
        error_message = f"Command failed: {' '.join(command)}\nError: {e.stderr}"
        logger.error(error_message)
        return False, e.stderr

def setup_domain_nginx_and_ssl(domain_name, admin_email):
    """
    Настраивает новый домен в Nginx и получает для него SSL-сертификат от Certbot.
    """
    nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
    nginx_enabled_path = f"/etc/nginx/sites-enabled/{domain_name}"

    # Шаг 1: Создание временной конфигурации Nginx для проверки Certbot
    temp_nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};
    root /var/www/html;
    index index.html index.htm;
}}
"""
    try:
        with open(f"/tmp/{domain_name}.conf", "w") as f:
            f.write(temp_nginx_config)
        run_shell_command(['mv', f'/tmp/{domain_name}.conf', nginx_config_path])
        
        if not os.path.exists(nginx_enabled_path):
             run_shell_command(['ln', '-s', nginx_config_path, nginx_enabled_path])

        # Перезагрузка Nginx для применения временной конфигурации
        success, _ = run_shell_command(['systemctl', 'reload', 'nginx'])
        if not success:
            raise Exception("Failed to reload Nginx with temporary config.")

        # Шаг 2: Выполнение Certbot для получения SSL-сертификата
        certbot_command = [
            'certbot', '--nginx', '-d', domain_name,
            '--email', admin_email, '--agree-tos', '--non-interactive', '--redirect'
        ]
        success, error = run_shell_command(certbot_command)
        if not success:
            raise Exception(f"Certbot failed. Check DNS A record for {domain_name}. Error: {error}")

        # Шаг 3: Создание финальной конфигурации Nginx для Proxy Pass
        # Certbot сам обновляет конфигурацию, нам нужно только убедиться, что Proxy Pass добавлен
        # Для простоты мы переписываем конфигурацию, чтобы убедиться, что она правильная
        final_nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};
    return 301 https://$host$request_uri;
}}
server {{
    listen 443 ssl http2;
    server_name {domain_name};

    ssl_certificate /etc/letsencrypt/live/{domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain_name}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        with open(f"/tmp/{domain_name}.conf", "w") as f:
            f.write(final_nginx_config)
        run_shell_command(['mv', f'/tmp/{domain_name}.conf', nginx_config_path])

        # Шаг 4: Финальная перезагрузка Nginx
        success, _ = run_shell_command(['systemctl', 'reload', 'nginx'])
        if not success:
            raise Exception("Failed to reload Nginx with final config.")
            
        return True, "Domain setup and SSL certificate obtained successfully."

    except Exception as e:
        # Очистка в случае ошибки
        run_shell_command(['rm', '-f', nginx_config_path])
        run_shell_command(['rm', '-f', nginx_enabled_path])
        run_shell_command(['systemctl', 'reload', 'nginx'])
        return False, str(e)
    
def remove_domain_nginx_files(domain_name):
    """Удаляет файлы конфигурации Nginx для указанного домена."""
    nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
    nginx_enabled_path = f"/etc/nginx/sites-enabled/{domain_name}"
    
    logger.info(f"Attempting to remove Nginx files for domain: {domain_name}")
    
    success1, _ = run_shell_command(['rm', '-f', nginx_config_path])
    success2, _ = run_shell_command(['rm', '-f', nginx_enabled_path])
    
    # Перезагрузка Nginx для применения изменений
    reload_success, error = run_shell_command(['systemctl', 'reload', 'nginx'])
    
    return (success1 or success2) and reload_success

def check_ssl_certificate_exists(domain_name):
    """
    Проверяет, существует ли SSL-сертификат для указанного домена в стандартном пути Certbot.
    """
    cert_path = f"/etc/letsencrypt/live/{domain_name}/fullchain.pem"
    key_path = f"/etc/letsencrypt/live/{domain_name}/privkey.pem"
    
    # os.path.exists не требует sudo и достаточно для этой проверки
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"SSL certificate found for domain {domain_name}.")
        return True
    else:
        logger.warning(f"SSL certificate NOT found for domain {domain_name}.")
        return False
    
def run_shell_command(command):
    """
    Выполняет команду оболочки с доступом sudo и возвращает полный результат.
    """
    try:
        full_command = ['sudo'] + command
        # check=False позволяет программе не останавливаться даже в случае ошибки
        result = subprocess.run(full_command, check=False, capture_output=True, text=True, encoding='utf-8')
        
        # Сочетание стандартного вывода и вывода ошибок
        output = result.stdout + result.stderr
        
        if result.returncode == 0:
            logger.info(f"Command successful: {' '.join(command)}")
            return True, output
        else:
            logger.error(f"Command failed with exit code {result.returncode}: {' '.join(command)}\nOutput: {output}")
            return False, output
            
    except Exception as e:
        error_message = f"Exception running command {' '.join(command)}: {e}"
        logger.error(error_message)
        return False, error_message