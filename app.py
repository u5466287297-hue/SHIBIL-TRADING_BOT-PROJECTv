import os
import requests
import yfinance as yf
import pandas as pd
import ta
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# 🔑 Telegram настройки (ПОПЪЛНИ СВОИТЕ)
TELEGRAM_TOKEN = "8410180235:AAFFHVfftt9qD5Gl7V32Wkvgod7I1wxDSNc"
CHAT_ID = "6737036704"

def send_telegram(message):
    if TELEGRAM_TOKEN.startswith("ТУК"): return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

# История на сигналите
signals_history = []

def fetch_data(symbol="BTC-USD", interval="1m", period="1d"):
    data = yf.download(tickers=symbol, period=period, interval=interval)
    data.dropna(inplace=True)
    return data

def calculate_indicators(data):
    data["EMA5"] = ta.trend.EMAIndicator(data["Close"], 5).ema_indicator()
    data["EMA20"] = ta.trend.EMAIndicator(data["Close"], 20).ema_indicator()
    data["RSI"] = ta.momentum.RSIIndicator(data["Close"], 14).rsi()
    data["MACD"] = ta.trend.MACD(data["Close"]).macd()
    data["MACD_SIGNAL"] = ta.trend.MACD(data["Close"]).macd_signal()
    data["ADX"] = ta.trend.ADXIndicator(data["High"], data["Low"], data["Close"], 14).adx()
    return data

def check_signals(data):
    last = data.iloc[-1]
    prev = data.iloc[-2]
    signal = None
    prepare = None

    if last["EMA5"] > last["EMA20"] and last["RSI"] > 50 and last["MACD"] > last["MACD_SIGNAL"] and last["ADX"] > 25:
        signal = "BUY"
    elif last["EMA5"] < last["EMA20"] and last["RSI"] < 50 and last["MACD"] < last["MACD_SIGNAL"] and last["ADX"] > 25:
        signal = "SELL"
    else:
        # Prepare сигнал ~20s (условия почти изпълнени)
        if prev["EMA5"] < prev["EMA20"] and last["EMA5"] > last["EMA20"]:
            prepare = "BUY"
        elif prev["EMA5"] > prev["EMA20"] and last["EMA5"] < last["EMA20"]:
            prepare = "SELL"

    return signal, prepare

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_signals")
def get_signals():
    data = fetch_data()
    data = calculate_indicators(data)
    signal, prepare = check_signals(data)

    now = datetime.now().strftime("%H:%M:%S")
    result = {"time": now, "signal": signal, "prepare": prepare}

    if signal:
        signals_history.append({"time": now, "signal": signal})
        send_telegram(f"✅ {signal} Signal at {now}")
    elif prepare:
        send_telegram(f"⚠️ Prepare {prepare} in ~20s at {now}")

    return jsonify(result)

@app.route("/get_history")
def get_history():
    return jsonify(signals_history)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
