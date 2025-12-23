import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="2030 Global Strategy")

# --- 1. CSS: COMPACT SIDEBAR & CENTERED TABLE ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.1rem; }
    [data-testid="stSidebar"] .stNumberInput { margin-bottom: -15px; }
    [data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stDataFrame"] th { text-align: center !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 8px; border: 1px solid #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FX CONVERSION LOGIC ---
@st.cache_data(ttl=3600)
def get_fx_rate(from_currency):
    if from_currency == "USD": return 1.0
    try:
        rate = yf.Ticker(f"{from_currency}USD=X").fast_info['lastPrice']
        return rate
    except: return 1.0

# --- 3. ROBUST DATA FETCHING ---
@st.cache_data(ttl=86400)
def get_safe_data(symbol_list, convert_to_usd):
    results = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            info = ticker.info
            
            # Basic info retrieval with fallbacks
            price = info.get('regularMarketPrice') or info.get('currentPrice') or ticker.fast_info['lastPrice']
            mc = info.get('marketCap') or ticker.fast_info['marketCap']
            currency = info.get('currency', 'USD')
            
            # Apply FX Conversion if toggled
            fx_rate = get_fx_rate(currency) if convert_to_usd else 1.0
            display_price = price * fx_rate
            display_mc = (mc / 1_000_000_000) * fx_rate
            
            name = s.replace('.T', '').split('-')[0]
            results.append({'Symbol': name, 'Raw': s, 'Price': display_price, 'MC_B': display_mc, 'Currency': currency if not convert_to_usd else "USD"})
        except: continue
    return pd.DataFrame(results)

# --- 4. SESSION STATE ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'BTC-USD', '3350.T', 'NVDA', 'ETH-USD']
if 'targets' not in st.session_state: st.session_state.targets = {}
if 'weights' not in st.session_state: st.session_state.weights = {}

# --- 5. SIDEBAR ---
st.sidebar.title("🌍 Global Controls")
usd_toggle = st.sidebar.toggle("Convert all to USD", value=True)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Targets")
df_raw = get_safe_data(st.session_state.symbols, usd_toggle)

if not df_raw.empty:
    for _, row in df_raw.iterrows():
        sym = row['Symbol']
        curr_mc = row['MC_B']
        if sym not in st.session_state.targets: st.session_state.targets[sym] = float(round(curr_mc * 5, 0))
        if sym not in st.session_state.weights: st.session_state.weights[sym] = 0.0

        with st.sidebar.container():
            st.write(f"**{sym}** ({row['Currency']} {row['Price']:,.2f})")
            c1, c2 = st.sidebar.columns(2)
            mc_step = max(1.0, round(curr_mc * 0.1, 0))
            st.session_state.targets[sym] = c1.number_input("MC", value=float(st.session_state.targets[sym]), step=float(mc_step), key=f"t_{sym}", label_visibility="collapsed")
            st.session_state.weights[sym] = c2.number_input("W%", value=float(st.session_state.weights[sym]), step=1.0, key=f"w_{sym}", label_visibility="collapsed")

st.sidebar.markdown("---")
new_ticker = st.sidebar.text_input("➕ Add (e.g. 7203.T, SOL-USD)").upper()
if st.sidebar.button("Add") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

with st.sidebar.expander("🗑️ Remove"):
    for sym in st.session_state.symbols:
        if st.button(f"Remove {sym}", key=f"del_{sym}"):
            st.session_state.symbols.remove(sym)
            st.rerun()

# --- 6. DISPLAY ---
if not df_raw.empty:
    def calc(row):
        t_mc = st.session_state.targets.get(row['Symbol'], row['MC_B'] * 5)
        w = st.session_state.weights.get(row['Symbol'], 0) / 100
        cagr = ((t_mc / row['MC_B'])**(1/5) - 1) * 100 if row['MC_B'] > 0 else 0
        return pd.Series([t_mc, row['Price'] * (t_mc / row['MC_B']), cagr, w*100, cagr * w])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)', 'Weight %', 'W.CAGR']] = df_raw.apply(calc, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)
    
    m1, m2 = st.columns(2)
    m1.metric("Portfolio CAGR", f"{df_final['W.CAGR'].sum():.2f}%")
    m2.metric("Allocated", f"{df_final['Weight %'].sum():.0f}%")

    st.dataframe(
        df_final[['Symbol', 'Price', 'MC_B', 'Weight %', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f" if usd_toggle else "%.2f"),
            "MC_B": st.column_config.NumberColumn("Current MC", format="$%.1fB" if usd_toggle else "%.1fB"),
            "Target MC": st.column_config.NumberColumn("Target MC", format="$%.0fB" if usd_toggle else "%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price", format="$%.2f" if usd_toggle else "%.2f"),
        }
    )
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", horizontal=True)
