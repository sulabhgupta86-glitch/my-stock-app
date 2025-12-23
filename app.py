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

# --- 2. SESSION STATE (Managing your list) ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD']

# --- 3. SIDEBAR: ADD / REMOVE ASSETS ---
st.sidebar.header("🛡️ Manage Portfolio")

# Add Section
new_ticker = st.sidebar.text_input("Add Ticker (e.g. MSFT or SOL-USD)").upper()
if st.sidebar.button("➕ Add to Portfolio") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

st.sidebar.markdown("---")

# Remove Section
st.sidebar.subheader("Remove Assets")
for sym in st.session_state.symbols:
    # Small buttons to delete specific symbols
    if st.sidebar.button(f"❌ Remove {sym}", key=f"del_{sym}"):
        st.session_state.symbols.remove(sym)
        st.rerun()

# --- 4. DATA PROCESSING ---
df_raw = get_safe_data(st.session_state.symbols)

if df_raw.empty:
    st.error("Waiting for data... try adding a ticker or clicking 'Force Refresh' in 5 minutes.")
else:
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 2030 Targets ($B)")
    targets = {}
    for _, row in df_raw.iterrows():
        # MAX MC = 20x Current MC
        curr_mc = int(row['Current MC (B)'])
        targets[row['Symbol']] = st.sidebar.slider(
            f"{row['Symbol']} Target", 
            1, curr_mc * 20, curr_mc * 2, step=10
        )

    # Calculation logic
    def calculate(row):
        target_mc = targets[row['Symbol']]
        cagr = ((target_mc / row['Current MC (B)'])**(1/5) - 1) * 100
        target_p = row['Current Price'] * (target_mc / row['Current MC (B)'])
        return pd.Series([target_mc, target_p, cagr])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)']] = df_raw.apply(calculate, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)

    # --- 5. MAIN PAGE LAYOUT ---
    st.title("🏆 2030 CAGR Leaderboard")

    # Table Formatting: Center Align, No Index, Styled Numbers
    # hide_index=True removes that first column of random numbers
    st.dataframe(
        df_final[['Symbol', 'Current Price', 'Current MC (B)', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", help="Asset Name"),
            "Current Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Current MC (B)": st.column_config.NumberColumn("Current MC", format="$%.0fB"),
            "Target MC": st.column_config.NumberColumn("Target MC (2030)", format="$%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price (2030)", format="$%.2f"),
            "CAGR (%)": st.column_config.NumberColumn("Est. CAGR", format="%.2f%%"),
        }
    )

    # Visual below the table
    st.markdown("### 📊 Return Potential Visualized")
    # Centers and sorts the chart by CAGR
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", use_container_width=True)
