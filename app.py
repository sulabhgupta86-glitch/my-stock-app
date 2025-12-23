import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")
st.title("📈 2030 Price & Market Cap Simulator")

# 1. LIST YOUR SYMBOLS HERE
# You can change these symbols anytime by editing this list
symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN']

@st.cache_data
def get_data(symbols):
    data = []
    for s in symbols:
        ticker = yf.Ticker(s)
        info = ticker.info
        # Get Current Price and Market Cap (in Billions)
        price = info.get('currentPrice', 0)
        mc = info.get('marketCap', 0) / 1_000_000_000 
        data.append({'Symbol': s, 'Current Price': price, 'Current MC (B)': mc})
    return pd.DataFrame(data)

df = get_data(symbols)

st.sidebar.header("Set 2030 Market Cap Targets ($ Billions)")
target_values = {}

# 2. CREATE SLIDERS
for index, row in df.iterrows():
    # This creates a slider for each stock
    # It starts at the current MC and lets you go up to 5x that amount
    target_values[row['Symbol']] = st.sidebar.slider(
        f"{row['Symbol']} Target",
        min_value=1,
        max_value=int(row['Current MC (B)'] * 5),
        value=int(row['Current MC (B)'] * 1.5)
    )

# 3. CALCULATE CAGR AND NEW PRICE
def calculate_metrics(row):
    target_mc = target_values[row['Symbol']]
    current_mc = row['Current MC (B)']
    
    # CAGR Formula for 5 years (2025 to 2030)
    cagr = ((target_mc / current_mc)**(1/5) - 1) * 100
    
    # Target Price = Current Price * (Target MC / Current MC)
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
