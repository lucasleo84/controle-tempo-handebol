# ================================
#   CONTROLE DE JOGO - APP.PY
#   Versão otimizada para Streamlit Cloud
#   com watchdog desativado e autorefresh seguro
# ================================

import os

# --- 🧰 Correções de ambiente ---
# Evita travamentos no Streamlit Cloud (limite de inotify)
os.environ["WATCHDOG_MAX_INSTANCES"] = "0"
os.environ["STREAMLIT_WATCHDOG"] = "false"

# --- Importações principais ---
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- Importações locais (ajuste robusto de path) ---
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

from jogador import (
    inicializar_equipes_se_nao_existirem,
    formato_mmss,
    atualizar_tempos,
    atualizar_penalidades,
    definir_titulares,
    corrigir_titulares,
    set_posicao_titular,
    pode_substituir,
    pode_penalizar,
    aplicar_exclusao_2min,
    aplicar_expulsao,
    efetuar_substituicao,
    pode_completar,
    completar_substituicao,
)

from registros import salvar_csv
from sons import tocar_alarme

# ================================
#   CONFIGURAÇÃO INICIAL DO APP
# ================================
st.set_page_config(
    page_title="Controle de Jogo",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Estado inicial ---
if "iniciado" not in st.session_state:
    st.session_state.update({
        "iniciado": False,
        "cronometro": 0,
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "slots_abertos": {"A": 0, "B": 0},
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "dark_mode": False
    })

# --- Inicializa equipes se ainda não existirem ---
inicializar_equipes_se_nao_existirem(st.session_state)

# --- Autorefresh otimizado ---
# Atualiza o app somente quando o cronômetro está rodando
if st.session_state["iniciado"]:
    st_autorefresh(interval=1000, limit=None, key="refresh_tick")
else:
    st_autorefresh(interval=0, key="refresh_pause")
