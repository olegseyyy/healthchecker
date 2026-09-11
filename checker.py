import json
import time
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TARGETS_FILE = "targets.json"
HISTORY_FILE = "history.jsonl"
STATE_FILE = "state.json"
REQUEST_TIMEOUT = 5
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_targets():
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram не настроен, сообщение не отправлено:", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️  Ошибка Telegram: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Не удалось отправить в Telegram: {e}")

def format_failure_alert(result):
    msg = f"🔴 <b>Сервис недоступен</b>\n"
    msg += f"<b>{result['service']}</b>\n"
    msg += f"URL: {result['url']}\n"
    if result["http_code"]:
        msg += f"HTTP-код: {result['http_code']}\n"
    if result["duration_ms"] is not None:
        msg += f"Время ответа: {result['duration_ms']} мс\n"
    if result["error"]:
        msg += f"Причина: {result['error']}\n"
    msg += f"Время: {result['timestamp']}"
    return msg

def format_recovery_alert(result):
    msg = f"🟢 <b>Сервис восстановлен</b>\n"
    msg += f"<b>{result['service']}</b>\n"
    msg += f"URL: {result['url']}\n"
    if result["duration_ms"] is not None:
        msg += f"Время ответа: {result['duration_ms']} мс\n"
    msg += f"Время: {result['timestamp']}"
    return msg

def check_service(target):
    name = target["name"]
    url = target["url"]
    expected_status = target.get("expected_status", 200)
    check_content = target.get("check_content")

    result = {
        "service": name,
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "status": "UNKNOWN",
        "http_code": None,
        "duration_ms": None,
        "error": None,
    }

    start = time.time()
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        duration_ms = round((time.time() - start) * 1000, 2)
        result["http_code"] = response.status_code
        result["duration_ms"] = duration_ms

        if response.status_code != expected_status:
            result["status"] = "FAIL"
            result["error"] = f"Ожидался код {expected_status}, получен {response.status_code}"
        elif check_content and check_content not in response.text:
            result["status"] = "FAIL"
            result["error"] = f"Строка '{check_content}' не найдена в ответе"
        else:
            result["status"] = "OK"
    except requests.exceptions.Timeout:
        result["status"] = "FAIL"
        result["error"] = f"Таймаут {REQUEST_TIMEOUT} сек"
    except requests.exceptions.ConnectionError:
        result["status"] = "FAIL"
        result["error"] = "Не удалось подключиться"
    except requests.exceptions.RequestException as e:
        result["status"] = "FAIL"
        result["error"] = f"Ошибка запроса: {e}"

    return result

def append_to_history(result):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

def print_result(result):
    status = result["status"]
    icon = "✅" if status == "OK" else "❌" if status == "FAIL" else "❓"
    line = f"{icon} {result['service']:<20} {status:<6}"
    if result["http_code"]:
        line += f" code={result['http_code']}"
    if result["duration_ms"] is not None:
        line += f" time={result['duration_ms']}ms"
    if result["error"]:
        line += f" | {result['error']}"
    print(line)

def main():
    if not os.path.exists(TARGETS_FILE):
        print(f"Файл {TARGETS_FILE} не найден!")
        return

    targets = load_targets()
    previous_state = load_state()
    current_state = {}

    print(f"Проверяю {len(targets)} сервис(ов)...\n")

    for target in targets:
        result = check_service(target)
        append_to_history(result)
        print_result(result)

        name = result["service"]
        current_status = result["status"]
        previous_status = previous_state.get(name)

        if previous_status is None:
            print(f"   (первая проверка {name}, статус: {current_status})")
        elif previous_status == "OK" and current_status == "FAIL":
            send_telegram_message(format_failure_alert(result))
            print(f"   🔔 Алерт отправлен: {name} упал")
        elif previous_status == "FAIL" and current_status == "OK":
            send_telegram_message(format_recovery_alert(result))
            print(f"   🔔 Алерт отправлен: {name} восстановлен")

        current_state[name] = current_status

    save_state(current_state)
    print(f"\nРезультаты записаны в {HISTORY_FILE}")
    print(f"Состояние сохранено в {STATE_FILE}")

if __name__ == "__main__":
    main()