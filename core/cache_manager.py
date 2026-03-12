import streamlit as st

@st.cache_data(ttl=120)
def cache_dataframe(df):
    return df