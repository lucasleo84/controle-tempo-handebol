# ======================================
# CONTROLE DE JOGO - APP_V8.PY
# ======================================
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
    aplicar_exclusao_2min,
    aplicar_expulsao,
    efetuar_substituicao,
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
        "cronometro": 0,                # em segundos
        "ultimo_tick": time.time(),
        "equipes": {"A": [], "B": []},
        "penalidades": [],
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "invertido": False,             # A<->B na tela
    })

inicializar_equipes_se_nao_existirem(st.session_state)

# ================================
#   CSS FIXO E ESTILO
# ================================
st.markdown(
    """
    <style>
    /* espaço pro cabeçalho padrão do Streamlit */
    .block-container { padding-top: 130px; }

    /* Cronômetro fixo */
    #header-fixed {
        position: sticky;
        top: 0;
        background-color: #ffffff;
        border-bottom: 2px solid #ddd;
        text-align: center;
        padding: 4px 0;
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

    /* Abas fixas logo abaixo do cronômetro */
    .tabs-fixed { position: sticky; top: 50px; background: #fff; z-index: 9998; }

    /* chips de legenda */
    .chip { display:inline-flex; align-items:center; gap:.5rem; padding:.25rem .5rem; border-radius:999px; font-weight:700; color:#fff; }
    .chip-sai   { background:#ff4b4b; }
    .chip-entra { background:#1aa260; }

    /* cabeçalhos de coluna */
    .side-head { font-weight:800; font-size:1.1rem; padding:.35rem .6rem; border-radius:8px; color:#fff; display:inline-block; }
    .side-A { background:#3B82F6; }   /* azul */
    .side-B { background:#EF4444; }   /* vermelho */

    /* divisória */
    hr { border:0; height:1px; background:#e4e4e7; margin:12px 0; }
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
        if atualizar_penalidades(st.session_state):
            st.toast("🔔 Penalidade encerrada!", icon="🔊")
            tocar_alarme()

tick_cronometro()

# ================================
#   HEADER FIXO (CRONÔMETRO)
# ================================
st.markdown(
    f"""
    <div id="header-fixed">
        <div class="digital">⏱ {formato_mmss(st.session_state['cronometro'])}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ================================
#   CONTROLES GERAIS
# ================================
c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
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
        st.session_state["cronometro"] = 0
        st.session_state["ultimo_tick"] = time.time()
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
with c5:
    st.toggle("🔁 Inverter lados (A↔B)", key="invertido")

# ================================
#   ABAS
# ================================
tabs = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização de Dados"
])

# ==============================================================
# ABA 1 — CONFIGURAÇÃO
# ==============================================================
with tabs[0]:
    st.subheader("Configuração da Equipe")
    colA, colB = st.columns(2)
    for equipe, col in zip(["A","B"], [colA,colB]):
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
# ABA 2 — TITULARES + FUNÇÕES
# ==============================================================
with tabs[1]:
    st.subheader("Definição de Titulares e Funções")
    for equipe in ["A","B"]:
        with st.expander(f"⚙️ Configurar equipe {equipe}", expanded=False):
            st.markdown(f"**Equipe {equipe}** — {st.session_state.get(f'nome_{equipe}_salvo','') or 'Sem nome'}")
            nums = [j["numero"] for j in st.session_state["equipes"][equipe]]
            titulares_sel = st.multiselect(
                "Selecione titulares (obrigatório)",
                options=nums,
                disabled=st.session_state["titulares_definidos"][equipe],
                key=f"tit_{equipe}"
            )
            cta1, cta2 = st.columns(2)
            with cta1:
                if st.button(f"Confirmar titulares {equipe}", disabled=st.session_state["titulares_definidos"][equipe]):
                    if not titulares_sel:
                        st.error("Selecione ao menos 1 titular.")
                    else:
                        definir_titulares(st.session_state, equipe, titulares_sel)
                        st.success("Titulares definidos e travados.")
            with cta2:
                if st.button(f"Corrigir {equipe}"):
                    corrigir_titulares(st.session_state, equipe)
                    st.info("Titulares desbloqueados para edição.")

        with st.expander(f"📋 Funções (opcional) — {equipe}", expanded=False):
            posicoes = ["Goleiro","Pivô","Ponta Esquerda","Armação Esquerda","Armação Central","Armação Direita","Ponta Direita"]
            titulares = [j for j in st.session_state["equipes"][equipe] if j["estado"]=="jogando"]
            if not titulares:
                st.info("Defina titulares para atribuir funções.")
            else:
                for j in titulares:
                    atual = st.session_state["funcoes"][equipe].get(j["numero"])
                    val = st.selectbox(
                        f"#{j['numero']}",
                        options=["(sem função)"]+posicoes,
                        index=0 if atual is None else (["(sem função)"]+posicoes).index(atual),
                        key=f"func_{equipe}_{j['numero']}"
                    )
                    set_posicao_titular(st.session_state, equipe, j["numero"], None if val=="(sem função)" else val)

# ==============================================================
# ABA 3 — CONTROLE DO JOGO (lado a lado + inverter)
# ==============================================================
with tabs[2]:
    st.subheader("Controle do Jogo")

    # Decide ordem visual A|B ou B|A
    lados = ["A","B"]
    if st.session_state["invertido"]:
        lados = ["B","A"]

    col_esq, col_dir = st.columns(2)

    def painel_controle_equipe(equipe: str):
        # Cabeçalho de lado
        st.markdown(
            f"<span class='side-head side-{equipe}'>Equipe {equipe}</span>",
            unsafe_allow_html=True
        )

        # Listas restritas
        jogando = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"]=="jogando" and j["elegivel"]]
        banco   = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"]=="banco" and j["elegivel"]]

        c1, c2 = st.columns([1,1])
        with c1:
            sai = st.selectbox("🟥 Sai", options=([None]+jogando), index=0, key=f"sai_{equipe}")
        with c2:
            entra = st.selectbox("🟩 Entra", options=([None]+banco), index=0, key=f"entra_{equipe}")

        # Legenda
        leg = []
        if sai is not None:
            leg.append(f"<span class='chip chip-sai'>Sai {sai}</span>")
        if entra is not None:
            leg.append(f"<span class='chip chip-entra'>Entra {entra}</span>")
        if leg:
            st.markdown(" ".join(leg), unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Jogador único para penalidades / completou
        unico = st.selectbox("Jogador (2min / Expulsão / Completou)", options=[None]+jogando+banco, index=0, key=f"unico_{equipe}")

        # Botões
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            disabled = (sai is None) or (entra is None) or (sai == entra)
            if st.button("Substituir", key=f"btn_sub_{equipe}", disabled=disabled):
                ok, msg = efetuar_substituicao(st.session_state, equipe, [str(sai), str(entra)])
                st.success(msg) if ok else st.error(msg)

        with b2:
            if st.button("2 Minutos", key=f"btn_2min_{equipe}", disabled=(unico is None)):
                ok, msg, terminou3 = aplicar_exclusao_2min(st.session_state, equipe, str(unico))
                if ok:
                    st.warning(msg)
                    if terminou3:
                        st.error("Jogador inelegível (3 exclusões).")
                else:
                    st.error(msg)

        with b3:
            if st.button("Expulsão", key=f"btn_exp_{equipe}", disabled=(unico is None)):
                ok, msg = aplicar_expulsao(st.session_state, equipe, str(unico))
                st.error(msg) if ok else st.error(msg)

        with b4:
            if st.button("Completou", key=f"btn_comp_{equipe}", disabled=(unico is None)):
                ok, msg = completar_substituicao(st.session_state, equipe, str(unico))
                st.success(msg) if ok else st.error(msg)

    with col_esq:
        painel_controle_equipe(lados[0])
    with col_dir:
        painel_controle_equipe(lados[1])

# ==============================================================
# ABA 4 — VISUALIZAÇÃO (tabelas)
# ==============================================================
with tabs[3]:
    st.subheader("Visualização de Dados")
    for equipe in ["A","B"]:
        st.markdown(f"### Equipe {equipe}")
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        if df.empty:
            st.info("Equipe vazia.")
            continue
        st.dataframe(df[["numero","estado","exclusoes","elegivel"]], use_container_width=True)

        ativos = [p for p in st.session_state["penalidades"] if p["equipe"]==equipe]
        if ativos:
            st.markdown("#### Penalidades Ativas")
            pen_rows = []
            for p in ativos:
                pen_rows.append({
                    "Jogador": f"{p['jogador']}",
                    "Tipo": "2min" if p["tipo"]=="2min" else "Expulsão",
                    "Restante": formato_mmss(p["restante"])
                })
            st.dataframe(pd.DataFrame(pen_rows), use_container_width=True)
        else:
            st.info("Nenhuma penalidade ativa.")
