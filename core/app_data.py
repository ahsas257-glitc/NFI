import streamlit as st

from core.data_engine import DataEngine
from services.data_loader import load_raw_data_from_secrets


@st.cache_data(ttl=300, show_spinner=False)
def load_app_data():
    raw_df = load_raw_data_from_secrets(st.secrets)
    engine = DataEngine(raw_df)
    return engine.get_clean_data()
