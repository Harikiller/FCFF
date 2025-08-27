import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Intrinsic Value Calculator", layout="wide")
st.title("📈 Intrinsic Value Calculator")

st.sidebar.header("Select Company Type")
company_type = st.sidebar.radio("Company Type", ["Financials", "Non-Financials"])

# Utility functions
def round2(x):
    return round(x, 2)

# Initialize history
history_file = "valuation_history.csv"

# ---------- Financials Section ----------
if company_type == "Financials":
    st.header("Valuation Models for Financial Companies")
    model = st.selectbox("Choose a Valuation Model", [
        "Gordon Growth DDM",
        "ROE-based DDM",
        "Two-stage DDM",
        "Residual Income Model"
    ])

    if model == "Gordon Growth DDM":
        D1 = st.number_input("Expected Dividend Next Year (D1)", value=10.0, step=0.1)
        g = st.number_input("Expected perpetual growth rate g (%)", value=5.0, step=0.1) / 100
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
        Ke = KePct / 100

        calculate = st.button("💡 Calculate Intrinsic Value")
        if calculate:
            if Ke <= g:
                st.error("Cost of Equity must be greater than growth rate")
            else:
                IV = D1 / (Ke - g)
                st.write(f"**Formula:** IV = D1 / (Ke - g)")
                st.write(f"**Step 1:** Ke - g = {round2(Ke - g)}")
                st.write(f"**Step 2:** IV = {D1} / {round2(Ke - g)}")
                st.success(f"Intrinsic Value = {round2(IV)}")

    elif model == "ROE-based DDM":
        BV = st.number_input("Book Value per share (BV)", value=100.0, step=0.1)
        ROE = st.number_input("Return on Equity (ROE %)", value=15.0, step=0.1) / 100
        payout = st.number_input("Dividend Payout Ratio (%)", value=40.0, step=0.1) / 100
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
        Ke = KePct / 100

        calculate = st.button("💡 Calculate Intrinsic Value")
        if calculate:
            b = 1 - payout
            g = ROE * b
            D1 = BV * ROE * payout
            if Ke <= g:
                st.error("Ke must be greater than growth")
            else:
                IV = D1 / (Ke - g)
                st.write(f"**Step 1:** Retention Ratio (b) = 1 - {payout} = {round2(b)}")
                st.write(f"**Step 2:** Growth (g) = ROE × b = {ROE} × {round2(b)} = {round2(g)}")
                st.write(f"**Step 3:** Dividend (D1) = BV × ROE × Payout = {BV} × {ROE} × {payout} = {round2(D1)}")
                st.write(f"**Step 4:** IV = {round2(D1)} / ({round2(Ke)} - {round2(g)})")
                st.success(f"Intrinsic Value = {round2(IV)}")

    elif model == "Two-stage DDM":
        D0 = st.number_input("Current Dividend (D0)", value=8.0, step=0.1)
        g1 = st.number_input("Growth rate for high growth phase (%)", value=15.0, step=0.1) / 100
        n = int(st.number_input("Years of high growth", value=5, step=1))
        g2 = st.number_input("Stable growth rate g2 (%)", value=6.0, step=0.1) / 100
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
        Ke = KePct / 100

        calculate = st.button("💡 Calculate Intrinsic Value")
        if calculate:
            dividends = [D0 * ((1+g1)**t) for t in range(1, n+1)]
            pvDiv = sum([dividends[t-1] / ((1+Ke)**t) for t in range(1, n+1)])
            TV = dividends[-1] * (1+g2) / (Ke - g2)
            pvTV = TV / ((1+Ke)**n)
            IV = pvDiv + pvTV
            st.write(f"**Step 1:** Forecasted Dividends = {[round2(d) for d in dividends]}")
            st.write(f"**Step 2:** PV of Dividends = {round2(pvDiv)}")
            st.write(f"**Step 3:** Terminal Value (TV) = {round2(TV)}")
            st.write(f"**Step 4:** PV of Terminal Value = {round2(pvTV)}")
            st.success(f"Intrinsic Value = {round2(IV)}")

    elif model == "Residual Income Model":
        BV = st.number_input("Current Book Value (BV)", value=100.0, step=0.1)
        EPS = st.number_input("Earnings Per Share (EPS)", value=15.0, step=0.1)
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
        Ke = KePct / 100
        growth = st.number_input("Growth rate of residual income (%)", value=5.0, step=0.1) / 100

        calculate = st.button("💡 Calculate Intrinsic Value")
        if calculate:
            RI = EPS - (Ke * BV)
            IV = BV + (RI / (Ke - growth))
            st.write(f"**Step 1:** Residual Income = EPS - Ke × BV = {EPS} - {round2(Ke)} × {BV} = {round2(RI)}")
            st.write(f"**Step 2:** IV = BV + RI / (Ke - g) = {BV} + {round2(RI)} / ({round2(Ke)} - {round2(growth)})")
            st.success(f"Intrinsic Value = {round2(IV)}")

# ---------- Non-Financials Section ----------
else:
    st.header("Valuation Models for Non-Financial Companies")

    EBIT = st.number_input("EBIT", value=1000.0, step=10.0)
    tax = st.number_input("Tax Rate (%)", value=30.0, step=0.1) / 100
    dep = st.number_input("Depreciation", value=100.0, step=10.0)
    capex = st.number_input("Capital Expenditure", value=200.0, step=10.0)
    wc = st.number_input("Change in Working Capital", value=50.0, step=10.0)
    years = int(st.number_input("Forecast Period (years)", value=5, step=1))
    gT = st.number_input("Terminal growth rate (%)", value=4.0, step=0.1) / 100

    KePct = st.number_input("Cost of Equity (%)", value=12.0, step=0.1)
    Ke = KePct / 100
    KdPct = st.number_input("Cost of Debt (%)", value=8.0, step=0.1)
    Kd = KdPct / 100
    E = st.number_input("Equity Value", value=5000.0, step=100.0)
    D = st.number_input("Debt Value", value=2000.0, step=100.0)
    V = E + D
    taxRate = st.number_input("Corporate Tax Rate (%)", value=30.0, step=0.1) / 100
    WACC = (E/V)*Ke + (D/V)*Kd*(1-taxRate)

    calculate = st.button("💡 Calculate Intrinsic Value")
    if calculate:
        FCFF = [(EBIT*(1-tax) + dep - capex - wc) for _ in range(years)]
        pvFCFF = [FCFF[t] / ((1+WACC)**(t+1)) for t in range(years)]
        TV = (FCFF[-1]*(1+gT)) / (WACC - gT)
        pvTV = TV / ((1+WACC)**years)
        EV = sum(pvFCFF) + pvTV
        EquityValue = EV - D
        IV = EquityValue / E if E > 0 else 0

        st.write(f"**Step 1:** FCFF Forecasts = {[round2(f) for f in FCFF]}")
        st.write(f"**Step 2:** PV of FCFF = {round2(sum(pvFCFF))}")
        st.write(f"**Step 3:** Terminal Value (TV) = {round2(TV)}")
        st.write(f"**Step 4:** PV of Terminal Value = {round2(pvTV)}")
        st.write(f"**Step 5:** Enterprise Value = {round2(EV)}")
        st.write(f"**Step 6:** Equity Value = {round2(EquityValue)}")
        st.success(f"Intrinsic Value per share ≈ {round2(IV)}")
