import streamlit as st
import pandas as pd
import time
import plotly.express as px
from utils.registros import salvar_csv
from utils.jogador import (
    inicializar_equipes, atualizar_tempos,
    aplicar_penalidade, substituir_jogadores, atualizar_penalidades
)
from utils.sons import tocar_alarme

st.set_page_config(page_title="Controle de Jogo", layout="wide")

if "iniciado" not in st.session_state:
    st.session_state.update({
        "iniciado": False,
        "tempo_inicio": None,
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "cronometro": 0,
        "alerta_sonoro": False
    })

st.title("🏐 Controle de Jogo com Registro e Alertas")

colA, colB = st.columns(2)
with colA:
    if not st.session_state["equipes"]["A"]:
        qtdA = st.number_input("Jogadores Equipe A", min_value=1, max_value=14, value=7)
        if st.button("Criar Equipe A"):
            st.session_state["equipes"]["A"] = inicializar_equipes("A", qtdA)
            st.success("Equipe A criada!")
with colB:
    if not st.session_state["equipes"]["B"]:
        qtdB = st.number_input("Jogadores Equipe B", min_value=1, max_value=14, value=7)
        if st.button("Criar Equipe B"):
            st.session_state["equipes"]["B"] = inicializar_equipes("B", qtdB)
            st.success("Equipe B criada!")

if st.session_state["equipes"]["A"] and st.session_state["equipes"]["B"]:
    st.divider()
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        if st.button("▶️ Iniciar"):
            st.session_state["iniciado"] = True
            st.session_state["tempo_inicio"] = time.time()
    with c2:
        if st.button("⏸️ Pausar"):
            st.session_state["iniciado"] = False
    with c3:
        if st.button("🔁 Zerar"):
            st.session_state["cronometro"] = 0
            for equipe in ["A", "B"]:
                for j in st.session_state["equipes"][equipe]:
                    j["tempo_jogado"] = j["tempo_banco"] = j["tempo_penalidade"] = 0
    with c4:
        if st.button("💾 Salvar CSV"):
            salvar_csv(st.session_state)
            st.success("✅ Dados salvos em dados/saida_jogo.csv")

    if st.session_state["iniciado"]:
        st.session_state["cronometro"] += 1
        atualizar_tempos(st.session_state)
        atualizar_penalidades(st.session_state)
        time.sleep(1)
        st.rerun()

    st.header(f"🕒 Tempo de jogo: {st.session_state['cronometro']} s")

    col1, col2 = st.columns(2)
    for equipe, col in zip(["A", "B"], [col1, col2]):
        with col:
            st.subheader(f"Equipe {equipe}")
            df = pd.DataFrame(st.session_state["equipes"][equipe])
            st.dataframe(
                df.style.highlight_max(subset=["tempo_jogado"], color="lightgreen"),
                use_container_width=True
            )

            jogador = st.selectbox(
                f"Selecione jogador {equipe}", df["numero"], key=f"sel_{equipe}"
            )
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                if st.button("Substituir", key=f"sub_{equipe}"):
                    substituir_jogadores(st.session_state, equipe, jogador)
            with ac2:
                if st.button("2 Minutos", key=f"penal_{equipe}"):
                    aplicar_penalidade(st.session_state, equipe, jogador, tipo="2min")
            with ac3:
                if st.button("Expulsar", key=f"exp_{equipe}"):
                    aplicar_penalidade(st.session_state, equipe, jogador, tipo="expulsao")

    st.divider()
    st.subheader("⏱️ Penalidades Ativas")
    if st.session_state["penalidades"]:
        pen_df = pd.DataFrame(st.session_state["penalidades"])
        st.dataframe(pen_df)
        penal_terminada = any(p["restante"] <= 0 for p in st.session_state["penalidades"])
        if penal_terminada:
            st.toast("🔔 Penalidade encerrada!", icon="🔊")
            tocar_alarme()
    else:
        st.info("Nenhuma penalidade ativa.")

    st.divider()
    st.subheader("📊 Estatísticas de Tempo de Jogo")
    for equipe in ["A", "B"]:
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        fig = px.bar(
            df,
            x="numero",
            y=["tempo_jogado", "tempo_banco", "tempo_penalidade"],
            labels={"value": "Tempo (s)", "numero": "Jogador"},
            barmode="group",
            title=f"Equipe {equipe}"
        )
        st.plotly_chart(fig, use_container_width=True)
