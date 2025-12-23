import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("📈 2030 Price & Market Cap Simulator")

# 1. UPDATED SYMBOLS (BTC-USD is the correct format)
symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD', 'MSFT']

@st.cache_data(ttl=3600)
def get_data(symbol_list):
    data = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            
            # Try to get price and MC using the most reliable method for each asset type
            # We check .info first for crypto, then fall back to .fast_info
            info = ticker.info
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            mc = info.get('marketCap')
            
            # If standard .info fails (common for crypto), try fast_info
            if price is None:
                price = ticker.fast_info['lastPrice']
            if mc is None:
                mc = ticker.fast_info['marketCap']

            if price and mc:
                mc_billions = mc / 1_000_000_000
                display_name = s.split('-')[0] # Changes BTC-USD to just BTC
                data.append({
                    'Symbol': display_name, 
                    'Current Price': price, 
                    'Current MC (B)': mc_billions
                })
        except Exception as e:
            st.warning(f"Could not load {s}: {e}")
            continue
    return pd.DataFrame(data)

df = get_data(symbols)

if df.empty:
    st.error("No data found. Yahoo Finance might be blocking the request. Try refreshing in 1 minute.")
else:
    st.sidebar.header("Set 2030 Market Cap Targets ($ Billions)")
    target_values = {}

    # 2. DYNAMIC SLIDERS
    for index, row in df.iterrows():
        # High-cap assets like BTC/Apple need big sliders
        # We set the max to 10x current MC or $15 Trillion, whichever is higher
        current_val = int(row['Current MC (B)'])
        max_slider = max(current_val * 10, 15000)
        
        target_values[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target MC (B)",
            min_value=1,
            max_value=max_slider,
            value=current_val * 2,
            step=10
        )

    # 3. MATH LOGIC
    def calculate_metrics(row):
        target_mc = target_values[row['Symbol']]
        current_mc = row['Current MC (B)']
        # CAGR for 5 years
        cagr = ((target_mc / current_mc)**(1/5) - 1) * 100
        target_price = row['Current Price'] * (target_mc / current_mc)
        return pd.Series([target_mc, target_price, cagr])

    df[['Target MC 2030', 'Target Price 2030', 'CAGR (%)']] = df.apply(calculate_metrics, axis=1)

    # 4. RANKING
    df['Rank'] = df['CAGR (%)'].rank(ascending=False).astype(int)
    df = df.sort_values('Rank')

    # 5. DISPLAY
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
