import streamlit as st
import time

def auto_refresh(interval=120):

    st.sidebar.info(f"Auto refresh every {interval} seconds")

    time.sleep(interval)

    st.rerun()