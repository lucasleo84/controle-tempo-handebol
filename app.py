# ================================
#   CONTROLE DE JOGO - APP.PY
#   Versão estável para Streamlit Cloud
#   (sem loops, watchdog desativado, cronômetro fluido)
# ================================

import os

# --- Correções de ambiente ---
os.environ["WATCHDOG_MAX_INSTANCES"] = "0"
os.environ["STREAMLIT_WATCHDOG"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

# --- Importações principais ---
import streamlit as st
import pandas as pd
import time
import sys

# --- Configuração de caminho para pacotes locais ---
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
        "dark_mode": False
    })

# Inicializa equipes
inicializar_equipes_se_nao_existirem(st.session_state)


# ================================
#   ESTILO E MODO NOTURNO
# ================================
def aplicar_css():
    dark = st.session_state["dark_mode"]
    bg = "#0e1117" if dark else "#ffffff"
    fg = "#e6edf3" if dark else "#111111"
    muted = "#9aa4ad" if dark else "#666666"

    st.markdown(
        f"""
        <style>
        body {{
            background-color: {bg};
            color: {fg};
        }}
        #sticky-timer {{
            position: sticky;
            top: 0;
            z-index: 999;
            padding: 8px 12px;
            background: {bg}CC;
            backdrop-filter: blur(6px);
            border-bottom: 1px solid {"#2a2f37" if dark else "#e9ecef"};
        }}
        .timer-chip {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 8px;
            font-weight: 700;
            border: 1px solid {"#3a3f48" if dark else "#dcdcdc"};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_css()


# ================================
#   ATUALIZAÇÃO SEGURA DO CRONÔMETRO
# ================================
def atualizar_cronometro():
    """Atualiza o cronômetro sem loops infinitos."""
    if st.session_state["iniciado"]:
        agora = time.time()
        if agora - st.session_state["ultimo_tick"] >= 1:
            st.session_state["cronometro"] += 1
            st.session_state["ultimo_tick"] = agora
            atualizar_tempos(st.session_state)
            terminou_alguma = atualizar_penalidades(st.session_state)
            if terminou_alguma:
                st.toast("🔔 Penalidade encerrada!", icon="🔊")
                tocar_alarme()


# ================================
#   ABAS PRINCIPAIS
# ================================
tabs = st.tabs([
    "Configuração da Equipe",
    "Controle do Jogo",
    "Visualização de Dados"
])

# ==============================================================
# ABA 1 — CONFIGURAÇÃO DA EQUIPE
# ==============================================================
with tabs[0]:
    st.subheader("Configuração da Equipe")

    colA, colB = st.columns(2, gap="large")
    for equipe, c in zip(["A", "B"], [colA, colB]):
        with c:
            st.markdown(f"### Equipe {equipe}")
            nome = st.text_input(f"Nome da equipe {equipe}", key=f"nome_{equipe}")
            qtd = st.number_input(f"Quantidade de jogadores {equipe}", min_value=1, max_value=14,
                                  value=len(st.session_state['equipes'][equipe]) or 7, key=f"qtd_{equipe}")

            nums = []
            cols = st.columns(7)
            for i in range(int(qtd)):
                with cols[i % 7]:
                    val = st.number_input(f"#{i+1}", min_value=0, max_value=999,
                                          value=st.session_state['equipes'][equipe][i]['numero']
                                          if i < len(st.session_state['equipes'][equipe]) else (i+1),
                                          key=f"num_{equipe}_{i}")
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
# ABA 2 — CONTROLE DO JOGO
# ==============================================================
with tabs[1]:
    atualizar_cronometro()

    st.markdown(
        f"""
        <div id="sticky-timer">
            <span class="timer-chip">⏱ {formato_mmss(st.session_state['cronometro'])}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    ctop1, ctop2, ctop3, ctop4, ctop5 = st.columns([1, 1, 1, 1, 2])
    with ctop1:
        if st.button("▶️ Iniciar"):
            st.session_state["iniciado"] = True
            st.session_state["ultimo_tick"] = time.time()
    with ctop2:
        if st.button("⏸️ Pausar"):
            st.session_state["iniciado"] = False
    with ctop3:
        if st.button("🔁 Zerar"):
            st.session_state["cronometro"] = 0
            for eq in ["A", "B"]:
                for j in st.session_state["equipes"][eq]:
                    j.update({
                        "tempo_jogado": 0,
                        "tempo_banco": 0,
                        "tempo_penalidade": 0,
                        "exclusoes": 0,
                        "elegivel": True,
                        "expulso": False
                    })
                st.session_state["penalidades"] = []
                st.session_state["slots_abertos"][eq] = 0
                st.session_state["titulares_definidos"][eq] = False
                st.session_state["funcoes"][eq] = {}
    with ctop4:
        if st.button("💾 Salvar CSV"):
            salvar_csv(st.session_state)
            st.success("Dados salvos em dados/saida_jogo.csv")
    with ctop5:
        st.toggle("Modo noturno", key="dark_mode", value=st.session_state["dark_mode"])
        aplicar_css()

    st.markdown("### Definir Titulares")
    infoA, infoB = st.columns(2)
    for equipe, box in zip(["A", "B"], [infoA, infoB]):
        with box:
            st.markdown(f"**Equipe {equipe}** — {st.session_state.get(f'nome_{equipe}_salvo', '') or 'Sem nome'}")
            nums = [j["numero"] for j in st.session_state["equipes"][equipe]]
            titulares_sel = st.multiselect(
                "Selecione titulares (obrigatório)",
                options=nums,
                disabled=st.session_state["titulares_definidos"][equipe],
                key=f"tit_{equipe}"
            )
            cta1, cta2 = st.columns(2)
            with cta1:
                if st.button(f"Confirmar Titulares {equipe}", disabled=st.session_state["titulares_definidos"][equipe]):
                    if len(titulares_sel) == 0:
                        st.error("Selecione ao menos 1 titular.")
                    else:
                        definir_titulares(st.session_state, equipe, titulares_sel)
                        st.success("Titulares definidos e travados.")
            with cta2:
                if st.button(f"Corrigir {equipe}"):
                    corrigir_titulares(st.session_state, equipe)
                    st.info("Titulares desbloqueados para edição.")

    st.divider()

    # Função dos jogadores
    st.markdown("### Função dos jogadores (opcional)")
    posicoes = ["Goleiro", "Pivô", "Ponta Esquerda", "Armação Esquerda",
                "Armação Central", "Armação Direita", "Ponta Direita"]

    fA, fB = st.columns(2)
    for equipe, box in zip(["A", "B"], [fA, fB]):
        with box:
            st.markdown(f"**Equipe {equipe}**")
            titulares = [j for j in st.session_state["equipes"][equipe] if j["estado"] == "jogando"]
            if not titulares:
                st.info("Defina titulares para atribuir funções.")
            else:
                for j in titulares:
                    val = st.selectbox(
                        f"#{j['numero']}",
                        options=["(sem função)"] + posicoes,
                        index=0 if j["numero"] not in st.session_state["funcoes"][equipe]
                        else (["(sem função)"] + posicoes).index(
                            st.session_state["funcoes"][equipe][j["numero"]]),
                        key=f"func_{equipe}_{j['numero']}"
                    )
                    set_posicao_titular(st.session_state, equipe, j["numero"],
                                        None if val == "(sem função)" else val)

    st.divider()

    # Controle de Tempo
    st.markdown("### Controle de Tempo")
    colA, colB = st.columns(2)
    for equipe, col in zip(["A", "B"], [colA, colB]):
        with col:
            st.markdown(f"**Equipe {equipe}**")
            df = pd.DataFrame(st.session_state["equipes"][equipe])
            df_view = df[["numero", "estado", "exclusoes", "elegivel"]]
            st.dataframe(df_view, use_container_width=True)

            sub_sel = st.multiselect("Selecionar 2 para Substituir", options=list(df["numero"]), key=f"sub_sel_{equipe}")
            um_sel = st.selectbox("Selecionar 1 para 2 Min / Expulsão / Completou", options=list(df["numero"]), key=f"um_sel_{equipe}")

            a1, a2, a3, a4 = st.columns(4)
            with a1:
                if st.button("Substituir", key=f"btn_sub_{equipe}"):
                    ok, msg = efetuar_substituicao(st.session_state, equipe, sub_sel)
                    st.success(msg) if ok else st.error(msg)
            with a2:
                if st.button("2 Minutos", key=f"btn_2min_{equipe}"):
                    ok, msg, terminou3 = aplicar_exclusao_2min(st.session_state, equipe, um_sel)
                    if ok:
                        st.warning(msg)
                        if terminou3:
                            st.error("Jogador tornou-se inelegível (3 exclusões).")
                    else:
                        st.error(msg)
            with a3:
                if st.button("Expulsão", key=f"btn_exp_{equipe}"):
                    ok, msg = aplicar_expulsao(st.session_state, equipe, um_sel)
                    st.error(msg) if ok else st.error(msg)
            with a4:
                if st.button("Completou", key=f"btn_comp_{equipe}"):
                    ok, msg = completar_substituicao(st.session_state, equipe, um_sel)
                    st.success(msg) if ok else st.error(msg)

    st.divider()
    st.markdown("#### Penalidades ativas")
    if st.session_state["penalidades"]:
        pen_df = pd.DataFrame(st.session_state["penalidades"])
        st.dataframe(pen_df, use_container_width=True)
    else:
        st.info("Nenhuma penalidade ativa.")


# ==============================================================
# ABA 3 — VISUALIZAÇÃO DE DADOS
# ==============================================================
with tabs[2]:
    st.subheader("Visualização de Dados")
    for equipe in ["A", "B"]:
        st.markdown(f"### Equipe {equipe}")
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        if df.empty:
            st.info("Equipe vazia.")
            continue
        viz = df.copy()
        viz["tempo_jogado (min)"] = (viz["tempo_jogado"] / 60).round(2)
        viz["tempo_banco (min)"] = (viz["tempo_banco"] / 60).round(2)
        viz["tempo_2min (min)"] = (viz["tempo_penalidade"] / 60).round(2)
        st.dataframe(viz[["numero", "estado", "exclusoes", "elegivel",
                          "tempo_jogado (min)", "tempo_banco (min)", "tempo_2min (min)"]],
                     use_container_width=True)
