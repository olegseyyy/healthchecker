import json
import time
import os
import requests
from datetime import datetime

TARGETS_FILE = "targets.json"
HISTORY_FILE = "history.jsonl"
REQUEST_TIMEOUT = 5

def load_targets():
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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
    print(f"Проверяю {len(targets)} сервис(ов)...\n")

    for target in targets:
        result = check_service(target)
        append_to_history(result)
        print_result(result)

    print(f"\nРезультаты записаны в {HISTORY_FILE}")

if __name__ == "__main__":
    main()