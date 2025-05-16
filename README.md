# Mikrotik Ping Exporter

**Экспортер метрик ping с MikroTik API**

---

## Описание

Этот проект собирает статистику ping (RTT, packet loss, status) с одного или нескольких MikroTik-роутеров через официальный API RouterOS и экспортирует её в Prometheus.

**Ключевые возможности:**

* Параллельный опрос большого числа роутеров
* Автоматическая перезагрузка конфигурации `config.yaml` без перезапуска
* Экспорт метрик:

  * `mikrotik_ping_rtt_avg{routerboard_name, target}` - средний RTT (мс)
  * `mikrotik_ping_packet_loss{routerboard_name, target}` - потеря пакетов (%)
  * `mikrotik_ping_status{routerboard_name, target}` - статус пинга (1/0)
  * `mikrotik_router_up{routerboard_name}` - доступность API (1/0)

---

## Требования

* **Python** 3.7 или выше

---

## Настройка MikroTik RouterOS

Выполните на каждом роутере:

```bash
/ip service enable api
/ip service set api port=8728 address=0.0.0.0/0 disabled=no
/user group add name=api_user_group policy=api,read,test,sensitive
/user add name=api_user group=api_user_group password=YOUR_API_PASSWORD
```

---

## Установка и запуск

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/Zomka/Mikrotik-Ping-Exporter.git
   cd Mikrotik-Ping-Exporter
   ```
2. Установите зависимости:

   ```bash
   pip install routeros_api prometheus_client pyyaml
   ```
3. Настройте `config.yaml` (пример ниже).
4. Запустите экспортёр:

   ```bash
   python mikrotik_exporter.py
   ```

Метрики будут доступны по адресу `http://<HOST>:<LISTEN_PORT>` (по умолчанию `59191`).

---

## Формат файла `config.yaml`

```yaml
USERNAME: api_user               # Имя пользователя MikroTik
PASSWORD: YOUR_API_PASSWORD      # Пароль
API_PORT: 8728                   # Порт API (по умолчанию 8728)
LISTEN_PORT: 59191               # Порт для HTTP-сервера метрик
PING_ADDRESSES: '1.1.1.1, 8.8.8.8, ya.ru'

routers:
  ExampleName1: 192.168.1.1
  ExampleName2: 192.168.50.1
  # ... другие роутеры ...
```

* **PING\_ADDRESSES** - список IP или доменов для пинга через запятую.
* **routers** - ключи YAML: имена роутеров (`routerboard_name`), значения: их IP.
## Пример отображения метрик в Grafana
![1](https://github.com/user-attachments/assets/c940d67a-cdbe-4d9b-94cf-89b70a89cb4e)
![2](https://github.com/user-attachments/assets/d9304152-993a-4124-8b70-b8167aa55980)
![3](https://github.com/user-attachments/assets/eb6c2999-5c16-49d1-9236-12b9e9b581e8)
---

# Mikrotik Ping Exporter (English)

**MikroTik API Ping Metrics Exporter**

---

## Description

This project collects ping statistics (RTT, packet loss, status) from one or multiple MikroTik routers using the official RouterOS API and exports them to Prometheus.

**Key Features:**

* Parallel polling of a large number of routers
* Automatic reload of `config.yaml` without restart
* Exports the following metrics:

  * `mikrotik_ping_rtt_avg{routerboard_name, target}` - average RTT in milliseconds
  * `mikrotik_ping_packet_loss{routerboard_name, target}` - packet loss percentage
  * `mikrotik_ping_status{routerboard_name, target}` - ping reachability status (1 = success, 0 = failure)
  * `mikrotik_router_up{routerboard_name}` - API availability status (1 = up, 0 = down)

---

## Requirements

* **Python** 3.7 or higher

Install required packages:

```bash
pip install routeros_api prometheus_client pyyaml
```

---

## MikroTik RouterOS Setup

Execute on each router:

```bash
/ip service enable api
/ip service set api port=8728 address=0.0.0.0/0 disabled=no
/user group add name=api_user_group policy=api,read,test,sensitive
/user add name=api_user group=api_user_group password=YOUR_API_PASSWORD
```

---

## Installation and Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/Zomka/Mikrotik-Ping-Exporter.git
   cd Mikrotik-Ping-Exporter
   ```
2. Install dependencies:

   ```bash
   pip install routeros_api prometheus_client pyyaml
   ```
3. Configure `config.yaml` (see example below).
4. Run the exporter:

   ```bash
   python mikrotik_exporter.py
   ```

Metrics will be available at `http://<HOST>:<LISTEN_PORT>` (default `59191`).

---

## `config.yaml` Format

```yaml
USERNAME: api_user          # MikroTik API username
PASSWORD: YOUR_API_PASSWORD # API password
API_PORT: 8728              # RouterOS API port (default 8728)
LISTEN_PORT: 59191          # HTTP server port for metrics
PING_ADDRESSES: '1.1.1.1, 8.8.8.8, ya.ru'

routers:
  ExampleName1: 192.168.1.1
  ExampleName2: 192.168.50.1
  # ... other routers ...
```

* **PING\_ADDRESSES** - comma-separated list of IPs or domains to ping.
* **routers** - YAML keys: router names (`routerboard_name`), values: their IP addresses.

---

## Prometheus Integration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mikrotik_ping'
    scrape_interval: 20s
    static_configs:
      - targets: ['exporter-host:59191']
```

## Example Grafana metrics
![1](https://github.com/user-attachments/assets/c940d67a-cdbe-4d9b-94cf-89b70a89cb4e)
![2](https://github.com/user-attachments/assets/d9304152-993a-4124-8b70-b8167aa55980)
![3](https://github.com/user-attachments/assets/eb6c2999-5c16-49d1-9236-12b9e9b581e8)
