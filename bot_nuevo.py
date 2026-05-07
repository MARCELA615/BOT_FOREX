import yfinance as yf
import pandas as pd
import requests
import time
import numpy as np

# 🔐 TELEGRAM
TOKEN = "8666484593:AAGa0q2OOXp8T2LIsG3ACJ0otEgqOkpBpzI"
CHAT_ID = "6131052337"

pairs = [
    "EURUSD=X", "AUDUSD=X", "NZDUSD=X",
    "USDCAD=X", "USDCHF=X", "AUDJPY=X", "EURCHF=X"
]

last_signal = {}

# 📤 SEND TELEGRAM
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# 📊 DATA
def get_data(pair, tf):
    df = yf.download(pair, interval=tf, period="60d")
    if df is None or df.empty:
        return None
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df

# 📈 INDICATORS
def indicators(df):
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# 📅 1D DIRECTION
def trend_1d(df):
    last = df.iloc[-1]
    if last["EMA50"] > last["EMA200"]:
        return "BUY"
    elif last["EMA50"] < last["EMA200"]:
        return "SELL"
    return None

# 📊 SWING (FRACTAL SIMPLE)
def get_swing(df):
    swing_high = df["High"].rolling(10).max().iloc[-1]
    swing_low = df["Low"].rolling(10).min().iloc[-1]
    return swing_low, swing_high

# 📊 FIBONACCI
def fib_levels(low, high):
    diff = high - low
    return {
        "78": high - diff * 0.786,
        "88": high - diff * 0.886
    }

# 🧠 STRUCTURE PROXY
def structure_zone(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    bos = last["Close"] > prev["High"] or last["Close"] < prev["Low"]
    choch = (last["Close"] > prev["High"] and prev["Close"] < prev["Open"]) or \
            (last["Close"] < prev["Low"] and prev["Close"] > prev["Open"])

    return bos, choch

# 📊 RSI FILTER
def rsi_ok(rsi, side):
    if side == "BUY":
        return 45 <= rsi <= 65
    if side == "SELL":
        return 35 <= rsi <= 55
    return False

# 🎯 ENTRY TYPE
def order_type(side, price, fib_zone):
    if side == "BUY":
        return "BUY LIMIT" if price <= fib_zone else "BUY STOP"
    else:
        return "SELL LIMIT" if price >= fib_zone else "SELL STOP"

# 🔍 ANALYSIS
def analyze(pair):

    df_1d = indicators(get_data(pair, "1d"))
    df_h1 = indicators(get_data(pair, "60m"))

    if df_1d is None or df_h1 is None:
        return

    side = trend_1d(df_1d)
    if not side:
        return

    swing_low, swing_high = get_swing(df_h1)
    fib = fib_levels(swing_low, swing_high)

    price = df_h1.iloc[-1]["Close"]
    rsi = df_h1.iloc[-1]["RSI"]

    bos, choch = structure_zone(df_h1)

    # 🔥 ZONA DE CONFLUENCIA
    zone_78 = abs(price - fib["78"]) / price < 0.002
    zone_88 = abs(price - fib["88"]) / price < 0.002

    if not (zone_78 or zone_88):
        return

    if not rsi_ok(rsi, side):
        return

    if not (bos or choch):
        return

    # 🔒 NO REPETIR
    if pair in last_signal and last_signal[pair] == side:
        return

    last_signal[pair] = side

    entry = price

    if side == "BUY":
        sl = swing_low
        tp = entry + (entry - sl) * 2
    else:
        sl = swing_high
        tp = entry - (sl - entry) * 2

    order = order_type(side, entry, fib["78"])

    send(f"""📊 {pair.replace("=X","")} {side}
TF: 1D + H1
Entrada: {round(entry,5)}
Zona Fib: 78% / 88%
SL: {round(sl,5)}
TP: {round(tp,5)}
RR: 1:2
RSI: {round(rsi,2)}
Orden: {order}
Confluencias: BOS/CHOCH + FIB + STRUCTURE""")

    print(pair, side)

# 🚀 LOOP
print("🔥 BOT SMART MONEY FIB PRO INICIADO 🔥")

while True:
    for p in pairs:
        try:
            analyze(p)
        except Exception as e:
            print("Error:", p, e)

    time.sleep(300)