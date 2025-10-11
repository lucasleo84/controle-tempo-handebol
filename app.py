import streamlit as st
import time
import pandas as pd
import streamlit.components.v1 as components
from utils.jogador import (
    formato_mmss, inicializar_equipes_se_nao_existirem,
    efetuar_substituicao, aplicar_exclusao_2min,
    aplicar_expulsao, completar_substituicao
)

# =====================================================
# 🔧 CONFIGURAÇÕES INICIAIS
# =====================================================
st.set_page_config("Controle de Jogo", layout="wide")

# Inicialização de variáveis globais
if "iniciado" not in st.session_state:
    st.session_state["iniciado"] = False
if "cronometro" not in st.session_state:
    st.session_state["cronometro"] = 0.0
if "ultimo_tick" not in st.session_state:
    st.session_state["ultimo_tick"] = time.time()
if "equipes" not in st.session_state:
    st.session_state["equipes"] = {"A": [], "B": []}
if "cores" not in st.session_state:
    st.session_state["cores"] = {"A": "#FFD700", "B": "#00BFFF"}
if "sub_msg_time" not in st.session_state:
    st.session_state["sub_msg_time"] = {"A": 0, "B": 0}

# =====================================================
# 🧭 FUNÇÕES AUXILIARES
# =====================================================

def tempo_logico_atual():
    if st.session_state["iniciado"]:
        agora = time.time()
        delta = agora - st.session_state["ultimo_tick"]
        return st.session_state["cronometro"] + delta
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

# =====================================================
# 🕹️ CRONÔMETRO (fixo + JS)
# =====================================================
def render_cronometro_js():
    """Renderiza o cronômetro JS fixo e fluido"""
    iniciado = st.session_state["iniciado"]
    base = st.session_state["cronometro"]
    base_fmt = formato_mmss(base)
    start_epoch = st.session_state["ultimo_tick"] if iniciado else None
    iniciado_js = "true" if iniciado else "false"
    base_js = f"{base:.3f}"
    start_js = "null" if start_epoch is None else f"{start_epoch:.3f}"

    html = f"""
    <div id="header-fixed">
        <div id="cronovisual" class="digital">⏱ {base_fmt}</div>
    </div>
    <script>
    (function(){{
        const el = document.getElementById('cronovisual');
        const iniciado = {iniciado_js};
        const baseElapsed = {base_js};
        const startEpoch = {start_js};
        function fmt(sec){{
            sec = Math.max(0, Math.floor(sec));
            const m = Math.floor(sec/60), s = sec%60;
            return (m<10?'0':'')+m+':'+(s<10?'0':'')+s;
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

# =====================================================
# ⚙️ INTERFACE PRINCIPAL
# =====================================================
st.title("🏐 Controle de Jogo com Registro e Alertas")
render_cronometro_js()

col1, col2, col3, col4 = st.columns(4)
col1.button("▶️ Iniciar", on_click=iniciar_jogo)
col2.button("⏸️ Pausar", on_click=pausar_jogo)
col3.button("🔁 Zerar", on_click=zerar_jogo)
col4.download_button("💾 Salvar CSV", data=b"", file_name="dados.csv")

abas = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

# =====================================================
# ⚙️ ABA 1 - CONFIGURAÇÃO
# =====================================================
with abas[0]:
    st.header("Configuração da Equipe")
    for eq in ["A", "B"]:
        nome = st.text_input(f"Nome da equipe {eq}", key=f"nome_{eq}")
        qtd = st.number_input(f"Número de jogadores - Equipe {eq}", min_value=1, max_value=20, step=1, key=f"qtd_{eq}")
        cor = st.color_picker(f"Cor da equipe {eq}", value=st.session_state["cores"][eq], key=f"cor_{eq}")
        st.session_state["cores"][eq] = cor
        if st.button(f"Registrar equipe {eq}"):
            st.session_state["equipes"][eq] = [{"numero": i + 1, "estado": "banco", "elegivel": True} for i in range(int(qtd))]
            st.success(f"Equipe {eq} configurada com {qtd} jogadores!")

# =====================================================
# ⚙️ ABA 3 - CONTROLE DO JOGO
# =====================================================
with abas[2]:
    st.header("Controle do Jogo")
    inverter = st.toggle("🔄 Inverter lados (A⇄B)", key="invert_lados")

    lados = ["A", "B"]
    if inverter:
        lados.reverse()

    c1, c2 = st.columns(2)
    with c1:
        if st.session_state["equipes"]["A"]:
            painel_equipe = "A" if not inverter else "B"
            painel_equipe_render = painel_equipe
            st.markdown(f"<h5 style='color:{st.session_state['cores'][painel_equipe]};'>Equipe {painel_equipe}</h5>", unsafe_allow_html=True)
            painel(painel_equipe)
    with c2:
        if st.session_state["equipes"]["B"]:
            painel_equipe = "B" if not inverter else "A"
            painel_equipe_render = painel_equipe
            st.markdown(f"<h5 style='color:{st.session_state['cores'][painel_equipe]};'>Equipe {painel_equipe}</h5>", unsafe_allow_html=True)
            painel(painel_equipe)

# =====================================================
# ⚙️ ABA 4 - VISUALIZAÇÃO DE DADOS
# =====================================================
with abas[3]:
    st.header("Visualização e Controle de Ações")
    if any(st.session_state["equipes"][eq] for eq in ["A", "B"]):
        dados = []
        for eq in ["A", "B"]:
            for j in st.session_state["equipes"][eq]:
                dados.append({
                    "Equipe": eq,
                    "Número": j["numero"],
                    "Estado": j["estado"],
                    "Elegível": j["elegivel"],
                    "Exclusões": j.get("exclusoes", 0)
                })
        st.dataframe(pd.DataFrame(dados))
    else:
        st.info("Configure as equipes primeiro.")
