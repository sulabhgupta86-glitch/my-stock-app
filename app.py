import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="2030 Portfolio Architect")

# --- 1. CSS FOR CENTERING & STYLING ---
st.markdown("""
    <style>
    [data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stDataFrame"] th { text-align: center !important; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CACHING (24H) ---
@st.cache_data(ttl=86400)
def get_safe_data(symbol_list):
    results = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            d = ticker.fast_info
            results.append({
                'Symbol': s.split('-')[0], 
                'Raw': s, 
                'Price': d['lastPrice'], 
                'MC_B': d['marketCap'] / 1_000_000_000
            })
        except: continue
    return pd.DataFrame(results)

# --- 3. SESSION STATE ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD']

if 'targets' not in st.session_state:
    st.session_state.targets = {}
if 'weights' not in st.session_state:
    st.session_state.weights = {}

# --- 4. SIDEBAR: SCALED INPUTS ---
st.sidebar.header("🎯 2030 Portfolio Inputs")
df_raw = get_safe_data(st.session_state.symbols)

if not df_raw.empty:
    for _, row in df_raw.iterrows():
        sym = row['Symbol']
        curr_mc = row['MC_B']
        
        # Default initialization (5x current)
        if sym not in st.session_state.targets:
            st.session_state.targets[sym] = float(round(curr_mc * 5, 0))
        if sym not in st.session_state.weights:
            st.session_state.weights[sym] = 0.0

        st.sidebar.subheader(f"📊 {sym}")
        
        # Target MC Input: Increment/Decrement by 10% of CURRENT MC
        # This keeps the scaling consistent for both BTC and smaller stocks
        mc_step = max(1.0, round(curr_mc * 0.1, 0))
        st.session_state.targets[sym] = st.sidebar.number_input(
            f"Target MC ($B)", 
            value=float(st.session_state.targets[sym]), 
            key=f"input_{sym}", 
            step=float(mc_step)
        )
        
        # Weight Input: Increment/Decrement by 1%
        st.session_state.weights[sym] = st.sidebar.number_input(
            f"{sym} Weight %", 
            value=float(st.session_state.weights[sym]), 
            min_value=0.0, 
            max_value=100.0, 
            step=1.0, 
            key=f"w_{sym}"
        )
        st.sidebar.markdown("---")

st.sidebar.header("⚙️ List Management")
new_ticker = st.sidebar.text_input("Add Ticker").upper()
if st.sidebar.button("Add Ticker") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

with st.sidebar.expander("Cleanup Portfolio"):
    for sym in st.session_state.symbols:
        if st.button(f"Remove {sym}", key=f"del_{sym}"):
            st.session_state.symbols.remove(sym)
            if sym in st.session_state.targets: del st.session_state.targets[sym]
            st.rerun()

# --- 5. CALCULATIONS ---
if not df_raw.empty:
    def calc(row):
        sym = row['Symbol']
        t_mc = st.session_state.targets.get(sym, row['MC_B'] * 5)
        weight = st.session_state.weights.get(sym, 0) / 100
        
        cagr = ((t_mc / row['MC_B'])**(1/5) - 1) * 100
        t_p = row['Price'] * (t_mc / row['MC_B'])
        weighted_cagr = cagr * weight
        return pd.Series([t_mc, t_p, cagr, weight*100, weighted_cagr])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)', 'Weight %', 'W.CAGR']] = df_raw.apply(calc, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)
    
    total_portfolio_cagr = df_final['W.CAGR'].sum()
    total_weight = df_final['Weight %'].sum()

    # --- 6. MAIN DISPLAY ---
    st.title("🏆 Portfolio Strategy Dashboard")
    
    # Key Metrics
    m1, m2 = st.columns(2)
    m1.metric("Total Portfolio CAGR", f"{total_portfolio_cagr:.2f}%")
    m2.metric("Total Allocation", f"{total_weight:.1f}%", delta=f"{100-total_weight:.1f}% Left", delta_color="normal" if total_weight <= 100 else "inverse")

    st.markdown("### 📋 Projections Leaderboard")
    st.dataframe(
        df_final[['Symbol', 'Price', 'MC_B', 'Weight %', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "MC_B": st.column_config.NumberColumn("Current MC", format="$%.0fB"),
            "Weight %": st.column_config.NumberColumn("Weight", format="%.0f%%"),
            "Target MC": st.column_config.NumberColumn("Target MC", format="$%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price", format="$%.2f"),
            "CAGR (%)": st.column_config.NumberColumn("CAGR", format="%.2f%%"),
        }
    )

    st.markdown("### 📊 Ranked Growth Potential")
    st.bar_chart(
        df_final, 
        x="Symbol", 
        y="CAGR (%)", 
        color="#29b5e8", 
        horizontal=True, 
        use_container_width=True
    )
