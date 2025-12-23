import streamlit as st
import yfinance as yf
import pandas as pd

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="2030 Portfolio Simulator")

# --- IMPROVED DATA FETCHING ---
@st.cache_data(ttl=86400) # Only talks to Yahoo once every 24 hours
def get_safe_data(symbol_list):
    results = []
    # Using a browser-like "User-Agent" to prevent being blocked
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            # Use 'fast_info' for speed and to stay under the radar
            data = ticker.fast_info
            price = data['lastPrice']
            mc = data['marketCap'] / 1_000_000_000
            
            # Use 'longName' if possible, otherwise just the symbol
            name = s.split('-')[0]
            results.append({'Symbol': name, 'Current Price': price, 'Current MC (B)': mc})
        except Exception:
            # If it fails, try a secondary fallback method
            try:
                info = yf.Ticker(s).info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                mc = info.get('marketCap') / 1_000_000_000
                results.append({'Symbol': s.split('-')[0], 'Current Price': price, 'Current MC (B)': mc})
            except:
                continue # Skip if both fail
    return pd.DataFrame(results)

# --- APP LAYOUT ---
st.title("📈 2030 Price & Market Cap Simulator")

# Initialize list if first time
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD']

# Sidebar Search
st.sidebar.header("Add Assets")
search = st.sidebar.text_input("Ticker (e.g., MSFT or SOL-USD)").upper()
if st.sidebar.button("Add to List") and search:
    if search not in st.session_state.symbols:
        st.session_state.symbols.append(search)
        st.cache_data.clear() # Force refresh to get new asset
        st.rerun()

df = get_safe_data(st.session_state.symbols)

if df.empty:
    st.error("⚠️ Yahoo is still blocking the server IP. Please wait 10 mins or try a 'Force Refresh'.")
    if st.button("Force Refresh"):
        st.cache_data.clear()
        st.rerun()
else:
    # --- SLIDERS ---
    st.sidebar.header("2030 Market Cap Targets ($B)")
    targets = {}
    for _, row in df.iterrows():
        # Set slider max to 10x current MC or $15T
        max_v = max(int(row['Current MC (B)'] * 10), 15000)
        targets[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target", 
            1, max_v, int(row['Current MC (B)'] * 2)
        )

    # --- MATH ---
    def calculate(row):
        target_mc = targets[row['Symbol']]
        cagr = ((target_mc / row['Current MC (B)'])**(1/5) - 1) * 100
        target_p = row['Current Price'] * (target_mc / row['Current MC (B)'])
        return pd.Series([target_mc, target_p, cagr])

    df[['Target MC', 'Target Price', 'CAGR (%)']] = df.apply(calculate, axis=1)
    df = df.sort_values('CAGR (%)', ascending=False)
    df['Rank'] = range(1, len(df) + 1)

    # --- VISUALS ---
    tab1, tab2 = st.tabs(["📊 Comparison Table", "📈 CAGR Visual"])
    
    with tab1:
        st.dataframe(df[['Rank', 'Symbol', 'Current Price', 'Current MC (B)', 'Target MC', 'Target Price', 'CAGR (%)']].style.format({
            'Current Price': '${:,.2f}', 'Current MC (B)': '${:,.1f}B', 
            'Target MC': '${:,.0f}B', 'Target Price': '${:,.2f}', 'CAGR (%)': '{:.2f}%'
        }), use_container_width=True)

    with tab2:
        st.bar_chart(df, x="Symbol", y="CAGR (%)", color="#29b5e8")
