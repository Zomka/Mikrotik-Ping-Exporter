# -*- coding: utf-8 -*-
import time
import yaml
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from prometheus_client import Gauge, start_http_server

from mikrotik_client import MikrotikRouterClient


file_handler = logging.FileHandler("mikrotik_exporter.log", encoding="utf-8")
console_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[file_handler, console_handler]
)


CONFIG_FILE = "config.yaml"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

USERNAME = config.get("USERNAME", "admin")
PASSWORD = config.get("PASSWORD", "")
API_PORT = config.get("API_PORT", 8728)
LISTEN_PORT = config.get("LISTEN_PORT", 8000)
ping_addresses_str = config.get("PING_ADDRESSES", "")
PING_ADDRESSES = [addr.strip() for addr in ping_addresses_str.split(",") if addr.strip()]

router_clients = {}
for name, ip in config.get("routers", {}).items():
    client = MikrotikRouterClient(name, ip, USERNAME, PASSWORD, port=API_PORT)
    router_clients[name] = client
    if not client.connect():
        logging.warning(f"Маршрутизатор {name} ({ip}) недоступен при запуске")

ping_rtt_avg_gauge = Gauge("mikrotik_ping_rtt_avg", "Средний RTT пинга в мс", ["routerboard_name", "target"])
ping_loss_gauge    = Gauge("mikrotik_ping_packet_loss", "Процент потерь пинга", ["routerboard_name", "target"])
ping_status_gauge  = Gauge("mikrotik_ping_status", "Статус reachability пинга (1/0)", ["routerboard_name", "target"])
router_up_gauge    = Gauge("mikrotik_router_up", "Состояние доступности роутера (API up/down)", ["routerboard_name"])

start_http_server(LISTEN_PORT)
logging.info(f"HTTP-сервер метрик запущен на порту {LISTEN_PORT}")


def update_router_metrics(name, client):

    result = client.ping_targets(PING_ADDRESSES)
    if result is None:
        router_up_gauge.labels(routerboard_name=name).set(0)
        logging.error(f"Маршрутизатор {name}: API недоступен — помечаем down")
        return

    router_up_gauge.labels(routerboard_name=name).set(1)
    for addr, stats in result.items():
        ping_rtt_avg_gauge.labels(routerboard_name=name, target=addr).set(stats['avg'])
        ping_loss_gauge   .labels(routerboard_name=name, target=addr).set(stats['loss'])
        ping_status_gauge .labels(routerboard_name=name, target=addr).set(stats['status'])


# Интервалы работы
collect_interval = 20           # секунд между циклами опроса
config_reload_interval = 60     # секунд между проверками конфига
last_config_reload = time.time()

logging.info(f"Начат мониторинг {len(router_clients)} роутеров: {', '.join(router_clients.keys())}")
if PING_ADDRESSES:
    logging.info(f"Адреса для пинга: {', '.join(PING_ADDRESSES)}")
else:
    logging.warning("Список адресов PING_ADDRESSES пуст – нечего пинговать.")

while True:
    cycle_start = time.time()

    with ThreadPoolExecutor(max_workers=min(32, len(router_clients) or 1)) as executor:
        futures = {executor.submit(update_router_metrics, name, client): name for name, client in router_clients.items()}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                router = futures[future]
                logging.error(f"Ошибка в потоке опроса роутера {router}: {e}")

    now = time.time()
    if now - last_config_reload >= config_reload_interval:
        last_config_reload = now
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                new_config = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Ошибка при чтении конфигурации: {e}")
            new_config = None

        if new_config:
            new_ping_str = new_config.get("PING_ADDRESSES", "")
            new_ping = [a.strip() for a in new_ping_str.split(",") if a.strip()]
            if set(new_ping) != set(PING_ADDRESSES):
                PING_ADDRESSES = new_ping
                logging.info(f"Обновлен список адресов для пинга: {', '.join(PING_ADDRESSES)}")

            new_routers = new_config.get("routers", {})
            for name, ip in new_routers.items():
                if name not in router_clients:
                    client = MikrotikRouterClient(name, ip, USERNAME, PASSWORD, port=API_PORT)
                    router_clients[name] = client
                    if client.connect():
                        logging.info(f"Добавлен новый роутер {name} ({ip}), успешно подключен.")
                    else:
                        logging.warning(f"Добавлен новый роутер {name} ({ip}), но пока недоступен.")
            for name in list(router_clients.keys()):
                if name not in new_routers:
                    client = router_clients.pop(name)
                    try:
                        client.api_pool.disconnect()
                    except Exception:
                        pass
                    logging.info(f"Роутер {name} удален из конфигурации")
                    router_up_gauge.labels(routerboard_name=name).set(0)
                    for addr in PING_ADDRESSES:
                        ping_rtt_avg_gauge.labels(routerboard_name=name, target=addr).set(0.0)
                        ping_loss_gauge   .labels(routerboard_name=name, target=addr).set(100.0)
                        ping_status_gauge .labels(routerboard_name=name, target=addr).set(0)

            new_user = new_config.get("USERNAME", USERNAME)
            new_pass = new_config.get("PASSWORD", PASSWORD)
            if new_user != USERNAME or new_pass != PASSWORD:
                USERNAME = new_user
                PASSWORD = new_pass
                logging.info("Изменены учетные данные, переподключаем роутеры")
                for name, client in router_clients.items():
                    client.username = USERNAME
                    client.password = PASSWORD
                    client.connect()

    elapsed = time.time() - cycle_start
    if elapsed < collect_interval:
        time.sleep(collect_interval - elapsed)
