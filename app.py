# ======================================
# CONTROLE DE JOGO - APP.PY (v3)
# Estável no Streamlit Cloud + cronômetro digital automático
# ======================================

import os
# 🔒 tornar o Cloud estável (evita loops por file watcher)
os.environ["WATCHDOG_MAX_INSTANCES"] = "0"
os.environ["STREAMLIT_WATCHDOG"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import streamlit as st
import pandas as pd
import time
import sys

# Caminho para módulos locais
import os as _os
sys.path.append(_os.path.join(_os.path.dirname(__file__), "utils"))

# ====== Funções utilitárias da sua camada de regras ======
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
        "cronometro": 0,            # segundos
        "ultimo_tick": time.time(), # controle do relógio
        "equipes": {"A": [], "B": []},
        "penalidades": [],          # [{equipe, jogador, tipo, inicio, restante}]
        "slots_abertos": {"A": 0, "B": 0},
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "dark_mode": True           # começa escuro para combinar com relógio
    })

inicializar_equipes_se_nao_existirem(st.session_state)

# ================================
#   ESTILO / TEMA
# ================================
def aplicar_css():
    dark = st.session_state["dark_mode"]
    bg = "#0b0b0f" if dark else "#ffffff"
    fg = "#e6edf3" if dark else "#111111"
    border = "#242833" if dark else "#e9ecef"

    st.markdown(
        f"""
        <style>
        body {{
            background-color: {bg};
            color: {fg};
        }}
        /* Header do timer fixo e centralizado */
        #sticky-timer {{
            position: sticky;
            top: 0;
            z-index: 999;
            padding: 10px 0;
            background: linear-gradient(180deg, {bg}F2 70%, {bg} 100%);
            backdrop-filter: blur(6px);
            border-bottom: 1px solid {border};
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .digital {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
                         "Courier New", monospace;
            font-weight: 800;
            font-size: 28px;
            letter-spacing: 2px;
            color: #FFD700;              /* amarelo digital */
            background: #000000;         /* fundo escuro */
            padding: 8px 16px;
            border-radius: 10px;
            border: 1px solid #3a3f48;
            text-shadow: 0 0 6px rgba(255, 215, 0, 0.8), 0 0 12px rgba(255, 215, 0, 0.3);
        }}
        .chip {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid {border};
            font-weight: 600;
            opacity: 0.9;
        }}
        .penal {{
            color: #fff;
            background: #8B0000; /* darkred */
            border-color: #a11a1a;
        }}
        .muted {{
            opacity: .85;
        }}
        /* Ajuste das tabelas */
        section[data-testid="stDataFrame"] div[data-testid="stTable"] {{
            background: {bg};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_css()

# ================================
#   RELOGIO AUTOMÁTICO
# ================================
def tick_cronometro():
    """
    Avança o cronômetro automaticamente, de forma estável no Cloud:
     - calcula quantos segundos passaram desde o último tick
     - aplica em lotes (cap de 5s) para não travar
     - atualiza tempos e penalidades
    """
    if not st.session_state["iniciado"]:
        return

    agora = time.time()
    dt = int(agora - st.session_state["ultimo_tick"])
    if dt <= 0:
        return

    # evita saltos muito grandes se a aba ficar inativa
    dt = min(dt, 5)

    for _ in range(dt):
        st.session_state["cronometro"] += 1
        st.session_state["ultimo_tick"] += 1
        atualizar_tempos(st.session_state)
        terminou = atualizar_penalidades(st.session_state)
        if terminou:
            st.toast("🔔 Penalidade encerrada!", icon="🔊")
            tocar_alarme()

# Executa o tick a cada render
tick_cronometro()

# ================================
#   HEADER FIXO (TIMER + MODO)
# ================================
with st.container():
    st.markdown(
        f"""
        <div id="sticky-timer">
            <div class="digital">⏱ {formato_mmss(st.session_state['cronometro'])}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

top1, top2, top3, top4, top5 = st.columns([1,1,1,1,2])
with top1:
    if st.button("▶️ Iniciar"):
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()
with top2:
    if st.button("⏸️ Pausar"):
        st.session_state["iniciado"] = False
with top3:
    if st.button("🔁 Zerar"):
        st.session_state["cronometro"] = 0
        st.session_state["ultimo_tick"] = time.time()
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
            st.session_state["slots_abertos"][eq] = 0
        st.session_state["penalidades"] = []
        st.session_state["titulares_definidos"] = {"A": False, "B": False}
        st.session_state["funcoes"] = {"A": {}, "B": {}}
with top4:
    if st.button("💾 Salvar CSV"):
        salvar_csv(st.session_state)
        st.success("Dados salvos em dados/saida_jogo.csv")
with top5:
    st.toggle("Modo noturno", key="dark_mode", value=st.session_state["dark_mode"])
    # reaplica CSS ao alternar
    aplicar_css()

# ================================
#   ABAS
# ================================
tabs = st.tabs([
    "Configuração da Equipe",
    "Controle do Jogo",
    "Visualização de Dados"
])

# ==============================================================
# ABA 1 — CONFIGURAÇÃO DA EQUIPE (nome → qtd → números)
# ==============================================================
with tabs[0]:
    st.subheader("Configuração da Equipe")

    colA, colB = st.columns(2)
    for equipe, col in zip(["A", "B"], [colA, colB]):
        with col:
            st.markdown(f"### Equipe {equipe}")
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
# ABA 2 — CONTROLE DO JOGO
# ==============================================================
with tabs[1]:
    st.subheader("Definir Titulares (obrigatório)")
    boxA, boxB = st.columns(2)
    for equipe, box in zip(["A","B"], [boxA, boxB]):
        with box:
            st.markdown(f"**Equipe {equipe}** — {st.session_state.get(f'nome_{equipe}_salvo','') or 'Sem nome'}")
            nums = [j["numero"] for j in st.session_state["equipes"][equipe]]
            titulares_sel = st.multiselect(
                "Selecione titulares",
                options=nums,
                disabled=st.session_state["titulares_definidos"][equipe],
                key=f"tit_{equipe}"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Confirmar {equipe}", disabled=st.session_state["titulares_definidos"][equipe]):
                    if len(titulares_sel) == 0:
                        st.error("Selecione ao menos 1 titular.")
                    else:
                        definir_titulares(st.session_state, equipe, titulares_sel)
                        st.success("Titulares definidos e travados.")
            with c2:
                if st.button(f"Corrigir {equipe}"):
                    corrigir_titulares(st.session_state, equipe)
                    st.info("Titulares desbloqueados para edição.")

    st.divider()
    st.subheader("Função dos jogadores (opcional)")
    posicoes = ["Goleiro","Pivô","Ponta Esquerda","Armação Esquerda","Armação Central","Armação Direita","Ponta Direita"]
    fA, fB = st.columns(2)
    for equipe, box in zip(["A","B"], [fA, fB]):
        with box:
            titulares = [j for j in st.session_state["equipes"][equipe] if j["estado"] == "jogando"]
            if not titulares:
                st.info("Defina titulares para atribuir funções.")
            else:
                for j in titulares:
                    current = st.session_state["funcoes"][equipe].get(j["numero"])
                    val = st.selectbox(
                        f"#{j['numero']}",
                        options=["(sem função)"] + posicoes,
                        index=0 if current is None else (["(sem função)"]+posicoes).index(current),
                        key=f"func_{equipe}_{j['numero']}"
                    )
                    set_posicao_titular(st.session_state, equipe, j["numero"], None if val=="(sem função)" else val)

    st.divider()
    st.subheader("Controle de Tempo — Painel Único por Equipe")

    def painel_controle_equipe(equipe: str):
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        st.markdown(f"### Equipe {equipe}")
        st.dataframe(df[["numero", "estado", "exclusoes", "elegivel"]], use_container_width=True)

        sel = st.multiselect(
            f"Selecionar jogador(es) {equipe} (1 para 2min/Expulsão/Completou, 2 para Substituir)",
            options=list(df["numero"]),
            key=f"sel_unificado_{equipe}"
        )

        # Regras de habilitação
        can_sub = (len(sel) == 2) and pode_substituir(st.session_state, equipe, sel)
        can_one = (len(sel) == 1) and pode_penalizar(st.session_state, equipe, sel[0])
        can_comp = (len(sel) == 1) and pode_completar(st.session_state, equipe, sel[0])

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Substituir", key=f"do_sub_{equipe}", disabled=not can_sub):
                ok, msg = efetuar_substituicao(st.session_state, equipe, sel)
                st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("2 Minutos", key=f"do_2min_{equipe}", disabled=not can_one):
                ok, msg, virou_inelegivel = aplicar_exclusao_2min(st.session_state, equipe, sel[0])
                if ok:
                    st.warning(msg)
                    if virou_inelegivel:
                        st.error("Jogador inelegível (3 exclusões).")
                else:
                    st.error(msg)
        with b3:
            if st.button("Expulsão", key=f"do_exp_{equipe}", disabled=not can_one):
                ok, msg = aplicar_expulsao(st.session_state, equipe, sel[0])
                st.error(msg) if ok else st.error(msg)
        with b4:
            if st.button("Completou", key=f"do_comp_{equipe}", disabled=not can_comp):
                ok, msg = completar_substituicao(st.session_state, equipe, sel[0])
                st.success(msg) if ok else st.error(msg)

        # Painel de penalidades com cronômetro regressivo vermelho
        st.markdown("#### Penalidades ativas")
        ativos = [p for p in st.session_state["penalidades"] if p["equipe"] == equipe]
        if not ativos:
            st.info("Nenhuma penalidade ativa.")
        else:
            # tabela com contagem regressiva em MM:SS
            pen_rows = []
            for p in ativos:
                pen_rows.append({
                    "Jogador": f"#{p['jogador']}",
                    "Tipo": "2 min" if p["tipo"] == "2min" else "Expulsão",
                    "Restante": formato_mmss(p["restante"])
                })
            st.dataframe(pd.DataFrame(pen_rows), use_container_width=True)
            # barra de progresso visual em vermelho
            for p in ativos:
                perc = max(0.0, min(1.0, (120 - p["restante"]) / 120))
                st.markdown(f"<span class='chip penal'> #{p['jogador']} — {formato_mmss(p['restante'])}</span>", unsafe_allow_html=True)
                st.progress(perc)

    colA2, colB2 = st.columns(2)
    with colA2:
        painel_controle_equipe("A")
    with colB2:
        painel_controle_equipe("B")

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
        viz["tempo_jogado (min)"]    = (viz["tempo_jogado"]    / 60).round(2)
        viz["tempo_banco (min)"]     = (viz["tempo_banco"]     / 60).round(2)
        viz["tempo_2min (min)"]      = (viz["tempo_penalidade"]/ 60).round(2)
        st.dataframe(
            viz[["numero","estado","exclusoes","elegivel",
                 "tempo_jogado (min)","tempo_banco (min)","tempo_2min (min)"]],
            use_container_width=True
        )
