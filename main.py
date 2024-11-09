import dns.asyncquery
import dns.message
import json
from random import randrange
import ipaddress
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import time
import asyncio
from tqdm import tqdm
from tqdm.asyncio import tqdm as tqdmAsync

configPath = "config.json"
ipsFilePath = "./dest/ips.txt"
domainsFilePath = "./dest/voice_domains.txt"
cidrFilePath = "./dest/cidr.txt"
config = {
    "dns": [
        "1.1.1.1",
        "8.8.8.8",
        "8.8.4.4",
        "9.9.9.9"
    ],
    "dnsStrategy": "random",
    "dnsQuery": "udp",
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
    "dnsTimeout": 0.2,
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
        "discordapp.io",
    ],
    "entriesPerRegion": 15000,
    "clearFiles": True,
    "workersCount": 4,
    "concurent": 50,
}
ports = {
    "tls": 853,
    "https": 443,
    "udp": 53,
}

try:
    with open(configPath, "r") as file:
        data = json.load(file)
        config.update(
            {
                "dns": data.get("dns", config["dns"]),
                "dnsStrategy": data.get("dnsStrategy", config["dnsStrategy"]),
                "dnsQuery": data.get("dnsQuery", config["dnsQuery"]),
                "dnsTimeout": data.get("dnsTimeout", config["dnsTimeout"]),
                "regions": data.get("regions", config["regions"]),
                "voiceBaseDomain": data.get(
                    "voiceBaseDomain", config["voiceBaseDomain"]
                ),
                "mainDomains": data.get("mainDomains", config["mainDomains"]),
                "entriesPerRegion": data.get(
                    "entriesPerRegion", config["entriesPerRegion"]
                ),
                "clearFiles": data.get("clearFiles", config["clearFiles"]),
                "workersCount": data.get("workersCount", config["workersCount"]),
                "concurent": data.get("concurent", config["concurent"]),
            }
        )
        ipsFilePath = data.get("ipsFile", ipsFilePath)
        domainsFilePath = data.get("domainsFile", domainsFilePath)
        cidrFilePath = data.get("cidrFile", cidrFilePath)
except FileNotFoundError:
    print(f"File {configPath} not found.")
except json.JSONDecodeError:
    print(f"Error decoding JSON in the file {configPath}.")

if config["clearFiles"]:
    open(ipsFilePath, "w").close()
    open(domainsFilePath, "w")
    open(cidrFilePath, "w").close()


# Фильтр ip адресов
def filterIps(ips: list[str]) -> list[str]:
    return [ip for ip in ips if not ip.startswith("127.") and ip != "0.0.0.0"]


# Функция для выполнения запроса DNS
async def fetch_dns(
    server: str, request: dns.query, dnsQuery: str, port: int, timeout: float
) -> list[str] | None:
    try:
        if dnsQuery == "tls":
            response = await dns.asyncquery.tls(
                request, server, port=port, timeout=timeout
            )
        elif dnsQuery == "https":
            response = await dns.asyncquery.https(
                request, server, port=port, timeout=timeout
            )
        else:
            response = await dns.asyncquery.udp(
                request, server, port=port, timeout=timeout
            )

        if response.answer:
            ips = [answer.address for answer in response.answer[0]]
            return filterIps(ips) if ips else []
        else:
            return []
    except Exception as e:
        return []


async def resolveDomain(
    semaphore: asyncio.Semaphore,
    domain: str,
    dnsServers: list[str],
    dnsStrategy: str,
    dnsQuery: str,
    port: int,
    timeout: float,
) -> tuple[str, list[str]]:
    async with semaphore:
        request = dns.message.make_query(domain, "A")
        tasks = [
            asyncio.create_task(fetch_dns(dns, request, dnsQuery, port, timeout))
            for dns in dnsServers
        ]
        if dnsStrategy == "faster":
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                ips = await task
                for pending_task in pending:
                    pending_task.cancel()
                return [domain, ips]
        elif dnsStrategy == "random":
            randIndex = randrange(len(tasks))
            ips = await tasks[randIndex]
            return [domain, ips]
        else:
            mergedIps = []
            for task in asyncio.as_completed(tasks):
                ips = await task
                mergedIps.extend(ips)
            return [domain, list(set(mergedIps))]


async def resolveDomainsList(
    domains: list[str],
    dnsServers: list[str],
    dnsStrategy: str,
    dnsQuery: str,
    port: int,
    timeout: float,
    concurent: int,
    desc: str,
    tqdmDelay: float = 0.1,
    tqdmMininterval: float = 0.1,
    tqdmColour: str = "white",
    tqdmLeave: str = False,
) -> dict[str, list[str]]:
    semaphore = asyncio.Semaphore(concurent)
    results: dict[str, list[str]] = {}
    tasks = [
        resolveDomain(
            semaphore, domain, dnsServers, dnsStrategy, dnsQuery, port, timeout
        )
        for domain in domains
    ]
    async with semaphore:
        tpls = await tqdmAsync.gather(
            *tasks,
            desc=desc,
            delay=tqdmDelay,
            mininterval=tqdmMininterval,
            colour=tqdmColour,
            leave=tqdmLeave,
        )
        for domain, ips in tpls:
            if ips:
                results[domain] = ips
        return results


# Асинхронное разрешение всех необходимых доменов
def processAllDomains():
    with open(domainsFilePath, "a") as domainsFile, open(ipsFilePath, "a") as ipsFile:
        with ThreadPoolExecutor(max_workers=config["workersCount"]) as executor:
            futures: list[Future] = []

            task = resolveDomainsList(
                config["mainDomains"],
                config["dns"],
                config["dnsStrategy"],
                config["dnsQuery"],
                ports[config["dnsQuery"]],
                config["dnsTimeout"],
                config["concurent"],
                "Resolving main domains",
                tqdmColour="#1ABC9C",
            )
            future = executor.submit(asyncio.run, task)
            futures.append(future)

            for region in config["regions"]:
                domains = [
                    f"{region}{num}.{config["voiceBaseDomain"]}"
                    for num in range(config["entriesPerRegion"])
                ]
                task = resolveDomainsList(
                    domains,
                    config["dns"],
                    config["dnsStrategy"],
                    config["dnsQuery"],
                    ports[config["dnsQuery"]],
                    config["dnsTimeout"],
                    config["concurent"],
                    f"Resolving domains for {region}",
                    0.25,
                    0.25,
                    "#1ABC9C",
                )
                future = executor.submit(
                    asyncio.run,
                    task,
                )
                futures.append(future)

            for future in tqdmAsync(
                as_completed(futures),
                total=len(futures),
                colour="#3498DB",
                desc="overall progress",
                leave=True,
                position=0,
            ):
                try:
                    result = future.result()
                    for domain in result:
                        ips = result[domain]
                        if ips:
                            domainsFile.write(f"{domain}\n")
                            for ip in ips:
                                ipsFile.write(f"{ip}/32\n")
                    domainsFile.flush()
                    ipsFile.flush()
                except Exception as e:
                    print(f"Ошибка при обработке: {e}")


# Объединение IP-адресов в подсети
def generate_cidrs():
    with open(ipsFilePath) as f:
        ips = [ip.strip() for ip in f.readlines()]
        ip_objects = [ipaddress.ip_network(ip) for ip in ips]
        merged_cidrs = ipaddress.collapse_addresses(ip_objects)
        with open(cidrFilePath, "w") as cidrFile:
            for cidr in tqdm(
                merged_cidrs, desc="Generating CIDRs", colour="#2ECC71", leave=True
            ):
                cidrFile.write(f"{cidr}\n")


# Основной процесс
def main():
    start = time.time()
    processAllDomains()
    time.sleep(0.5)
    generate_cidrs()
    time.sleep(0.5)
    print("Time spent: ", time.strftime("%H:%M:%S", time.gmtime(time.time() - start)))


if __name__ == "__main__":
    main()
