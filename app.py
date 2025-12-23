import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="2030 Portfolio Strategy")

# --- 1. DAILY DATA CACHING ---
@st.cache_data(ttl=86400)
def get_safe_data(symbol_list):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            data = ticker.fast_info
            price = data['lastPrice']
            mc = data['marketCap'] / 1_000_000_000
            name = s.split('-')[0]
            results.append({'Symbol': name, 'Raw': s, 'Current Price': price, 'Current MC (B)': mc})
        except:
            continue
    return pd.DataFrame(results)

# --- 2. SESSION STATE MANAGEMENT ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD']

# --- 3. SIDEBAR LAYOUT ---
st.sidebar.header("🛡️ Portfolio Controls")

# Add Section
new_ticker = st.sidebar.text_input("Add Ticker (e.g. MSFT or SOL-USD)").upper()
if st.sidebar.button("➕ Add to Portfolio") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

st.sidebar.markdown("---")

# Fetch Data
df_raw = get_safe_data(st.session_state.symbols)

if not df_raw.empty:
    # A. TARGET SLIDERS (Now Above Remove Buttons)
    st.sidebar.header("🎯 2030 Target Market Cap ($B)")
    targets = {}
    for _, row in df_raw.iterrows():
        curr_mc = int(row['Current MC (B)'])
        # MAX MC = 20x Current MC
        # DEFAULT = 5x Current MC for all assets
        targets[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target", 
            min_value=1, 
            max_value=curr_mc * 20, 
            value=curr_mc * 5, 
            step=10
        )

    st.sidebar.markdown("---")

    # B. REMOVE ASSETS (Now Below Sliders)
    with st.sidebar.expander("🗑️ Remove Assets from List"):
        for sym in st.session_state.symbols:
            if st.button(f"Remove {sym}", key=f"del_{sym}"):
                st.session_state.symbols.remove(sym)
                st.rerun()

    # --- 4. MATH & RANKING ---
    def calculate(row):
        target_mc = targets[row['Symbol']]
        cagr = ((target_mc / row['Current MC (B)'])**(1/5) - 1) * 100
        target_p = row['Current Price'] * (target_mc / row['Current MC (B)'])
        return pd.Series([target_mc, target_p, cagr])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)']] = df_raw.apply(calculate, axis=1)
    
    # Sort everything by CAGR for the visual ranking
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)

    # --- 5. MAIN PAGE LAYOUT ---
    st.title("🏆 2030 CAGR Leaderboard")

    # Table: Hidden index, centered numbers via config
    st.dataframe(
        df_final[['Symbol', 'Current Price', 'Current MC (B)', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol"),
            "Current Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Current MC (B)": st.column_config.NumberColumn("Current MC", format="$%.0fB"),
            "Target MC": st.column_config.NumberColumn("Target MC (2030)", format="$%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price (2030)", format="$%.2f"),
            "CAGR (%)": st.column_config.NumberColumn("Est. CAGR", format="%.2f%%"),
        }
    )

    # Visual below the table, strictly ordered by rank
    st.markdown("### 📊 Ranked Return Potential")
    # Using sort=False ensures the chart keeps the rank order we set in the dataframe
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", use_container_width=True)

else:
    st.warning("Please add a valid ticker to begin.")
