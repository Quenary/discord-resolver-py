import dns.resolver
import dns.query
import dns.message
import json
from tqdm import tqdm
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

configPath = "config.json"
ipsFilePath = './dest/ips.txt'
domainsFilePath = './dest/voice_domains.txt'
cidrFilePath = './dest/cidr.txt'
config = {
    "dns": ["1.1.1.1", "8.8.8.8", "9.9.9.9"],
    "dnsQuery": "tls",
    "regions": [
        "atlanta",
        "brazil", 
        "bucharest",
        "buenos-aires",
        "dubai", 
        "finland", 
        "frankfurt",
        "hongkong",
        "india", 
        "japan",
        "madrid",
        "milan",
        "newark",
        "rotterdam",
        "russia",
        "santa-clara",
        "santiago",
        "seattle",
        "singapore",
        "south-korea",
        "southafrica",
        "stage-scale",
        "stockholm",
        "sydney",
        "tel-aviv",
        "us-central",
        "us-east",
        "us-south",
        "us-west",
        "warsaw",
    ],
    "voiceBaseDomain": "discord.gg",
    "dnsTimeout": 0.1,
    "mainDomains": [
        "dis.gd",
        "disboard.org",
        "discord.center",
        "discord.co",
        "discord.com",
        "discord.dev",
        "discord.gg",
        "gateway.discord.gg",
        "cdn.discordapp.com",
        "static.discordapp.com",
        "status.discordapp.com",
        "updates.discord.com",
        "users.discordapp.com",
        "apps.discordapp.com",
        "discord.gift",
        "discord.me",
        "discord.media",
        "discord.new",
        "discord.st",
        "discordInvites.net",
        "discordapp.com",
        "discordapp.net",
        "discordbee.com",
        "discordbotlist.com",
        "discordcdn.com",
        "discordexpert.com",
        "discordhome.com",
        "discordhub.com",
        "discordlist.me",
        "discordlist.space",
        "discords.com",
        "discordservers.com",
        "discordstatus.com",
        "discordtop.com",
        "disforge.com",
        "dyno.gg",
        "findAdiscord.com",
        "mee6.xyz",
        "top.gg",
        "discord.design",
        "discord.gifts",
        "discord.store",
        "discord.tools",
        "discordmerch.com",
        "discordpartygames.com",
        "discord-activities.com",
        "discordactivities.com",
        "discordsays.com",
        "discordapp.io"
    ],
    "entriesPerRegion": 9999,
    "clearFiles": True,
    "workersCount": 20,
}
ports = {
    "tls":853,
    "https":443,
    "udp":53,
}

try:
    with open(configPath, 'r') as file:
        data = json.load(file)
        config.update({
            'dns': data.get('dns', config['dns']),
            'dnsQuery': data.get('dnsQuery', config['dnsQuery']),
            'dnsTimeout': data.get('dnsTimeout', config['dnsTimeout']),
            'regions': data.get('regions', config['regions']),
            'voiceBaseDomain': data.get('voiceBaseDomain', config['voiceBaseDomain']),
            'mainDomains': data.get('mainDomains', config['mainDomains']),
            'entriesPerRegion': data.get('entriesPerRegion', config['entriesPerRegion']),
            'workersCount': data.get('workersCount', config['workersCount']),
        })
        ipsFilePath = data.get('ipsFile', ipsFilePath)
        domainsFilePath = data.get('domainsFile', domainsFilePath)
        cidrFilePath = data.get('cidrFile', cidrFilePath)
        
        
except FileNotFoundError:
    print(f"File {configPath} not found.")
except json.JSONDecodeError:
    print(f"Error decoding JSON in the file {configPath}.")
    
if config['clearFiles']:
    open(ipsFilePath, 'w').close()
    open(domainsFilePath, 'w')
    open(cidrFilePath, 'w').close()

# Функция для выполнения запроса DNS
def fetch_dns(server, request, dnsQuery, port, timeout):
    try:
        if dnsQuery == 'tls':
            response = dns.query.tls(request, server, port=port, timeout=timeout)
        elif dnsQuery == 'https':
            response = dns.query.https(request, server, port=port, timeout=timeout)
        else:
            response = dns.query.udp(request, server, port=port, timeout=timeout)

        # Проверяем, есть ли записи в ответе
        if response.answer:
            ips = [answer.address for answer in response.answer[0]]
            return ips if ips else "NO_RECORDS"
        else:
            return "NO_RECORDS"

    except Exception as e:
        return None

# Функция для получения IP-адресов с использованием пула потоков
def get_ip_addresses(domain, dnsServers=["1.1.1.1", "8.8.8.8", "9.9.9.9"], dnsQuery='tls', port=853, timeout=0.1):
    request = dns.message.make_query(domain, "A")
    
    with ThreadPoolExecutor(max_workers=len(dnsServers)) as executor:
        futures = [executor.submit(fetch_dns, server, request, dnsQuery, port, timeout) for server in dnsServers]
        
        for future in as_completed(futures):
            result = future.result()
            if result == "NO_RECORDS":
                return []  # Завершаем выполнение, если ответ успешный, но записей нет
            
            if result:  # Если есть IP-адреса
                return result  # Возвращаем первый успешный результат с IP-адресами

    return []  # Если не было успешных ответов


def process_main_domains():
    with open(ipsFilePath, 'a') as ipsFile, open (domainsFilePath, 'a') as domainsFile:
        for domain in tqdm(config['mainDomains'], desc="Resolving main domains"):
            ips = get_ip_addresses(domain, config['dns'], config['dnsQuery'], ports[config['dnsQuery']], config['dnsTimeout'])
            if ips:
                domainsFile.write(f"{domain}\n")
            for ip in ips:
                ipsFile.write(f"{ip}/32\n")
        domainsFile.flush()
        ipsFile.flush()

# Генерация региональных доменов
def generate_voice_domains():
    with open(domainsFilePath, 'a') as domainsFile, open(ipsFilePath, 'a') as ipsFile:
        # Используем ThreadPoolExecutor для параллельного выполнения
        with ThreadPoolExecutor(max_workers=config['workersCount']) as executor:
            # Проходим по регионам
            for region in config['regions']:
                futures_to_domains = {}  # Словарь для сопоставления задачи и домена
                
                # Используем tqdm для отслеживания прогресса по каждому домену
                for i in tqdm(range(config['entriesPerRegion']), desc=f"Generating domains for {region}"):
                    domain = f"{region}{i}.{config['voiceBaseDomain']}"
                    future = executor.submit(get_ip_addresses, domain, config['dns'], config['dnsQuery'], ports[config['dnsQuery']], config['dnsTimeout'])
                    futures_to_domains[future] = domain  # Сохраняем домен для каждой задачи

                    # Проверяем завершение задач по мере их выполнения
                    if len(futures_to_domains) >= config['workersCount'] or i == config['entriesPerRegion'] - 1:
                        for future in as_completed(futures_to_domains):
                            domain = futures_to_domains[future]  # Получаем домен из словаря

                            try:
                                ips = future.result()  # Получаем IP-адреса из результата
                                if ips:
                                    # Записываем домен и IP в файл
                                    domainsFile.write(f"{domain}\n")
                                    for ip in ips:
                                        ipsFile.write(f"{ip}/32\n")
                            except Exception as e:
                                # Пропускаем ошибки
                                print(f"Ошибка при обработке {domain}: {e}")

                        # Очищаем словарь задач для следующего батча
                        futures_to_domains.clear()

                # Сохраняем файлы после завершения каждого региона
                domainsFile.flush()
                ipsFile.flush()

# Объединение IP-адресов в подсети
def generate_cidrs():
    with open(ipsFilePath) as f:
        ips = [ip.strip() for ip in f.readlines()]

    ip_objects = [ipaddress.ip_network(ip) for ip in ips]
    merged_cidrs = ipaddress.collapse_addresses(ip_objects)

    with open(cidrFilePath, 'w') as cidrFile:
        for cidr in tqdm(merged_cidrs, desc="Generating CIDRs"):
            cidrFile.write(f"{cidr}\n")

# Основной процесс
def main():
    start = time.time()
    process_main_domains()
    generate_voice_domains()
    generate_cidrs()
    print('Time spent: ', time.strftime('%H:%M:%S', time.gmtime(time.time() - start)))
if __name__ == "__main__":
    main()