import paramiko  
import sys       
import time      
from config import SSH_USER, SSH_KEY_PATH, POSTGRES_VERSION,POSTGRES_USER, POSTGRES_PASSWORD

SERVERS = sys.argv[1].split(',')

def connect_ssh(server):
    key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=SSH_USER, pkey=key)
    return ssh 

def get_cpu_load(ssh):
    stdin, stdout, stderr = ssh.exec_command(
        "uptime | awk -F'load average:' '{ print $2 }' | awk '{print $1}'"
    )
    load_str = stdout.read().decode().strip().replace(',', '.').rstrip('.')
    load = float(load_str)
    return load

def install_postgres(ssh, distro):
    commands = []
    if distro == 'debian':
        commands = [
            'apt update',
            'apt install -y postgresql'
        ]
    elif distro == 'centos':
        commands = [
            'yum install -y postgresql-server postgresql-contrib',
            'postgresql-setup --initdb || postgresql-setup initdb',
            'systemctl enable postgresql',
            'systemctl start postgresql',
            'firewall-cmd --permanent --add-port=5432/tcp',
            'firewall-cmd --reload'
        ]

    for cmd in commands:
        print(f"Выполняется: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        time.sleep(2)

    print("Создание пользователя student...")

    create_commands = [
        ("CREATE ROLE", f"sudo -u postgres psql -tAc \"CREATE USER {POSTGRES_USER} WITH PASSWORD '{POSTGRES_PASSWORD}';\""),
        ("ALTER ROLE", f"sudo -u postgres psql -tAc \"ALTER USER {POSTGRES_USER} WITH LOGIN;\""),
        ("CREATE DATABASE", f"sudo -u postgres psql -tAc \"CREATE DATABASE student_db OWNER {POSTGRES_USER};\""),
        ("GRANT", f"sudo -u postgres psql -tAc \"GRANT ALL PRIVILEGES ON DATABASE student_db TO {POSTGRES_USER};\""),
    ]

    for expected_output, cmd in create_commands:
        print(f"Выполняется: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()

        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if expected_output in out:
            print(f"Успешно: {expected_output}")
        else:
            print(f"Не удалось: {expected_output}")
            print(f"STDOUT: {out}")
            print(f"STDERR: {err}")
        time.sleep(1)

def install_postgres_second(ssh, distro):
    commands = []
    if distro == 'debian':
        commands = [
            'apt update',
            'apt install -y postgresql'
        ]
    elif distro == 'centos':
        commands = [
            'yum install -y postgresql',
            'systemctl enable postgresql',
            'systemctl start postgresql',
        ]

    for cmd in commands:
        print(f"  ➤ Выполняется на втором сервере: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status() 
        time.sleep(2)

def configure_postgres(ssh, distro, second_server_ip):
    if distro == 'debian':
        pg_hba_conf = f"/etc/postgresql/{POSTGRES_VERSION}/main/pg_hba.conf"
        postgresql_conf = f"/etc/postgresql/{POSTGRES_VERSION}/main/postgresql.conf"
    elif distro == 'centos':
        pg_hba_conf = f"/var/lib/pgsql/data/pg_hba.conf"
        postgresql_conf = f"/var/lib/pgsql/data/postgresql.conf"
    else:
        raise ValueError(f"Unsupported distro: {distro}")

    print("Настройка postgresql.conf & pg_hba.conf")

    cmds = [
        (
            "Добавление строки доступа в pg_hba.conf",
            f"echo \"host all {POSTGRES_USER} {second_server_ip}/32 md5\" >> {pg_hba_conf}"
        ),
        (
            "Разрешение подключения на все интерфейсы",
            f"sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" {postgresql_conf}",
        ),
        (
            "Перезапуск PostgreSQL",
            "systemctl restart postgresql"
        )
    ]

    for description, cmd in cmds:
        print(f"{description}: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if exit_code == 0:
            print(f"Успешно: {description}")
        else:
            print(f"Ошибка при: {description}")
            print(f"STDOUT: {out}")
            print(f"STDERR: {err}")
        time.sleep(1)

def test_postgres(ssh):
    test_cmd = "sudo -i -u postgres -- psql -tAc 'SELECT 1'"
    stdin, stdout, stderr = ssh.exec_command(test_cmd)
    result = stdout.read().decode().strip()
    return result == '1'

def detect_distro(ssh):
    stdin, stdout, stderr = ssh.exec_command('cat /etc/os-release')
    os_release = stdout.read().decode()
    if 'debian' in os_release.lower():
        return 'debian'
    else:
        return 'centos'
    
def main():
    loads = {}
    ssh_connections = {}

    for server in SERVERS:
        ssh = connect_ssh(server)
        if not server:
            raise Exception("Не удалось подключиться ни к одному серверу")
        print(f"\nАнализ сервера: {server}")
        ssh_connections[server] = ssh 
        loads[server] = get_cpu_load(ssh)
        print(f"\nНагрузка на сервер: {loads[server]}")

    target_server = min(loads, key=loads.get)
    second_server = [srv for srv in SERVERS if srv != target_server][0]
    print(f"Выбран сервер для установки PostgreSQL: {target_server}")

    target_ssh = ssh_connections[target_server]
    second_ssh = ssh_connections[second_server]
    distro = detect_distro(target_ssh)
    install_postgres(target_ssh, distro)
    configure_postgres(target_ssh, distro, second_server)
    distro = detect_distro(second_ssh)
    install_postgres_second(second_ssh, distro)

    if test_postgres(target_ssh):
        print("PostgreSQL успешно установлен и работает.")
    else:
        print("Ошибка проверки работы PostgreSQL.")

    for ssh in ssh_connections.values():
        ssh.close()

if __name__ == "__main__":
    main()