import json
import os
from datetime import datetime, timedelta

HISTORY_FILE = "history.jsonl"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
DAYS_WINDOW = 7


def load_history():
    """Читает history.jsonl и возвращает список записей."""
    if not os.path.exists(HISTORY_FILE):
        return []
    records = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def calculate_stats(records):
    cutoff = datetime.now() - timedelta(days=DAYS_WINDOW)
    stats = {}

    for rec in records:
        name = rec.get("service")
        if not name:
            continue

        if name not in stats:
            stats[name] = {
                "total": 0,
                "ok": 0,
                "last_status": None,
                "last_timestamp": None,
                "url": rec.get("url", ""),
            }

        stats[name]["url"] = rec.get("url", stats[name]["url"])

        ts = rec.get("timestamp")
        if ts and (stats[name]["last_timestamp"] is None or ts > stats[name]["last_timestamp"]):
            stats[name]["last_timestamp"] = ts
            stats[name]["last_status"] = rec.get("status")

        try:
            rec_time = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue

        if rec_time >= cutoff:
            stats[name]["total"] += 1
            if rec.get("status") == "OK":
                stats[name]["ok"] += 1

    for name, s in stats.items():
        if s["total"] > 0:
            s["uptime"] = round(s["ok"] / s["total"] * 100, 2)
        else:
            s["uptime"] = 0.0

    return stats


def render_html(stats):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = ""
    for name, s in sorted(stats.items()):
        if s["last_status"] == "OK":
            badge = '<span class="badge ok">● Онлайн</span>'
        elif s["last_status"] == "FAIL":
            badge = '<span class="badge fail">● Офлайн</span>'
        else:
            badge = '<span class="badge unknown">● Неизвестно</span>'

        uptime = s["uptime"]
        if uptime >= 99:
            uptime_class = "uptime-good"
        elif uptime >= 95:
            uptime_class = "uptime-warn"
        else:
            uptime_class = "uptime-bad"

        rows += f"""
        <tr>
            <td><a href="{s['url']}" target="_blank">{name}</a></td>
            <td>{badge}</td>
            <td class="{uptime_class}">{uptime}%</td>
            <td>{s['last_timestamp'] or '—'}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Статус сервисов</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f7fa;
            color: #1f2937;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        h1 {{ margin-top: 0; }}
        .subtitle {{ color: #6b7280; margin-bottom: 30px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{ background: #f9fafb; font-weight: 600; }}
        .badge {{ padding: 4px 10px; border-radius: 20px; font-size: 14px; }}
        .badge.ok {{ background: #d1fae5; color: #065f46; }}
        .badge.fail {{ background: #fee2e2; color: #991b1b; }}
        .badge.unknown {{ background: #e5e7eb; color: #374151; }}
        .uptime-good {{ color: #059669; font-weight: 600; }}
        .uptime-warn {{ color: #d97706; font-weight: 600; }}
        .uptime-bad {{ color: #dc2626; font-weight: 600; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ color: #9ca3af; font-size: 13px; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Статус сервисов</h1>
        <p class="subtitle">Uptime за последние {DAYS_WINDOW} дней</p>
        <table>
            <thead>
                <tr>
                    <th>Сервис</th>
                    <th>Статус</th>
                    <th>Uptime</th>
                    <th>Последняя проверка</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <p class="footer">Страница сгенерирована {generated_at}</p>
    </div>
</body>
</html>
"""
    return html


def main():
    records = load_history()
    stats = calculate_stats(records)
    html = render_html(stats)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Страница сгенерирована: {OUTPUT_FILE}")
    print(f"Сервисов на странице: {len(stats)}")


if __name__ == "__main__":
    main()