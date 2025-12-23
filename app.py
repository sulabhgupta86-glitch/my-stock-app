import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="2030 Portfolio Architect")

# --- 1. CSS: BALANCED SPACING & CENTERING ---
st.markdown("""
    <style>
    /* Add vertical breathing room between stock blocks */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 1.5rem; }
    
    /* Push the Weight label down so it doesn't overlap the Target input */
    .stNumberInput { margin-top: 10px; margin-bottom: 5px; }
    
    /* Center Table Data for professional look */
    [data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stDataFrame"] th { text-align: center !important; }
    
    /* Metrics Styling */
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 8px; border: 1px solid #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA FETCHING (STALE DATA FOCUS) ---
@st.cache_data(ttl=604800) # CACHED FOR 1 WEEK (Focus on long-term stats, not live)
def get_safe_data(symbol_list):
    results = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            # Try 3 different ways to get data before giving up
            try:
                # Method 1: Standard fast lookup
                d = ticker.fast_info
                price, mc = d['lastPrice'], d['marketCap'] / 1_000_000_000
            except:
                try:
                    # Method 2: History (Best for Crypto/BTC)
                    h = ticker.history(period="5d")
                    price = h['Close'].iloc[-1]
                    mc = ticker.info.get('marketCap', 0) / 1_000_000_000
                except:
                    # Method 3: Last Resort Static Info
                    inf = ticker.info
                    price = inf.get('previousClose') or inf.get('regularMarketPrice')
                    mc = inf.get('marketCap', 0) / 1_000_000_000
            
            if price and price > 0:
                name = s.replace('.T', '').split('-')[0]
                results.append({'Symbol': name, 'Raw': s, 'Price': price, 'MC_B': mc})
        except: continue
    return pd.DataFrame(results)

# --- 3. SESSION STATE ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'TSLA', 'BTC-USD', 'NVDA', '3350.T']

if 'targets' not in st.session_state: st.session_state.targets = {}
if 'weights' not in st.session_state: st.session_state.weights = {}

# --- 4. SIDEBAR: SCALED INPUTS ---
st.sidebar.header("🎯 2030 Strategy")
df_raw = get_safe_data(st.session_state.symbols)

if not df_raw.empty:
    for _, row in df_raw.iterrows():
        sym = row['Symbol']
        curr_mc = row['MC_B']
        
        # Initialize defaults
        if sym not in st.session_state.targets: st.session_state.targets[sym] = float(round(curr_mc * 5, 0))
        if sym not in st.session_state.weights: st.session_state.weights[sym] = 0.0

        st.sidebar.subheader(f"📊 {sym}")
        
        # Target MC: 10% Steps
        mc_step = max(1.0, round(curr_mc * 0.1, 0))
        st.session_state.targets[sym] = st.sidebar.number_input(
            f"{sym} Target MC ($B)", value=float(st.session_state.targets[sym]), 
            key=f"t_{sym}", step=float(mc_step)
        )
        
        # Weight: 1% Steps (Increased margin for clarity)
        st.session_state.weights[sym] = st.sidebar.number_input(
            f"{sym} Weight %", value=float(st.session_state.weights[sym]), 
            min_value=0.0, max_value=100.0, step=1.0, key=f"w_{sym}"
        )
        st.sidebar.markdown("---")

# Management
st.sidebar.header("⚙️ Manage List")
new_ticker = st.sidebar.text_input("Add Ticker").upper()
if st.sidebar.button("Add") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

with st.sidebar.expander("Remove Assets"):
    for sym in st.session_state.symbols:
        if st.button(f"Remove {sym}", key=f"del_{sym}"):
            st.session_state.symbols.remove(sym)
            st.rerun()

# --- 5. DISPLAY & CALCULATIONS ---
if not df_raw.empty:
    def calc(row):
        t_mc = st.session_state.targets.get(row['Symbol'], row['MC_B'] * 5)
        w = st.session_state.weights.get(row['Symbol'], 0) / 100
        cagr = ((t_mc / row['MC_B'])**(1/5) - 1) * 100 if row['MC_B'] > 0 else 0
        t_p = row['Price'] * (t_mc / row['MC_B']) if row['MC_B'] > 0 else 0
        return pd.Series([t_mc, t_p, cagr, w*100, cagr * w])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)', 'Weight %', 'W.CAGR']] = df_raw.apply(calc, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)
    
    st.title("🏆 2030 Portfolio Roadmap")
    m1, m2 = st.columns(2)
    m1.metric("Total Portfolio CAGR", f"{df_final['W.CAGR'].sum():.2f}%")
    m2.metric("Total Weight", f"{df_final['Weight %'].sum():.0f}%")

    st.dataframe(
        df_final[['Symbol', 'Price', 'MC_B', 'Weight %', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "MC_B": st.column_config.NumberColumn("Current MC", format="$%.1fB"),
            "Weight %": st.column_config.NumberColumn("Weight", format="%.0f%%"),
            "Target MC": st.column_config.NumberColumn("Target MC", format="$%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price", format="$%.2f"),
            "CAGR (%)": st.column_config.NumberColumn("CAGR", format="%.2f%%"),
        }
    )
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", horizontal=True)
