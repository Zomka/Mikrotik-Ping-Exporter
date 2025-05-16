# -*- coding: utf-8 -*-
import logging
import time
from routeros_api import RouterOsApiPool
import re

class MikrotikRouterClient:
    def __init__(self, name: str, ip: str, username: str, password: str, port: int = 8728):
        self.name = name        # Имя роутера
        self.ip = ip            # IP-адрес роутера
        self.username = username
        self.password = password
        self.port = port
        self.api = None         # Объект API-подключения
        self.api_pool = None    # Пул соединений RouterOsApiPool
        self.connected = False  # Флаг состояния соединения

    def connect(self):
        if self.api_pool:
            try:
                self.api_pool.disconnect()
            except Exception:
                pass
        self.api_pool = None
        self.api = None
        self.connected = False

        try:
            self.api_pool = RouterOsApiPool(self.ip, username=self.username, password=self.password,
                                            port=self.port, plaintext_login=True)
            self.api = self.api_pool.get_api()
            self.connected = True
            logging.info(f"Успешно подключено API к роутеру {self.name} ({self.ip})")
            return True
        except Exception as e:
            logging.error(f"Не удалось подключиться к роутеру {self.name} ({self.ip}): {e}")
            return False

    def ping_targets(self, targets):
        results = {}
        if not self.connected:
            if not self.connect():
                return None

        for addr in targets:
            try:
                response = self.api.get_resource('/').call('ping', {
                    'address': addr,
                    'count': '3',
                    'interval': '1'
                })
                if not response:
                    # Если ответ пустой (маловероятно), отмечаем отсутствие данных
                    logging.warning(f"{self.name}: пустой ответ на ping {addr}")
                    results[addr] = {'avg': 0.0, 'loss': 100.0, 'status': 0}
                    continue

                stats = None
                for entry in response:
                    if 'avg-rtt' in entry or 'packet-loss' in entry:
                        stats = entry
                if stats is None:
                    stats = response[-1]

                sent = int(stats.get('sent', 0))
                received = int(stats.get('received', 0))
                loss_count = sent - received
                loss_pct = 100.0 * loss_count / sent if sent > 0 else 100.0

                avg_rtt_str = stats.get('avg-rtt') or stats.get('time') or ""
                avg_rtt_ms = self._parse_time(avg_rtt_str) if avg_rtt_str else 0.0

                status = 1 if received > 0 else 0

                if status:
                    logging.info(f"Роутер {self.name} ({self.ip}): ping {addr} avg={avg_rtt_ms:.1f} мс, потери={loss_pct:.1f}%")
                else:
                    logging.warning(f"Роутер {self.name} ({self.ip}): адрес {addr} не отвечает (потери 100%)")

                results[addr] = {'avg': avg_rtt_ms, 'loss': loss_pct, 'status': status}
            except Exception as e:
                logging.error(f"Ошибка при ping {addr} на роутере {self.name} ({self.ip}): {e}. Повторная попытка...")
                self.connected = False
                if self.connect():
                    try:
                        response = self.api.get_resource('/').call('ping', {
                            'address': addr,
                            'count': '3',
                            'interval': '1'
                        })
                        if not response:
                            results[addr] = {'avg': 0.0, 'loss': 100.0, 'status': 0}
                            continue
                        stats = None
                        for entry in response:
                            if 'avg-rtt' in entry or 'packet-loss' in entry:
                                stats = entry
                        if stats is None:
                            stats = response[-1]
                        sent = int(stats.get('sent', 0))
                        received = int(stats.get('received', 0))
                        loss_count = sent - received
                        loss_pct = 100.0 * loss_count / sent if sent > 0 else 100.0
                        avg_rtt_str = stats.get('avg-rtt') or stats.get('time') or ""
                        avg_rtt_ms = self._parse_time(avg_rtt_str) if avg_rtt_str else 0.0
                        status = 1 if received > 0 else 0
                        results[addr] = {'avg': avg_rtt_ms, 'loss': loss_pct, 'status': status}
                        if status:
                            logging.info(f"Роутер {self.name} ({self.ip}): ping {addr} avg={avg_rtt_ms:.1f} мс, потери={loss_pct:.1f}%")
                        else:
                            logging.warning(f"Роутер {self.name} ({self.ip}): адрес {addr} не отвечает (потери 100%)")
                    except Exception as e2:
                        logging.error(f"Повторный сбой ping {addr} на роутере {self.name}: {e2}")
                        results[addr] = {'avg': 0.0, 'loss': 100.0, 'status': 0}
                else:
                    results[addr] = {'avg': 0.0, 'loss': 100.0, 'status': 0}
        return results

    def _parse_time(self, time_str: str) -> float:
        total_ms = 0.0
        for value, unit in re.findall(r'([\d\.]+)(ms|us|s)', time_str):
            v = float(value)
            if unit == 's':
                total_ms += v * 1000.0
            elif unit == 'ms':
               total_ms += v
            elif unit == 'us':
             total_ms += v / 1000.0
        return total_ms

