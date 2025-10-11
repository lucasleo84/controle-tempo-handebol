# ======================================
# CONTROLE DE JOGO - APP_v9.5 (híbrido JS + Python, sem duplo clique)
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
        "cronometro": 0.0,                      # tempo acumulado até última pausa
        "ultimo_tick": time.time(),             # epoch quando iniciou
        "iniciado": False,

        "equipes": {"A": [], "B": []},
        "penalidades": [],                      # [{'tipo':'2min','equipe':'A','jogador':'7','restante':120,'ultimo_tick':...,'ativo':True}, ...]
        "titulares_definidos": {"A": False, "B": False},
        "funcoes": {"A": {}, "B": {}},
        "invertido": False,
        "slots_abertos": {"A": 0, "B": 0},

        "cores": {"A": "#00AEEF", "B": "#EC008C"},  # Ciano/Magenta
        "sub_msg_time": {"A": 0.0, "B": 0.0},       # legenda Sai/Entra (expira em 3s)
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
def tempo_logico_atual() -> float:
    """Tempo oficial (segundos). Não altera o estado."""
    if st.session_state["iniciado"]:
        agora = time.time()
        return st.session_state["cronometro"] + (agora - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def iniciar_jogo():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()
        st.toast("⏱️ Iniciado", icon="▶️")

def pausar_jogo():
    if st.session_state["iniciado"]:
        st.session_state["cronometro"] = tempo_logico_atual()
        st.session_state["iniciado"] = False
        st.toast("⏸️ Pausado", icon="⏸️")

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
    st.toast("🔁 Zerado", icon="🔁")


# ======================================
# CRONÔMETRO VISUAL (JS) — renderizado **APÓS** os botões
# ======================================
def render_cronometro_js():
    iniciado = bool(st.session_state["iniciado"])
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if iniciado else None

    iniciado_js = "true" if iniciado else "false"
    base_elapsed_js = json.dumps(base_elapsed)
    start_epoch_js = json.dumps(start_epoch)

    html = f"""
    <div id="header-fixed">
        <div id="cronovisual" class="digital">⏱ {formato_mmss(tempo_logico_atual())}</div>
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
# BOTÕES (processados antes do render do cronômetro)
# ======================================
bc1, bc2, bc3, bc4 = st.columns([1, 1, 1, 1])
with bc1:
    if st.button("▶️ Iniciar", key="btn_start"):
        iniciar_jogo()
with bc2:
    if st.button("⏸️ Pausar", key="btn_pause"):
        pausar_jogo()
with bc3:
    if st.button("🔁 Zerar", key="btn_reset"):
        zerar_jogo()
with bc4:
    if st.button("💾 Salvar CSV", key="btn_save"):
        salvar_csv(st.session_state)
        st.success("Dados salvos com sucesso!")

# Agora sim, renderizamos o cronômetro JS com o estado **já atualizado**
render_cronometro_js()


# ======================================
# ABAS
# ======================================
tabs = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])


# ==============================================================
# ABA 1 — CONFIGURAÇÃO
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
            if st.button(f"Salvar equipe {equipe}", key=f"save_team_{equipe}"):
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
# ABA 2 — TITULARES
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
                if st.button(f"Confirmar titulares {equipe}", key=f"conf_tit_{equipe}", disabled=st.session_state["titulares_definidos"][equipe]):
                    if not titulares_sel:
                        st.error("Selecione ao menos 1 titular.")
                    else:
                        definir_titulares(st.session_state, equipe, titulares_sel)
                        st.success("Titulares definidos.")
            with c2:
                if st.button(f"Corrigir {equipe}", key=f"corr_tit_{equipe}"):
                    corrigir_titulares(st.session_state, equipe)
                    st.info("Titulares desbloqueados.")

            with st.expander("📋 Funções (opcional)", expanded=False):
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
# ABA 3 — CONTROLE DO JOGO
# ==============================================================
with tabs[2]:
    st.subheader("Controle do Jogo")
    st.toggle("🔁 Inverter lados (A↔B)", key="invertido")
    lados = ["A","B"]
    if st.session_state["invertido"]:
        lados = ["B","A"]
    col_esq, col_dir = st.columns(2)

    def painel(equipe: str):
    st.markdown(
        f"<span class='side-head' style='background:{st.session_state['cores'][equipe]};'>Equipe {equipe}</span>",
        unsafe_allow_html=True
    )

    # Listas de elegibilidade
    jogando = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"] == "jogando" and j["elegivel"]]
    banco = [j["numero"] for j in st.session_state["equipes"][equipe] if j["estado"] == "banco" and j["elegivel"]]

    # Variáveis locais (para evitar StreamlitAPIException)
    sai_key = f"sai_{equipe}"
    entra_key = f"entra_{equipe}"
    sai_val = st.session_state.get(sai_key)
    entra_val = st.session_state.get(entra_key)

    c1, c2, c3 = st.columns([1, 1, 1.1])
    sai = c1.selectbox("🟥 Sai (jogando)", [None] + sorted(jogando), key=sai_key)
    entra = c2.selectbox("🟩 Entra (banco)", [None] + sorted(banco), key=entra_key)

    # botão Substituir
    if c3.button("Substituir", key=f"substituir_{equipe}", disabled=(sai is None or entra is None or sai == entra)):
        ok, msg = efetuar_substituicao(st.session_state, equipe, [str(sai), str(entra)])
        if ok:
            # em vez de reatribuir, usamos update() seguro
            st.session_state.update({sai_key: None, entra_key: None})
            st.session_state["sub_msg_time"][equipe] = time.time()
            st.success(msg)
        else:
            st.error(msg)

    # mensagem visual de substituição (expira em 3 s)
    now = time.time()
    if now - st.session_state["sub_msg_time"][equipe] < 3:
        s = "—" if sai is None else str(sai)
        e = "—" if entra is None else str(entra)
        st.markdown(
            f"<span class='chip chip-sai'>Sai {s}</span> <span class='chip chip-entra'>Entra {e}</span>",
            unsafe_allow_html=True
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # painel de penalidades
    unico_key = f"unico_{equipe}"
    unico = st.selectbox("Jogador (2min / Expulsão / Completou)", [None] + sorted(jogando + banco), key=unico_key)
    b1, b2, b3 = st.columns(3)
    if b1.button("2 Minutos", key=f"dois_min_{equipe}", disabled=(unico is None)):
        ok, msg, terminou3 = aplicar_exclusao_2min(st.session_state, equipe, str(unico))
        if ok:
            st.warning(msg)
            if terminou3:
                st.error("Jogador inelegível (3 exclusões).")
        else:
            st.error(msg)
    if b2.button("Expulsão", key=f"expulsao_{equipe}", disabled=(unico is None)):
        ok, msg = aplicar_expulsao(st.session_state, equipe, str(unico))
        st.error(msg) if not ok else st.warning(msg)
    if b3.button("Completou", key=f"completou_{equipe}", disabled=(unico is None)):
        ok, msg = completar_substituicao(st.session_state, equipe, str(unico))
        st.success(msg) if ok else st.error(msg)

# ==============================================================
# ABA 4 — VISUALIZAÇÃO
# ==============================================================
with tabs[3]:
    st.subheader("Visualização de Dados")
    for equipe in ["A","B"]:
        st.markdown(f"### Equipe {equipe}")
        df = pd.DataFrame(st.session_state["equipes"][equipe])
        if df.empty:
            st.info("Sem dados.")
        else:
            st.dataframe(df[["numero","estado","exclusoes","elegivel"]], use_container_width=True)

    # Penalidades 2min ativas — cronômetros JS independentes
    ativos = []
    for p in st.session_state.get("penalidades", []):
        if p.get("tipo") == "2min" and p.get("ativo", True):
            restante = p.get("restante", 120)
            ativos.append({
                "equipe": p.get("equipe", "?"),
                "jogador": p.get("jogador", "?"),
                "restante": max(0, int(restante)),
            })

    if ativos:
        st.markdown("### Penalidades (2 minutos)")
        for idx, pen in enumerate(ativos, start=1):
            comp_id = f"pen_{idx}"
            html_pen = f"""
            <div id="{comp_id}" style="background:#500;padding:8px;border-radius:6px;color:#fff;margin-bottom:6px;">
              ⏳ Jogador {pen['jogador']} ({pen['equipe']}) - <span id="{comp_id}_t">{formato_mmss(pen['restante'])}</span>
            </div>
            <script>
            (function(){{
              let rest = {pen['restante']};
              const el = document.getElementById("{comp_id}_t");
              function fmt(sec){{ sec=Math.max(0,Math.floor(sec)); const m=Math.floor(sec/60),s=sec%60; return (m<10?'0':'')+m+':' + (s<10?'0':'')+s; }}
              function beep(){{ try{{ const c=new (window.AudioContext||window.webkitAudioContext)(); const o=c.createOscillator(); const g=c.createGain(); o.type='sine'; o.frequency.value=880; o.connect(g); g.connect(c.destination); g.gain.value=.1; o.start(); setTimeout(()=>{{o.stop();c.close();}},500); }}catch(e){{}} }}
              function tick(){{
                rest -= 1;
                if(rest <= 0){{ el.innerText='00:00'; clearInterval(window["{comp_id}_timer"]); beep(); }}
                else {{ el.innerText = fmt(rest); }}
              }}
              if(window["{comp_id}_timer"]) clearInterval(window["{comp_id}_timer"]);
              window["{comp_id}_timer"] = setInterval(tick, 1000);
            }})();
            </script>
            """
            components.html(html_pen, height=48)
    else:
        st.info("Nenhuma penalidade ativa.")
