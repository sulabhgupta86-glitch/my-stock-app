import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("📈 2030 Price & Market Cap Simulator")

# 1. LIST YOUR SYMBOLS HERE
symbols = ['BTC-USD', 'TSLA', 'LMND', 'MSTR', 'IREN']

@st.cache_data(ttl=3600) # This saves data for 1 hour so we don't keep asking Yahoo
def get_data(symbol_list):
    data = []
    # We download everything at once (fastest & safest way to avoid blocks)
    tickers = yf.Tickers(' '.join(symbol_list))
    
    for s in symbol_list:
        try:
            ticker = tickers.tickers[s]
            # Fast_info is a more reliable way to get price and MC without triggers
            price = ticker.fast_info['lastPrice']
            mc = ticker.fast_info['marketCap'] / 1_000_000_000 
            data.append({'Symbol': s, 'Current Price': price, 'Current MC (B)': mc})
        except Exception:
            # If one stock fails, we just skip it so the app doesn't crash
            continue
    return pd.DataFrame(data)

df = get_data(symbols)

if df.empty:
    st.error("Yahoo Finance is currently blocking requests. Please wait 5 minutes and refresh.")
else:
    st.sidebar.header("Set 2030 Market Cap Targets ($ Billions)")
    target_values = {}

    # 2. CREATE SLIDERS
    for index, row in df.iterrows():
        target_values[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target",
            min_value=1,
            max_value=int(row['Current MC (B)'] * 20), # Increased to 10x 
            value=int(row['Current MC (B)'] * 1.5)
        )

    # 3. CALCULATE CAGR AND NEW PRICE
    def calculate_metrics(row):
        target_mc = target_values[row['Symbol']]
        current_mc = row['Current MC (B)']
        cagr = ((target_mc / current_mc)**(1/5) - 1) * 100
        target_price = row['Current Price'] * (target_mc / current_mc)
        return pd.Series([target_mc, target_price, cagr])

    df[['Target MC 2030', 'Target Price 2030', 'CAGR (%)']] = df.apply(calculate_metrics, axis=1)

    # 4. RANKING
    df['Rank'] = df['CAGR (%)'].rank(ascending=False).astype(int)
    df = df.sort_values('Rank')

    # 5. DISPLAY THE TABLE
    st.dataframe(
        df.style.format({
            'Current Price': '${:,.2f}',
            'Current MC (B)': '${:,.2f}B',
            'Target MC 2030': '${:,.0f}B',
            'Target Price 2030': '${:,.2f}',
            'CAGR (%)': '{:.2f}%'
        }),
        use_container_width=True
    )
