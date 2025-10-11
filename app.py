# ======================================
# CONTROLE DE JOGO - APP_v8.3
# ======================================

import os
import sys
import time
import threading
import pandas as pd
import streamlit as st

# --- Caminho para os módulos locais ---
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))
from jogador import (
    inicializar_equipes_se_nao_existirem,
    formato_mmss,
    atualizar_tempos,
    atualizar_penalidades,
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
#   CONFIGURAÇÃO INICIAL
# ======================================
st.set_page_config(page_title="Controle de Jogo", layout="wide", initial_sidebar_state="collapsed")

if "iniciado" not in st.session_state:
    st.session_state.update({
        "iniciado": False,
        "cronometro": 0.0,
        "ultimo_tick": time.time(),
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "invertido": False,
        "slots_abertos": {"A": 0, "B": 0},
        "cores": {"A": "#00AEEF", "B": "#EC008C"},
        "sub_msg_time": {"A": 0.0, "B": 0.0},
        "last_render": time.time(),
    })

inicializar_equipes_se_nao_existirem(st.session_state)

# ======================================
#   CSS FIXO E ESTILO
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
#   ATUALIZAÇÃO FLUIDA DO CRONÔMETRO
# ======================================
def atualizar_cronometro():
    """Atualiza o cronômetro de forma precisa"""
    agora = time.time()
    delta = agora - st.session_state["last_render"]
    st.session_state["last_render"] = agora

    if st.session_state["iniciado"]:
        st.session_state["cronometro"] += delta
        atualizar_tempos(st.session_state)
        if atualizar_penalidades(st.session_state):
            st.toast("🔔 Penalidade encerrada!", icon="🔊")
            tocar_alarme()

# executa a atualização e agenda novo ciclo
atualizar_cronometro()
threading.Thread(target=lambda: (time.sleep(1), st.experimental_rerun()), daemon=True).start()

# ======================================
#   CRONÔMETROS DE 2 MINUTOS (EXCLUSÕES)
# ======================================
def atualizar_penalidades_2min():
    """Atualiza cronômetros de 2 minutos"""
    ativos = []
    for p in st.session_state["penalidades"]:
        if p["tipo"] == "2min":
            p["restante"] -= (time.time() - p["ultimo_tick"])
            p["ultimo_tick"] = time.time()
            if p["restante"] <= 0:
                p["ativo"] = False
                st.toast(f"⚠️ Jogador {p['jogador']} da equipe {p['equipe']} pode retornar!")
                tocar_alarme()
            else:
                ativos.append(p)
    st.session_state["penalidades"] = ativos

# ======================================
#   CABEÇALHO FIXO (CRONÔMETRO + BOTÕES)
# ======================================
with st.container():
    st.markdown(
        f"""
        <div id="header-fixed">
            <div class="digital">⏱ {formato_mmss(st.session_state['cronometro'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        if st.button("▶️ Iniciar"):
            st.session_state["iniciado"] = True
            st.session_state["ultimo_tick"] = time.time()
    with c2:
        if st.button("⏸️ Pausar"):
            st.session_state["iniciado"] = False
    with c3:
        if st.button("🔁 Zerar"):
            st.session_state["iniciado"] = False
            st.session_state["cronometro"] = 0.0
            for eq in ["A","B"]:
                for j in st.session_state["equipes"][eq]:
                    j.update({
                        "tempo_jogado": 0, "tempo_banco": 0, "tempo_penalidade": 0,
                        "exclusoes": 0, "elegivel": True, "expulso": False, "estado":"banco"
                    })
            st.session_state["penalidades"] = []
    with c4:
        if st.button("💾 Salvar CSV"):
            salvar_csv(st.session_state)
            st.success("Dados salvos em dados/saida_jogo.csv")

# ======================================
#   PALETA CMYK
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
#   ABAS PRINCIPAIS
# ======================================
tabs = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização de Dados"
])

# ==============================================================
# ABA 1 – CONFIGURAÇÃO
# ==============================================================
with tabs[0]:
    st.subheader("Configuração da Equipe")
    colA, colB = st.columns(2)
    for equipe, col in zip(["A","B"], [colA, colB]):
        with col:
            st.markdown(f"### Equipe {equipe}")
            cor_nome = st.selectbox(
                f"Cor da Equipe {equipe} (CMYK)",
                options=list(PALETA.keys()),
                key=f"cor_nome_{equipe}"
            )
            st.session_state["cores"][equipe] = PALETA[cor_nome]

            nome = st.text_input(f"Nome da equipe {equipe}", key=f"nome_{equipe}")
            qtd = st.number_input(
                f"Quantidade de jogadores {equipe}",
                min_value=1, max_value=14,
                value=len(st.session_state['equipes'][equipe]) or 7,
                key=f"qtd_{equipe}"
            )
            nums = []
            grid = st.columns(7)
            for i in range(int(qtd)):
                with grid[i % 7]:
                    val = st.number_input(
                        f"#{i+1}", min_value=0, max_value=999,
                        value=st.session_state['equipes'][equipe][i]['numero']
                              if i < len(st.session_state['equipes'][equipe]) else (i+1),
                        key=f"num_{equipe}_{i}"
                    )
                    nums.append(int(val))
            if st.button(f"Salvar equipe {equipe}"):
                nova = []
                for n in nums:
                    nova.append({
                        "numero": n, "estado":"banco",
                        "tempo_jogado":0, "tempo_banco":0, "tempo_penalidade":0,
                        "exclusoes":0, "elegivel":True, "expulso":False
                    })
                st.session_state["equipes"][equipe] = nova
                st.session_state[f"nome_{equipe}_salvo"] = nome
                st.success(f"Equipe {equipe} salva!")

# ==============================================================
# ABA 2 – TITULARES
# ==============================================================
with tabs[1]:
    st.subheader("Definir Titulares e Funções")
    for equipe in ["A","B"]:
        with st.expander(f"⚙️ Configurar equipe {equipe}", expanded=False):
            nums = [j["numero"] for j in st.session_state["equipes"][equipe]]
            titulares_sel = st.multiselect(
                "Selecione titulares (obrigatório)",
                options=nums,
                disabled=st.session_state["titulares_definidos"][equipe],
                key=f"tit_{equipe}"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Confirmar titulares {equipe}", disabled=st.session_state["titulares_definidos"][equipe]):
                    definir_titulares(st.session_state, equipe, titulares_sel)
                    st.success("Titulares definidos.")
            with c2:
                if st.button(f"Corrigir {equipe}"):
                    corrigir_titulares(st.session_state, equipe)
                    st.info("Titulares desbloqueados.")

# ==============================================================
# ABA 3 – CONTROLE DE JOGO
# ==============================================================
with tabs[2]:
    st.subheader("Controle do Jogo")
    st.toggle("🔁 Inverter lados (A↔B)", key="invertido")
    lados = ["A","B"]
    if st.session_state["invertido"]:
        lados = ["B","A"]
    col_esq, col_dir = st.columns(2)

    def painel(equipe):
        st.markdown(
            f"<span class='side-head' style='background:{st.session_state['cores'][equipe]};'>Equipe {equipe}</span>",
            unsafe_allow_html=True
        )

        jogando = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"]=="jogando" and j["elegivel"]]
        banco   = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"]=="banco" and j["elegivel"]]

        c1, c2, c3 = st.columns([1,1,1.1])
        sai = c1.selectbox("🟥 Sai", [None]+jogando, key=f"sai_{equipe}")
        entra = c2.selectbox("🟩 Entra", [None]+banco, key=f"entra_{equipe}")

       if c3.button("Substituir", key=f"substituir_{equipe}", disabled=(sai is None or entra is None)):
            ok, msg = efetuar_substituicao(st.session_state, equipe, [str(sai), str(entra)])
            if ok:
                st.session_state[f"sai_{equipe}"] = None
                st.session_state[f"entra_{equipe}"] = None
                st.session_state["sub_msg_time"][equipe] = time.time()
                st.success("Substituição feita.")
            else:
                st.error(msg)

        now = time.time()
        if now - st.session_state["sub_msg_time"][equipe] < 3:
            st.markdown(
                f"<span class='chip chip-sai'>Sai {sai}</span> <span class='chip chip-entra'>Entra {entra}</span>",
                unsafe_allow_html=True
            )

    with col_esq: painel(lados[0])
    with col_dir: painel(lados[1])

# ==============================================================
# ABA 4 – VISUALIZAÇÃO
# ==============================================================
with tabs[3]:
    st.subheader("Visualização de Dados")
    for equipe in ["A","B"]:
        st.markdown(f"### Equipe {equipe}")
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        if df.empty:
            st.info("Sem dados.")
            continue
        st.dataframe(df[["numero","estado","exclusoes","elegivel"]], use_container_width=True)
