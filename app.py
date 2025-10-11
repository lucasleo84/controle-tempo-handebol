# ======================================
# CONTROLE DE JOGO - APP_v9.1 (híbrido JS + Python)
# ======================================

import os
import sys
import time
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --- Caminho para módulos locais ---
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))
from jogador import (
    inicializar_equipes_se_nao_existirem,
    formato_mmss,
    definir_titulares,
    corrigir_titulares,
    set_posicao_titular,
    aplicar_exclusao_2min,
    aplicar_expulsao,
    efetuar_substituicao,
    completar_substituicao,
)
from registros import salvar_csv
from sons import tocar_alarme


# ======================================
# CONFIGURAÇÃO INICIAL
# ======================================
st.set_page_config(page_title="Controle de Jogo", layout="wide", initial_sidebar_state="collapsed")

if "iniciado" not in st.session_state:
    st.session_state.update({
        "cronometro": 0.0,
        "ultimo_tick": time.time(),
        "iniciado": False,
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "invertido": False,
        "slots_abertos": {"A": 0, "B": 0},
        "cores": {"A": "#00AEEF", "B": "#EC008C"},
        "sub_msg_time": {"A": 0.0, "B": 0.0},
    })

inicializar_equipes_se_nao_existirem(st.session_state)


# ======================================
# PALETA CMYK
# ======================================
PALETA = {
    "Ciano": "#00AEEF",
    "Magenta": "#EC008C",
    "Amarelo": "#FFD700",
    "Preto": "#000000",
    "Azul": "#0072CE",
    "Vermelho": "#ED1C24",
    "Verde": "#00A651",
    "Laranja": "#F7941D",
    "Roxo": "#92278F",
    "Cinza": "#6D6E71",
}


# ======================================
# CSS FIXO
# ======================================
st.markdown(
    """
    <style>
    .block-container { padding-top: 150px; }

    #header-fixed {
        position: sticky;
        top: 0;
        background-color: #ffffff;
        border-bottom: 2px solid #ddd;
        text-align: center;
        padding: 4px 0 0 0;
        z-index: 9999;
    }
    .digital {
        font-family: 'Courier New', monospace;
        font-size: 30px;
        font-weight: bold;
        color: #FFD700;
        background-color: #000;
        padding: 6px 20px;
        border-radius: 6px;
        display: inline-block;
        letter-spacing: 2px;
        box-shadow: 0 0 10px rgba(255, 215, 0, .5);
    }
    div.stTabs > div[data-baseweb="tab-list"] {
        position: sticky;
        top: 56px;
        background: #fff;
        z-index: 9998;
        border-bottom: 1px solid #e5e7eb;
        padding-top: 6px;
    }
    .chip { display:inline-flex; align-items:center; gap:.5rem; padding:.25rem .6rem; border-radius:999px; font-weight:700; color:#fff; }
    .chip-sai   { background:#ff4b4b; }
    .chip-entra { background:#1aa260; }
    .side-head { font-weight:800; font-size:1.05rem; padding:.35rem .6rem; border-radius:8px; color:#fff; display:inline-block; }
    hr { border:0; height:1px; background:#e4e4e7; margin:12px 0; }
    </style>
    """,
    unsafe_allow_html=True
)


# ======================================
# FUNÇÕES CRONÔMETRO LÓGICO
# ======================================
def tempo_logico_atual():
    if st.session_state["iniciado"]:
        agora = time.time()
        return st.session_state["cronometro"] + (agora - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def iniciar_jogo():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()

def pausar_jogo():
    if st.session_state["iniciado"]:
        st.session_state["cronometro"] = tempo_logico_atual()
        st.session_state["iniciado"] = False

def zerar_jogo():
    st.session_state["iniciado"] = False
    st.session_state["cronometro"] = 0.0
    st.session_state["ultimo_tick"] = time.time()
    for eq in ["A", "B"]:
        for j in st.session_state["equipes"][eq]:
            j.update({
                "tempo_jogado": 0, "tempo_banco": 0, "tempo_penalidade": 0,
                "exclusoes": 0, "elegivel": True, "expulso": False, "estado": "banco"
            })
    st.session_state["penalidades"] = []


# ======================================
# CRONÔMETRO VISUAL (JS)
# ======================================
def render_cronometro_js():
    """Renderiza cronômetro visual fluido com JS sincronizado com tempo lógico."""
    iniciado = bool(st.session_state["iniciado"])
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if iniciado else None

    iniciado_js = "true" if iniciado else "false"
    base_elapsed_js = json.dumps(base_elapsed)
    start_epoch_js = json.dumps(start_epoch)

    html = f"""
    <div id="header-fixed">
        <div id="cronovisual" class="digital">⏱ {formato_mmss(base_elapsed)}</div>
    </div>
    <script>
    (function(){{
        const el = document.getElementById('cronovisual');
        const iniciado = {iniciado_js};
        const baseElapsed = {base_elapsed_js};
        const startEpoch = {start_epoch_js};

        function fmt(sec){{
            sec = Math.max(0, Math.floor(sec));
            const m = Math.floor(sec/60);
            const s = sec % 60;
            return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
        }}
        function tick(){{
            let elapsed = baseElapsed;
            if(iniciado && startEpoch){{
                const now = Date.now()/1000;
                elapsed = baseElapsed + (now - startEpoch);
            }}
            el.textContent = '⏱ ' + fmt(elapsed);
        }}
        tick();
        if(window.__cronovisual_timer) clearInterval(window.__cronovisual_timer);
        window.__cronovisual_timer = setInterval(tick, 250);
    }})();
    </script>
    """
    components.html(html, height=72)


# ======================================
# CABEÇALHO FIXO
# ======================================
render_cronometro_js()

bc1, bc2, bc3, bc4 = st.columns([1, 1, 1, 1])
with bc1:
    if st.button("▶️ Iniciar"):
        iniciar_jogo()
with bc2:
    if st.button("⏸️ Pausar"):
        pausar_jogo()
with bc3:
    if st.button("🔁 Zerar"):
        zerar_jogo()
with bc4:
    if st.button("💾 Salvar CSV"):
        salvar_csv(st.session_state)
        st.success("Dados salvos com sucesso!")


# ======================================
# ABAS
# ======================================
tabs = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

# (continua o restante igual à versão anterior: configuração, titulares, controle e visualização)
