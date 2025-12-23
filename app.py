import streamlit as st
import yfinance as yf
import pandas as pd

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="2030 CAGR Simulator")
st.title("📈 2030 Investment Strategy Simulator")

# --- DATA LOADING (CACHED FOR 24 HOURS) ---
# We set ttl=86400 seconds (24 hours) so we don't annoy Yahoo Finance
@st.cache_data(ttl=86400)
def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # Try different data fields as fallback for crypto vs stocks
        info = ticker.info
        price = info.get('regularMarketPrice') or info.get('currentPrice') or ticker.fast_info['lastPrice']
        mc = info.get('marketCap') or ticker.fast_info['marketCap']
        
        if price and mc:
            return {'Symbol': symbol.split('-')[0], 'Price': price, 'MC_B': mc / 1_000_000_000}
    except:
        return None
    return None

# --- SESSION STATE (YOUR PRIVATE DATA BANK) ---
if 'my_symbols' not in st.session_state:
    st.session_state.my_symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD']

# --- SIDEBAR: ADD NEW SYMBOLS ---
st.sidebar.header("Add to Portfolio")
new_sym = st.sidebar.text_input("Enter Ticker (e.g. MSFT, SOL-USD)", "").upper()
if st.sidebar.button("Add Ticker") and new_sym:
    if new_sym not in st.session_state.my_symbols:
        st.session_state.my_symbols.append(new_sym)
        st.cache_data.clear() # Refresh data when you add a new one

# --- PROCESS DATA ---
final_data = []
for s in st.session_state.my_symbols:
    res = fetch_stock_data(s)
    if res:
        final_data.append(res)

df = pd.DataFrame(final_data)

if not df.empty:
    st.sidebar.header("Set 2030 Targets ($ Billions)")
    target_values = {}
    
    # Create sliders for each stock
    for index, row in df.iterrows():
        current_mc = int(row['MC_B'])
        target_values[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target MC",
            min_value=1,
            max_value=max(current_mc * 10, 10000),
            value=current_mc * 2
        )

    # --- CALCULATE ---
    def calc(row):
        target_mc = target_values[row['Symbol']]
        cagr = ((target_mc / row['MC_B'])**(1/5) - 1) * 100
        target_price = row['Price'] * (target_mc / row['MC_B'])
        return pd.Series([target_mc, target_price, cagr])

    df[['Target MC', 'Target Price', 'CAGR (%)']] = df.apply(calc, axis=1)
    df = df.sort_values('CAGR (%)', ascending=False)
    df['Rank'] = range(1, len(df) + 1)

    # --- VISUALS ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Results Table")
        st.dataframe(df[['Rank', 'Symbol', 'Price', 'MC_B', 'Target MC', 'Target Price', 'CAGR (%)']].style.format({
            'Price': '${:,.2f}', 'MC_B': '${:,.1f}B', 'Target MC': '${:,.0f}B', 
            'Target Price': '${:,.2f}', 'CAGR (%)': '{:.2f}%'
        }), use_container_width=True)

    with col2:
        st.subheader("CAGR Ranking")
        # Horizontal bar chart for quick visual ranking
        st.bar_chart(df, x="Symbol", y="CAGR (%)", color="#29b5e8")

else:
    st.error("Could not fetch data. Please check your symbols or try again later.")
    if st.button("Force Refresh"):
        st.cache_data.clear()
        st.rerun()
