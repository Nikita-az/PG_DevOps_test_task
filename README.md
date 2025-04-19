# PostgreSQL Auto Installer

Скрипт для автоматической установки и настройки PostgreSQL на удалённый сервер

## Требования

1. Два Linux-сервера (Debian и CentOS/AlmaLinux)
2. Доступ по SSH с ключом к обоим серверам для пользователя root
3. Python 3.8+
4. Библиотеки: `paramiko`

## Установка

1. Клонируйте репозиторий:
 ```
  git clone https://github.com/Nikita-az/PG_DevOps_test_task.git
  cd PG_DevOps_test_task
 ```

2. Установка зависимостей:
  ```
  apt install python-pip3
  pip3 install paramiko
  ```

3. Настройте файл конфигурации config.py:
 ```
   # SSH configuration
  SSH_USER = "root"                   # Пользователь для SSH
  SSH_KEY_PATH = "/path/to/ssh_key"   # Путь к приватному ключу

  # PostgreSQL configuration
  POSTGRES_VERSION = "15"             # Версия PostgreSQL
  POSTGRES_USER = "student"           # Имя пользователя БД
  POSTGRES_PASSWORD = "secure_pass"   # Пароль пользователя
```
4. Запустите скрипт с IP-адресами серверов:
   ```
   python3 main.py 192.168.1.100,192.168.1.101
   ```

5. Пример вывода:
   ```
   Анализ сервера: 192.168.1.100
   Нагрузка на сервер: 0.15

   Выбран сервер для установки PostgreSQL: 192.168.1.100
   Установка PostgreSQL...
   Создание пользователя student...
   Настройка конфигурации...
   PostgreSQL успешно установлен и работает.
   ```

# Проверка установки
1. Подключитесь к PostgreSQL с другого сервера:
   ```
   psql -h 192.168.1.100 -U student -d student_db
   ```

2. Выполните тестовый запрос:
   ```
   SELECT version();
   ```
