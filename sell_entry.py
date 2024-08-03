from flask import Flask, request, render_template_string
import yfinance as yf
import pandas as pd
import webbrowser
import threading
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Initialize with default ticker symbols
current_ticker_symbols = ['TATAMOTORS.NS', 'MARUTI.NS', 'TCS.NS']
data_5min_all = {}
user_capital = 2000000  # Default value
user_risk = 7000        # Default value

# Function to calculate RSI
def calculate_rsi(data, window=23):
    delta = data['Close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(data, window=20, num_std_dev=2):
    data['SMA'] = data['Close'].rolling(window=window).mean()
    data['StdDev'] = data['Close'].rolling(window=window).std()
    data['UpperBand'] = data['SMA'] + (num_std_dev * data['StdDev'])
    data['LowerBand'] = data['SMA'] - (num_std_dev * data['StdDev'])
    return data

# Function to fetch 5-minute data and calculate RSI and Bollinger Bands
def fetch_5min_rsi_bollinger(ticker_symbol, period='1d'):
    ticker = yf.Ticker(ticker_symbol)
    data_5min = ticker.history(period=period, interval='5m')
    data_5min = calculate_bollinger_bands(data_5min)
    data_5min['RSI'] = calculate_rsi(data_5min)
    return data_5min

# Function to fetch daily, weekly, and monthly RSI
def fetch_rsi_levels(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    daily_data = ticker.history(period="1y", interval="1d")
    daily_rsi = calculate_rsi(daily_data).iloc[-1]
    weekly_data = ticker.history(period="5y", interval="1wk")
    weekly_rsi = calculate_rsi(weekly_data).iloc[-1]
    monthly_data = ticker.history(period="max", interval="1mo")
    monthly_rsi = calculate_rsi(monthly_data).iloc[-1]
    return daily_rsi, weekly_rsi, monthly_rsi

# Function to validate ticker symbol
def is_valid_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period='1d')
        return not data.empty
    except Exception as e:
        return False

# Function to generate HTML content
def generate_html_content(ticker_symbols, user_capital, user_risk, error_message=''):
    rsi_levels = {}
    global data_5min_all

    for ticker_symbol in ticker_symbols:
        data_5min = fetch_5min_rsi_bollinger(ticker_symbol)
        data_5min = data_5min.dropna(subset=['RSI', 'LowerBand'])
        data_5min_all[ticker_symbol] = data_5min

        daily_rsi, weekly_rsi, monthly_rsi = fetch_rsi_levels(ticker_symbol)
        rsi_levels[ticker_symbol] = {'daily': daily_rsi, 'weekly': weekly_rsi, 'monthly': monthly_rsi}

    html_content = f"""
    <html>
    <head>
        <title>5-Minute RSI Levels</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color:#FEFFFE;
            }}
            h1 {{
                color: #333;
                text-align: center;
            }}
            .main-table {{
                border-collapse: collapse;
                width: 80%;
                margin: 20px auto;
            }}
            .main-table, th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
                position: relative;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            .highlight-low {{
                background-color: lightgreen;
                position: relative;
            }}
            .highlight-mid {{
                background-color: yellow;
            }}
            .highlight-high {{
                background-color: red;
            }}
            .price-info {{
                font-size: smaller;
                color: #333;
                position: absolute;
                bottom: 20px;
                right: 100px;
                top: 2px;
            }}
            .stop-loss {{
                font-size: smaller;
                color: black;
                position: absolute;
                bottom: 2px;
                right: 2px;
            }}
            .qty {{
                font-size: smaller;
                color: white;
                position: absolute;
                top: 2px;
                right: 2px;
            }}
            .target {{
                font-size: smaller;
                color: #1233B3;
                position: absolute;
                bottom: 2px;
                right: 100px;
            }}
            .rsi-table {{
                margin-top: 20px;
                border-collapse: collapse;
                width: 80%;
                margin: 0 auto;
                table-layout: fixed;
            }}
            .rsi-table th, .rsi-table td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
                width: 25%;
                height: 50px;
                overflow: hidden;
            }}
            .rsi-table th {{
                background-color: #f2f2f2;
            }}
            .input-form {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .input-form input {{
                padding: 8px;
                margin-right: 8px;
                font-size: 16px;
            }}
            .right-inputs {{
                position: absolute;
                top: 20px;
                right: 20px;
            }}
            .gainer {{
                text-align: right;
                text-decoration: none;
                margin right:200px;
            }}
            .loser {{
                text-align: right;
                text-decoration: none;
                margin right:100px;
            }}
            .error-message {{
                color: red;
                text-align: center;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>SELL SIDE ENTRY</h1>
        <h2 class="gainer"><a href="https://www.nseindia.com" target="_blank">Nifty 50 loser</a></h2>
         <h2 class="loser"><a https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050">Nifty 500 loser</a></h2>
        <div class="input-form">
            <form action="/" method="post">
                <input type="text" name="ticker1" value="{ticker_symbols[0]}" placeholder="Enter first ticker symbol">
                <input type="text" name="ticker2" value="{ticker_symbols[1]}" placeholder="Enter second ticker symbol">
                <input type="text" name="ticker3" value="{ticker_symbols[2]}" placeholder="Enter third ticker symbol">
                <input type="text" name="capital" value="{user_capital}" placeholder="Enter Your Capital">
                <input type="text" name="risk" value="{user_risk}" placeholder="Enter Your Per Day Risk Capacity">
                <input type="submit" value="Submit">
            </form>
        </div>
        {f'<div class="error-message">{error_message}</div>' if error_message else ''}
        <table class="main-table">
            <thead>
                <tr>
                    <th>Ticker Symbol</th>
                    <th>Day RSI Level</th>
                    <th>Week RSI Level</th>
                    <th>Month RSI Level</th>
                </tr>
    """

    for ticker_symbol in ticker_symbols:
        daily_rsi = rsi_levels[ticker_symbol]['daily']
        weekly_rsi = rsi_levels[ticker_symbol]['weekly']
        monthly_rsi = rsi_levels[ticker_symbol]['monthly']
        html_content += f"""
                <tr>
                    <td>{ticker_symbol}</td>
                    <td class="{'highlight-low' if daily_rsi < 40 else 'highlight-mid' if 40 <= daily_rsi <= 60 else 'highlight-high'}">{daily_rsi:.2f}</td>
                    <td>{weekly_rsi:.2f}</td>
                    <td>{monthly_rsi:.2f}</td>
                </tr>
        """

    html_content += """
            </thead>
        </table>
        <table class="rsi-table">
            <thead>
                <tr>
                    <th>Time</th>
    """

    for ticker_symbol in ticker_symbols:
        html_content += f"<th>{ticker_symbol} RSI Level</th>"

    html_content += """
                </tr>
            </thead>
            <tbody>
    """

    if ticker_symbols:
        timestamps = data_5min_all[ticker_symbols[0]].index

        for timestamp in timestamps:
            html_content += f"<tr><td>{timestamp.strftime('%Y-%m-%d %H:%M')}</td>"
            for ticker_symbol in ticker_symbols:
                row_class = ''
                rsi = data_5min_all[ticker_symbol].loc[timestamp]['RSI']
                close = data_5min_all[ticker_symbol].loc[timestamp]['Close']
                lower_band = data_5min_all[ticker_symbol].loc[timestamp]['LowerBand']

                if rsi <= 20 and close < lower_band:
                    row_class = 'highlight-low'
                    step1 = user_capital / close
                    step2 = user_risk / step1
                    stop_loss = close - step2
                    qty = user_capital / close
                    value = close
                    percentage = 0.36
                    target = (value * percentage) / 100
                    target_price = target + close
                    html_content += (
                        f"<td class='{row_class}'>{rsi:.2f}<span class='price-info'>Price: {close:.2f}</span><span class='stop-loss'>SL: {stop_loss:.2f}</span><span class='qty'>Qty: {qty:.2f}</span>"
                        f"<span class='target'>Target: {target_price:.2f}</span></td>")
                elif rsi > 60:
                    step1 = user_capital / close
                    step2 = user_risk / step1
                    stop_loss = close + step2
                    qty = user_capital / close
                    value = close
                    percentage = 0.36
                    target = (value * percentage) / 100
                    target_price = close-target
                    row_class = 'highlight-high'
                    html_content +=(
                        f"<td class='{row_class}'>{rsi:.2f}<span class='price-info'>Price: {close:.2f}</span><span class='stop-loss'>SL: {stop_loss:.2f}</span><span class='qty'>Qty: {qty:.2f}</span>"
                        f"<span class='target'>Target: {target_price:.2f}</span></td>")
                else:
                    html_content += f"<td>{rsi:.2f}</td>"

            html_content += "</tr>"

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_content

# Function to open the web browser
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

# Route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    global current_ticker_symbols
    global user_capital
    global user_risk

    error_message = ''

    if request.method == 'POST':
        ticker1 = request.form['ticker1'].strip().upper()
        ticker2 = request.form['ticker2'].strip().upper()
        ticker3 = request.form['ticker3'].strip().upper()
        capital = request.form['capital'].strip()
        risk = request.form['risk'].strip()

        if not is_valid_ticker(ticker1):
            error_message += f'Invalid ticker symbol: {ticker1}. '
        if not is_valid_ticker(ticker2):
            error_message += f'Invalid ticker symbol: {ticker2}. '
        if not is_valid_ticker(ticker3):
            error_message += f'Invalid ticker symbol: {ticker3}. '

        if error_message == '':
            current_ticker_symbols = [ticker1, ticker2, ticker3]
            user_capital = float(capital) if capital else user_capital
            user_risk = float(risk) if risk else user_risk

    html_content = generate_html_content(current_ticker_symbols, user_capital, user_risk, error_message)
    return render_template_string(html_content)

# Function to periodically refresh the page
def refresh_page():
    with app.app_context():
        html_content = generate_html_content(current_ticker_symbols, user_capital, user_risk)
        with open('templates/index.html', 'w') as f:
            f.write(html_content)

# Scheduler to refresh the page every 5 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_page, trigger="interval", minutes=5)
scheduler.start()

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=False)
