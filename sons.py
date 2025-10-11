import base64
import streamlit as st

def tocar_alarme():
    beep = "UklGRlIAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YVIAAABJRElJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJ"
    audio_bytes = base64.b64decode(beep)
    st.audio(audio_bytes, format="audio/wav", start_time=0)
