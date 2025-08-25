import os
import time
import pandas as pd
import yfinance as yf
import ta
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# 🔑 Telegram настройки
TELEGRAM_TOKEN = "8410180235:AAFFHVfftt9qD5Gl7V32Wkvgod7I1wxDSNc"
CHAT_ID = "6737036704"

def send_telegram_message(message: str):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        except Exception as e:
            print("Telegram error:", e)


def calculate_indicators(data):
    # squeeze() премахва излишни размерности (от (n,1) → (n,))
    close = data["Close"].squeeze()
    high = data["High"].squeeze()
    low = data["Low"].squeeze()

    # Индикатори
    data["EMA5"] = ta.trend.EMAIndicator(close, 5).ema_indicator()
    data["EMA20"] = ta.trend.EMAIndicator(close, 20).ema_indicator()
    data["RSI"] = ta.momentum.RSIIndicator(close, 14).rsi()

    macd = ta.trend.MACD(close)
    data["MACD"] = macd.macd()
    data["MACD_SIGNAL"] = macd.macd_signal()

    adx = ta.trend.ADXIndicator(high, low, close, 14)
    data["ADX"] = adx.adx()

    return data


def generate_signal(data):
    latest = data.iloc[-1]

    # Сигнал по EMA пресичане + RSI + ADX
    if latest["EMA5"] > latest["EMA20"] and latest["RSI"] > 50 and latest["ADX"] > 25:
        return "BUY"
    elif latest["EMA5"] < latest["EMA20"] and latest["RSI"] < 50 and latest["ADX"] > 25:
        return "SELL"
    else:
        return "HOLD"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_signals")
def get_signals():
    # 📊 Основни Forex двойки
    forex_pairs = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X"
    ]
    period = "30d"
    interval = "1m"

    signals = []

    for symbol in forex_pairs:
        data = yf.download(tickers=symbol, period=period, interval=interval)
        if data.empty:
            continue

        data = calculate_indicators(data)
        signal = generate_signal(data)
        price = float(data["Close"].iloc[-1])

        signals.append({
            "symbol": symbol,
            "signal": signal,
            "price": price
        })

        # 📲 Изпращаме Prepare/Confirm сигнал в Telegram
        if signal in ["BUY", "SELL"]:
            send_telegram_message(f"⏳ Prepare: {signal} сигнал след 20 сек. на {symbol} ({price})")
            time.sleep(20)
            send_telegram_message(f"✅ Confirm: {signal} {symbol} ({price})")

    return jsonify(signals)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
