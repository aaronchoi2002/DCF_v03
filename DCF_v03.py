import json
import requests
import streamlit as st
from urllib.request import urlopen
import pandas as pd
from bs4 import BeautifulSoup

api_key = "e3e1ef68f4575bca8a430996a4e11ed1"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'}
stock = st.sidebar.text_input("輸入股票代碼", value="AAPL")

def get_stock_price(stock_code):
    url = f"https://financialmodelingprep.com/api/v3/profile/{stock_code.upper()}?apikey={api_key}"
    response = requests.get(url)
    stock_data = response.json()

    if not stock_data:
        raise ValueError("未找到數據")

    price = stock_data[0].get('price', 0)
    companyName = stock_data[0].get('companyName', "")
    industry = stock_data[0].get('industry', "")

    return price, companyName, industry



def get_ttm_free_cash_flow(stock_code):
    url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{stock_code.upper()}?period=quarter&limit=4&apikey={api_key}"
    response = requests.get(url)
    stock_data = response.json()

    if len(stock_data) < 4:
        raise ValueError("數據不足，無法計算 TTM 自由現金流")

    free_cash_flows = [quarter['freeCashFlow'] for quarter in stock_data[:4]]
    ttm_free_cash_flow = round(sum(free_cash_flows), 2)
    most_recent_date = stock_data[0]['date']
    most_recent_year = int(most_recent_date.split("-")[0])
    currency = stock_data[0]['reportedCurrency']

    return ttm_free_cash_flow, most_recent_year, currency

def get_ttm_revenue_shareoutstanding(stock_code):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{stock_code.upper()}?period=quarter&limit=4&apikey={api_key}"
    response = requests.get(url)
    stock_data = response.json()

    if len(stock_data) < 4:
        raise ValueError("數據不足，無法計算 TTM 營收")

    revenues = [quarter['revenue'] for quarter in stock_data[:4]]
    ttm_revenue = round(sum(revenues), 2)
    most_recent_date = stock_data[0]['date']
    most_recent_year = int(most_recent_date.split("-")[0])
    shares_outstanding = stock_data[0].get('weightedAverageShsOutDil', 0)

    return ttm_revenue, most_recent_year, shares_outstanding

def get_wacc_netdabt(stock_code):
    response = urlopen(f"https://financialmodelingprep.com/api/v4/advanced_discounted_cash_flow?symbol={stock_code.upper()}&apikey={api_key}")
    stock = response.read().decode("utf-8")
    stock = json.loads(stock)
    stock = pd.json_normalize(stock).T

    wacc = round(stock.loc["wacc"].iloc[0], 2) if type(stock.loc["wacc"].iloc[0]) == float else 0.0
    net_debt = stock.loc["netDebt"].iloc[0]
    return wacc, net_debt

def grown_rate(stock_code):
    response = requests.get(f"https://finance.yahoo.com/quote/{stock_code}/analysis", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    if len(soup.find_all(class_="Ta(end) Py(10px)")) < 16:
        grown = 0
    else:
        grown = soup.find_all(class_="Ta(end) Py(10px)")[16].text
        grown = float(grown.replace("%", "")) if grown != 'N/A' else 0
    return grown

def get_cash_equivalents_and_total_debt(stock_code):
    url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{stock_code.upper()}?period=quarter&limit=50&apikey={api_key}"
    response = requests.get(url)
    stock_data = response.json()

    if not stock_data:
        raise ValueError("未找到數據")

    cash_equivalents = stock_data[0].get('cashAndShortTermInvestments', 0)
    total_debt = stock_data[0].get('totalDebt', 0)

    return cash_equivalents, total_debt

# Highlight the first row
def highlight_first_row(s):
    return ['background-color: yellow' if s.name == df.index[0] else '' for _ in s]

wacc, net_debt = get_wacc_netdabt(stock)
s_growth = grown_rate(stock)

# Input fields
s_growth = st.sidebar.number_input("短期成長率 (1 - 5年) (%)", value=5.0)
l_growth = st.sidebar.number_input("長期成長率 (5 年以後) (%)", value=5.0)
f_growth = st.sidebar.number_input("永久成長率 (%)", value=2.5)
wacc = st.sidebar.number_input("加權平均資本成本 (WACC) (%)", value=wacc)
cash, debt = get_cash_equivalents_and_total_debt(stock)



ttm_fcf, latest_year, currency = get_ttm_free_cash_flow(stock)
ttm_revenue, latest_year, share_outstanding = get_ttm_revenue_shareoutstanding(stock)
price, companyName, industry = get_stock_price(stock)



fcf_yield = round((ttm_fcf / ttm_revenue) * 100, 2)


# Calculate future free cash flows
years = list(range(latest_year - 1, latest_year - 1 + 11))
fcf = [ttm_fcf]

# First 5 years with short-term growth rate
for i in range(1, 6):
    fcf.append(round(fcf[-1] * (1 + s_growth / 100),))

# Next years with long-term growth rate
for i in range(6, 11):
    fcf.append(round(fcf[-1] * (1 + l_growth / 100),))

# Calculate terminal value
terminal_value = (fcf[-1] * (1 + f_growth / 100)) / (wacc / 100 - f_growth / 100)

# Create a DataFrame to display the data
df = pd.DataFrame({'年份': years, '自由現金流': fcf})
df["自由現金流_PV"] = df['自由現金流'] / (1 + wacc / 100) ** df.index
terminal_value_pv = terminal_value / (1 + wacc / 100) ** 10

# Calculate the enterprise value (EV), excluding the first row of present values
ev = df["自由現金流_PV"].iloc[1:].sum() + terminal_value_pv
equity_value = ev + cash - debt

int_value = round(equity_value / share_outstanding,2)


# Display the DataFrame and the calculated values




st.markdown(f"<h2 style='color:blue;'>公司名稱: {companyName}</h2>", unsafe_allow_html=True)

col, col2 = st.columns(2)
with col:
    st.markdown(f"<h2 style='color:blue;'>股價: {price}</h2>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<h2 style='color:blue;'>貼現價值: {int_value}</h2>", unsafe_allow_html=True)



col, col2 = st.columns(2)
with col:
    st.write(f"營收 (TTM): {ttm_revenue:,} {currency}")
with col2:
    st.write(f"自由現金流 (TTM): {ttm_fcf:,} {currency}")
st.write(f"自由現金流收益率: {fcf_yield}%")

st.write("折現現金流模型")
st.table(df.style.apply(highlight_first_row, axis=1).format({"自由現金流": "${:,.0f}", "自由現金流_PV": "${:,.0f}"}))
col, col2 = st.columns(2)
with col:
    st.write(f"終值: {terminal_value:,.0f}")
with col2:
    st.write(f"終值_PV: {terminal_value_pv:,.0f} ")

st.write("---------------")
st.write(f"企業價值: {ev:,.0f}")
col, col2 = st.columns(2)
with col:
    st.write(f"(+) 現金及現金等值: {cash:,.0f}")
with col2:
    st.write(f"(-) 總負債: {debt:,.0f}")

st.write(f"股權價值: {equity_value:,.0f}")
st.write(f"發行股份數量: {share_outstanding:,}")
