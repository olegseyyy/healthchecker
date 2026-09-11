# Personal Health Checker

Мониторинг доступности личных сервисов с алертами в Telegram и публичной статус-страницей.

![Health Check](https://github.com/olegseyyy/healthchecker/actions/workflows/check.yml/badge.svg)

**Живой статус:** https://olegseyyy.github.io/healthchecker/

## Как это работает

GitHub Actions (каждые 15 минут)
  -> checker.py -> targets.json
  -> history.jsonl
  -> generate_status.py -> docs/index.html -> GitHub Pages
  -> Telegram (при смене состояния)

## Запуск локально

git clone https://github.com/olegseyyy/healthchecker.git
cd healthchecker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Создайте .env:
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

python checker.py
python generate_status.py

## Как добавить сервис

Откройте targets.json и добавьте объект:
{
  "name": "Мой блог",
  "url": "https://example.com",
  "expected_status": 200,
  "check_content": "<title>"
}

## Стек

Python, requests, GitHub Actions, GitHub Pages, Telegram Bot API