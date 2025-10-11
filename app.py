# ======================================
# CONTROLE DE JOGO - APP_V6.PY
# ======================================
# Autor: Lucas Leonardo e Ayla
# Versão estável e aprimorada para o Streamlit Cloud
# Estrutura: utils/jogador.py | utils/registros.py | utils/sons.py
# ======================================

import os
import time
import sys
import pandas as pd
import streamlit as st

# --- Estabilidade no Streamlit Cloud ---
os.environ["WATCHDOG_MAX_INSTANCES"] = "0"
os.environ["STREAMLIT_WATCHDOG"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# --- Caminho para módulos locais ---
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
#   CONFIGURAÇÃO INICIAL
# ================================
st.set_page_config(page_title="Controle de Jogo", layout="wide", initial_sidebar_state="collapsed")

if "iniciado" not in st.session_state:
    st.session_state.update({
        "iniciado": False,
        "cronometro": 0,
        "ultimo_tick": time.time(),
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "slots_abertos": {"A": 0, "B": 0},
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
    })

inicializar_equipes_se_nao_existirem(st.session_state)

# ================================
#   ESTILO GERAL E FIXAÇÃO
# ================================
st.markdown(
    """
    <style>
    /* Mantém cronômetro e abas fixas */
    .block-container {
        padding-top: 110px;
    }
    #header-fixed {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background-color: #ffffff;
        border-bottom: 2px solid #ddd;
        text-align: center;
        padding: 6px;
    }
    .digital {
        font-family: 'Courier New', monospace;
        font-size: 28px;
        font-weight: 700;
        color: #FFD700;
        background-color: #000000;
        padding: 8px 20px;
        border-radius: 8px;
        display: inline-block;
        letter-spacing: 2px;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.6);
    }
    .tabs-fixed {
        position: fixed;
        top: 60px;
        left: 0;
        right: 0;
        background: #ffffff;
        border-bottom: 1px solid #ccc;
        z-index: 9998;
        padding-bottom: 5px;
    }
    .tab-content {
        height: 75vh;
        overflow-y: auto;
        padding-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================================
#   CRONÔMETRO DIGITAL
# ================================
def tick_cronometro():
    if not st.session_state["iniciado"]:
        return
    agora = time.time()
    dt = int(agora - st.session_state["ultimo_tick"])
    if dt > 0:
        st.session_state["cronometro"] += dt
        st.session_state["ultimo_tick"] = agora
        atualizar_tempos(st.session_state)
        terminou = atualizar_penalidades(st.session_state)
        if terminou:
            st.toast("🔔 Penalidade encerrada!", icon="🔊")
            tocar_alarme()

tick_cronometro()

# ================================
#   HEADER FIXO (CRONÔMETRO + BOTÕES)
# ================================
st.markdown(
    f"""
    <div id="header-fixed">
        <div class="digital">⏱ {formato_mmss(st.session_state['cronometro'])}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Botões de controle
col1, col2, col3, col4, col5 = st.columns([1,1,1,1,2])
with col1:
    if st.button("▶️ Iniciar"):
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()
with col2:
    if st.button("⏸️ Pausar"):
        st.session_state["iniciado"] = False
with col3:
    if st.button("🔁 Zerar"):
        st.session_state["iniciado"] = False
        st.session_state["cronometro"] = 0
        for eq in ["A", "B"]:
            for j in st.session_state["equipes"][eq]:
                j.update({
                    "tempo_jogado": 0,
                    "tempo_banco": 0,
                    "tempo_penalidade": 0,
                    "exclusoes": 0,
                    "elegivel": True,
                    "expulso": False,
                    "estado": "banco"
                })
        st.session_state["penalidades"] = []
with col4:
    if st.button("💾 Salvar CSV"):
        salvar_csv(st.session_state)
        st.success("Dados salvos em dados/saida_jogo.csv")

# ================================
#   ABAS FIXAS
# ================================
tabs_html = """
<div class="tabs-fixed">
<b>Abas:</b> Configuração | Titulares | Controle | Visualização e Controle de Ações
</div>
"""
st.markdown(tabs_html, unsafe_allow_html=True)

# Cria as abas reais
tabs = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização e Controle de Ações"
])

# ==============================================================
# ABA 1 — CONFIGURAÇÃO DA EQUIPE
# ==============================================================
with tabs[0]:
    with st.container():
        st.subheader("Configuração da Equipe")
        colA, colB = st.columns(2)
        for equipe, col in zip(["A", "B"], [colA, colB]):
            with col:
                st.markdown(f"### Equipe {equipe}")
                nome = st.text_input(f"Nome da equipe {equipe}", key=f"nome_{equipe}")
                qtd = st.number_input(f"Quantidade de jogadores {equipe}", min_value=1, max_value=14,
                                      value=len(st.session_state['equipes'][equipe]) or 7, key=f"qtd_{equipe}")
                nums = []
                cols = st.columns(7)
                for i in range(int(qtd)):
                    with cols[i % 7]:
                        val = st.number_input(
                            f"#{i+1}",
                            min_value=0, max_value=999,
                            value=st.session_state['equipes'][equipe][i]['numero']
                            if i < len(st.session_state['equipes'][equipe]) else (i+1),
                            key=f"num_{equipe}_{i}"
                        )
                        nums.append(int(val))
                if st.button(f"Salvar equipe {equipe}"):
                    nova = []
                    for n in nums:
                        nova.append({
                            "numero": n,
                            "estado": "banco",
                            "tempo_jogado": 0,
                            "tempo_banco": 0,
                            "tempo_penalidade": 0,
                            "exclusoes": 0,
                            "elegivel": True,
                            "expulso": False
                        })
                    st.session_state["equipes"][equipe] = nova
                    st.session_state[f"nome_{equipe}_salvo"] = nome
                    st.success(f"Equipe {equipe} salva!")

# ==============================================================
# ABA 2 — DEFINIR TITULARES E FUNÇÕES
# ==============================================================
with tabs[1]:
    with st.container():
        st.subheader("Definição de Titulares e Funções")
        for equipe in ["A", "B"]:
            with st.expander(f"⚙️ Configurar equipe {equipe}", expanded=False):
                st.markdown(f"**Equipe {equipe}** — {st.session_state.get(f'nome_{equipe}_salvo', '') or 'Sem nome'}")
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
                        if len(titulares_sel) == 0:
                            st.error("Selecione ao menos 1 titular.")
                        else:
                            definir_titulares(st.session_state, equipe, titulares_sel)
                            st.success("Titulares definidos e travados.")
                with c2:
                    if st.button(f"Corrigir {equipe}"):
                        corrigir_titulares(st.session_state, equipe)
                        st.info("Titulares desbloqueados para edição.")

            with st.expander(f"📋 Funções dos jogadores (opcional) — {equipe}", expanded=False):
                posicoes = ["Goleiro", "Pivô", "Ponta Esquerda", "Armação Esquerda", "Armação Central", "Armação Direita", "Ponta Direita"]
                titulares = [j for j in st.session_state["equipes"][equipe] if j["estado"] == "jogando"]
                if not titulares:
                    st.info("Defina titulares para atribuir funções.")
                else:
                    for j in titulares:
                        atual = st.session_state["funcoes"][equipe].get(j["numero"])
                        val = st.selectbox(
                            f"#{j['numero']}",
                            options=["(sem função)"] + posicoes,
                            index=0 if atual is None else (["(sem função)"] + posicoes).index(atual),
                            key=f"func_{equipe}_{j['numero']}"
                        )
                        set_posicao_titular(st.session_state, equipe, j["numero"], None if val == "(sem função)" else val)

# ==============================================================
# ABA 3 — CONTROLE DO JOGO
# ==============================================================
with tabs[2]:
    with st.container():
        st.subheader("Controle do Jogo")
        st.markdown("O cronômetro no topo é atualizado automaticamente. Use os botões acima para iniciar, pausar ou zerar o tempo.")

# ==============================================================
# ABA 4 — VISUALIZAÇÃO E CONTROLE DE AÇÕES
# ==============================================================
with tabs[3]:
    with st.container():
        st.subheader("Visualização e Controle de Ações")
        for equipe in ["A", "B"]:
            st.markdown(f"### Equipe {equipe}")
            df = pd.DataFrame(st.session_state["equipes"][equipe])
            if df.empty:
                st.info("Equipe vazia.")
                continue
            # ---- Seleção de jogadores com Sai / Entra ----
            jogadores_ativos = [j for j in st.session_state["equipes"][equipe] if j["elegivel"]]
            labels = []
            for j in jogadores_ativos:
                labels.append(f"#{j['numero']}")
            sel = st.multiselect(
                "Selecione jogadores (1 para 2min/Expulsão/Completou, 2 para Substituir)",
                options=labels,
                key=f"sel_{equipe}"
            )
            # Adiciona texto dentro da seleção
            custom_opts = []
            for i, opt in enumerate(sel):
                if i == 0:
                    custom_opts.append(f"🟥 Sai {opt}")
                elif i == 1:
                    custom_opts.append(f"🟩 Entra {opt}")
            if custom_opts:
                st.write(" | ".join(custom_opts))

            # ---- Botões ----
            can_sub = len(sel) == 2
            can_one = len(sel) == 1
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("Substituir", key=f"sub_{equipe}", disabled=not can_sub):
                    ok, msg = efetuar_substituicao(st.session_state, equipe, sel)
                    st.success(msg) if ok else st.error(msg)
            with b2:
                if st.button("2 Minutos", key=f"exclui_{equipe}", disabled=not can_one):
                    ok, msg, terminou = aplicar_exclusao_2min(st.session_state, equipe, sel[0])
                    if ok:
                        st.warning(msg)
                        if terminou:
                            st.error("Jogador inelegível (3 exclusões).")
                    else:
                        st.error(msg)
            with b3:
                if st.button("Expulsão", key=f"expulsa_{equipe}", disabled=not can_one):
                    ok, msg = aplicar_expulsao(st.session_state, equipe, sel[0])
                    st.error(msg) if ok else st.error(msg)
            with b4:
                if st.button("Completou", key=f"comp_{equipe}", disabled=not can_one):
                    ok, msg = completar_substituicao(st.session_state, equipe, sel[0])
                    st.success(msg) if ok else st.error(msg)

            # ---- Tabela de estados e penalidades ----
            st.dataframe(df[["numero", "estado", "exclusoes", "elegivel"]], use_container_width=True)
            ativos = [p for p in st.session_state["penalidades"] if p["equipe"] == equipe]
            if ativos:
                st.markdown("#### Penalidades Ativas")
                pen_rows = []
                for p in ativos:
                    pen_rows.append({
                        "Jogador": f"#{p['jogador']}",
                        "Tipo": "2min" if p["tipo"] == "2min" else "Expulsão",
                        "Restante": formato_mmss(p["restante"])
                    })
                st.dataframe(pd.DataFrame(pen_rows), use_container_width=True)
            else:
                st.info("Nenhuma penalidade ativa.")
