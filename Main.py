import os
import time
import requests
import threading
from flask import Flask
from datetime import datetime, timezone

# -------------------------------
# FLASK WEB SERVER (REQUIRED FOR 24/7)
# -------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Upstox Free Bot Running!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

# Start web server on separate thread
threading.Thread(target=run_server).start()

# -------------------------------
# ENV VARIABLES FROM REPLIT SECRETS
# -------------------------------
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

INSTRUMENT_KEYS = os.getenv(
    "INSTRUMENT_KEYS",
    "NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank"
)

POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "1"))
LEVEL_STEP_POINTS = float(os.getenv("LEVEL_STEP_POINTS", "50"))

last_level_alert = {}


# -------------------------------
# TELEGRAM FUNCTION
# -------------------------------
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print("Telegram Error:", e)


# -------------------------------
# FETCH QUOTES FROM UPSTOX
# -------------------------------
def fetch_quotes(keys):
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}"}
    params = {"instrument_key": keys}

    r = requests.get(url, headers=headers, params=params, timeout=5)

    if r.status_code == 401:
        print("⚠️ ACCESS TOKEN EXPIRED. Update in Replit Secrets.")
        return {}

    return r.json().get("data", {})


# -------------------------------
# PRICE PROCESSING (ALERT ENGINE)
# -------------------------------
def process_tick(symbol, ltp, volume):
    global last_level_alert
    level = int(round(ltp / LEVEL_STEP_POINTS) * LEVEL_STEP_POINTS)
    prev = last_level_alert.get(symbol)

    if prev != level:
        last_level_alert[symbol] = level
        msg = (
            f"⚡ {symbol}\n"
            f"Price: {ltp}\n"
            f"Level touched: {level}\n"
            f"Volume: {volume}\n"
            f"Time: {datetime.now()}"
        )
        print(msg)
        send_telegram(msg)


# -------------------------------
# MAIN LOOP
# -------------------------------
def main():
    print("🚀 Upstox Free Bot Started…")
    send_telegram("🚀 Upstox Free Replit Bot Started!")

    keys = [k.strip() for k in INSTRUMENT_KEYS.split(",")]

    while True:
        data = fetch_quotes(",".join(keys))

        for k in keys:
            d = data.get(k)
            if not d:
                continue

            ltp = d.get("last_price") or d.get("ltp")
            depth = d.get("depth", {})
            buy_qty = sum((x.get("quantity", 0) for x in depth.get("buy", [])))

            if ltp:
                process_tick(k, float(ltp), float(buy_qty))

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
