import streamlit as st
import time
import json
import streamlit.components.v1 as components

# =====================================================
# 🔧 Inicialização de estado
# =====================================================
if "equipes" not in st.session_state:
    st.session_state["equipes"] = {"A": [], "B": []}
if "cores" not in st.session_state:
    st.session_state["cores"] = {"A": "#00AEEF", "B": "#EC008C"}
if "titulares_definidos" not in st.session_state:
    st.session_state["titulares_definidos"] = {"A": False, "B": False}

# --- estado do cronômetro (lógico) ---
# cron_base: segundos acumulados até a última pausa
# cron_running: se está rodando
# cron_start_epoch: time.time() do último "iniciar" (para calcular o tempo corrente)
if "cron_base" not in st.session_state:
    st.session_state["cron_base"] = 0.0
if "cron_running" not in st.session_state:
    st.session_state["cron_running"] = False
if "cron_start_epoch" not in st.session_state:
    st.session_state["cron_start_epoch"] = None
if "periodo" not in st.session_state:
    st.session_state["periodo"] = "1º Tempo"

# =====================================================
# 🧭 Criação das abas
# =====================================================
abas = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização de Dados"
])

# =====================================================
# Helpers do cronômetro
# =====================================================
def tempo_logico_atual() -> float:
    """Retorna o tempo total (segundos) sem alterar o estado."""
    if st.session_state["cron_running"] and st.session_state["cron_start_epoch"]:
        agora = time.time()
        return st.session_state["cron_base"] + (agora - st.session_state["cron_start_epoch"])
    return st.session_state["cron_base"]

def iniciar():
    if not st.session_state["cron_running"]:
        st.session_state["cron_running"] = True
        st.session_state["cron_start_epoch"] = time.time()
        st.toast("⏱️ Iniciado", icon="▶️")

def pausar():
    if st.session_state["cron_running"]:
        # consolida o tempo
        st.session_state["cron_base"] = tempo_logico_atual()
        st.session_state["cron_running"] = False
        st.session_state["cron_start_epoch"] = None
        st.toast("⏸️ Pausado", icon="⏸️")

def zerar():
    st.session_state["cron_running"] = False
    st.session_state["cron_base"] = 0.0
    st.session_state["cron_start_epoch"] = None
    st.toast("🔁 Zerado", icon="🔁")

def fmt_mmss(seg):
    seg = int(max(0, seg))
    m, s = divmod(seg, 60)
    return f"{m:02d}:{s:02d}"

def render_cronometro_js():
    """Renderiza cronômetro visual suave (JS), sincronizado com o lógico."""
    iniciado = st.session_state["cron_running"]
    base_elapsed = float(st.session_state["cron_base"])
    start_epoch = float(st.session_state["cron_start_epoch"]) if iniciado and st.session_state["cron_start_epoch"] else None

    base_js = json.dumps(base_elapsed)     # p.ex. 123.45
    start_js = json.dumps(start_epoch)     # p.ex. 1712345678.12 ou null
    iniciado_js = "true" if iniciado else "false"
    inicial_fmt = fmt_mmss(tempo_logico_atual())

    html = f"""
    <div style="text-align:center; margin-top:4px;">
      <span id="cronovisual" style="
        font-family: 'Courier New', monospace;
        font-size: 36px;
        font-weight: bold;
        color: #FFD700;
        background:#000; padding:8px 18px; border-radius:8px;
        display:inline-block; letter-spacing:2px;
        box-shadow: 0 0 8px rgba(255,215,0,.45);
      ">⏱ {inicial_fmt}</span>
    </div>
    <script>
    (function(){{
        const el = document.getElementById('cronovisual');
        const iniciado = {iniciado_js};
        const baseElapsed = {base_js};
        const startEpoch = {start_js};
        function fmt(sec) {{
            sec = Math.max(0, Math.floor(sec));
            const m = Math.floor(sec/60), s = sec%60;
            return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
        }}
        function tick(){{
            let elapsed = baseElapsed;
            if (iniciado && startEpoch) {{
                const now = Date.now()/1000;
                elapsed = baseElapsed + (now - startEpoch);
            }}
            el.textContent = '⏱ ' + fmt(elapsed);
        }}
        tick();
        if (window.__cronovisual_timer) clearInterval(window.__cronovisual_timer);
        window.__cronovisual_timer = setInterval(tick, 250);
    }})();
    </script>
    """
    components.html(html, height=70)

# =====================================================
# ABA 3 — CONTROLE DO JOGO (equipes lado a lado + cronômetro JS)
# =====================================================
import streamlit.components.v1 as components

# ---------------------- Inicialização Segura ----------------------
if "iniciado" not in st.session_state:
    st.session_state.iniciado = False
if "cronometro" not in st.session_state:
    st.session_state.cronometro = 0.0
if "ultimo_tick" not in st.session_state:
    st.session_state.ultimo_tick = 0.0
if "invertido" not in st.session_state:
    st.session_state.invertido = False

# ---------------------- Funções Auxiliares ----------------------
def atualizar_estado(eq, numero, novo_estado):
    for j in st.session_state["equipes"][eq]:
        if j["numero"] == numero:
            j["estado"] = novo_estado
            return

def jogadores_por_estado(eq, estado):
    return [j["numero"] for j in st.session_state["equipes"][eq]
            if j["estado"] == estado and j["elegivel"]]

# ---------------------- Cronômetro Principal (JS) ----------------------
def render_cronometro_js():
    iniciado = "true" if st.session_state["iniciado"] else "false"
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if st.session_state["iniciado"] else None

    st.markdown("""
        <style>
        .cronofixo {
            position: sticky; top: 0; z-index: 999; text-align:center;
            background:#111; border-bottom:2px solid #FFD700;
            padding:6px 0 10px 0;
        }
        .digital {
            font-family:'Courier New', monospace; font-size:36px; font-weight:bold;
            color:#FFD700; background:#000; padding:6px 20px; border-radius:8px;
            display:inline-block; letter-spacing:2px;
            box-shadow:0 0 10px rgba(255,215,0,.7);
        }
        .btn-painel{
            display:inline-block; background:#222; color:white; border:1px solid #555;
            padding:4px 10px; margin:2px; border-radius:5px; cursor:pointer;
            font-size:13px;
        }
        .btn-painel:hover{ background:#333; }
        </style>
    """, unsafe_allow_html=True)

    html = f"""
    <div class="cronofixo">
        <div id="cronovisual" class="digital">⏱ 00:00</div><br>
        <button class="btn-painel" onclick="iniciar()">▶️ Iniciar</button>
        <button class="btn-painel" onclick="pausar()">⏸️ Pausar</button>
        <button class="btn-painel" onclick="zerar()">🔁 Zerar</button>
    </div>

    <script>
      let segundos = {base_elapsed};
      let rodando = {iniciado};
      let startEpoch = {json.dumps(start_epoch)};
      let timer = null;

      function fmt(sec){{
        sec = Math.max(0, Math.floor(sec));
        const m = Math.floor(sec/60), s = sec % 60;
        return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
      }}

      function atualizar(){{
        document.getElementById("cronovisual").innerText = '⏱ ' + fmt(segundos);
      }}

      function tick(){{
        if(rodando && startEpoch){{
          const agora = Date.now()/1000;
          segundos = {base_elapsed} + (agora - startEpoch);
          atualizar();
        }}
      }}

      function iniciar(){{
        if(!rodando){{
          rodando = true;
          startEpoch = Date.now()/1000;
        }}
      }}

      function pausar(){{
        if(rodando){{
          const agora = Date.now()/1000;
          segundos = {base_elapsed} + (agora - startEpoch);
          rodando = false;
          atualizar();
        }}
      }}

      function zerar(){{
        rodando = false;
        segundos = 0;
        atualizar();
      }}

      atualizar();
      if(window.__cronovisual_timer) clearInterval(window.__cronovisual_timer);
      window.__cronovisual_timer = setInterval(tick, 250);
    </script>
    """
    components.html(html, height=120)

# ---------------------- Cronômetro 2 minutos ----------------------
def render_cronometro_exclusao():
    html = """
    <div style="text-align:center;">
      <div id="exclusao" style="font-family:'Courier New';font-size:18px;color:#FF3333;
        background:#111;padding:4px 8px;border-radius:6px;display:inline-block;
        text-shadow:0 0 10px red;">⏱ 02:00</div>
    </div>
    <audio id="alarme" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg"></audio>
    <script>
      let t = 120;
      const el = document.getElementById('exclusao');
      const beep = document.getElementById('alarme');
      const timer = setInterval(() => {
        t--;
        const m = String(Math.floor(t/60)).padStart(2,'0');
        const s = String(t%60).padStart(2,'0');
        el.textContent = '⏱ ' + m + ':' + s;
        if (t <= 0) {
          clearInterval(timer);
          el.textContent = '✅ Tempo cumprido';
          beep.play();
        }
      }, 1000);
    </script>
    """
    components.html(html, height=90)

# ---------------------- Painel de cada equipe ----------------------
def painel(eq, cor):
    st.markdown(
        f"<h4 style='text-align:center; color:{cor}; margin-bottom:6px;'>Equipe {eq}</h4>",
        unsafe_allow_html=True
    )

    jogando = jogadores_por_estado(eq, "jogando")
    banco = jogadores_por_estado(eq, "banco")
    excluidos = jogadores_por_estado(eq, "excluido")

    col1, col2, col3 = st.columns([1, 1, 1])

    # Substituição
    with col1:
        st.markdown("**🔁 Substituição**")
        sai = st.selectbox("Sai", jogando, key=f"sai_{eq}")
        entra = st.selectbox("Entra", banco, key=f"entra_{eq}")
        if st.button("Confirmar", key=f"sub_{eq}"):
            if sai and entra:
                atualizar_estado(eq, sai, "banco")
                atualizar_estado(eq, entra, "jogando")
                st.success(f"Sai {sai}, Entra {entra}")

    # 2 minutos + Completou
    with col2:
        st.markdown("**⏱ 2 minutos**")
        jogador_ex = st.selectbox("Jogador", jogando, key=f"exc_{eq}")
        if st.button("Aplicar", key=f"btn_exc_{eq}"):
            if jogador_ex:
                atualizar_estado(eq, jogador_ex, "excluido")
                st.warning(f"{jogador_ex} fora por 2 minutos")
                render_cronometro_exclusao()

        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
        st.markdown("**✅ Completou / Retorna**")
        elegiveis = jogadores_por_estado(eq, "excluido") + jogadores_por_estado(eq, "banco")
        jogador_comp = st.selectbox("Jogador que retorna", elegiveis, key=f"comp_{eq}")
        if st.button("Confirmar Retorno", key=f"btn_comp_{eq}"):
            if jogador_comp:
                atualizar_estado(eq, jogador_comp, "jogando")
                st.success(f"{jogador_comp} voltou ao jogo")

    # Expulsão
    with col3:
        st.markdown("**🟥 Expulsão**")
        jogador_exp = st.selectbox("Jogador", jogando + banco + excluidos, key=f"exp_{eq}")
        if st.button("Expulsar", key=f"btn_exp_{eq}"):
            if jogador_exp:
                atualizar_estado(eq, jogador_exp, "expulso")
                for j in st.session_state["equipes"][eq]:
                    if j["numero"] == jogador_exp:
                        j["elegivel"] = False
                st.error(f"{jogador_exp} expulso do jogo!")

# ---------------------- Renderização da Aba ----------------------
with abas[2]:
    st.subheader("Controle do Jogo")

    # Botão de inverter lados
    if st.button("🔄 Inverter Lados"):
        st.session_state.invertido = not st.session_state.invertido

    # Cronômetro fixo com botões
    render_cronometro_js()
    st.markdown("<br>", unsafe_allow_html=True)

    # Cores e colunas
    cor_a = st.session_state["cores"].get("A", "#1976D2")
    cor_b = st.session_state["cores"].get("B", "#D32F2F")

    if not st.session_state.invertido:
        colA, colB = st.columns(2)
        with colA:
            painel("A", cor_a)
        with colB:
            painel("B", cor_b)
    else:
        colB, colA = st.columns(2)
        with colB:
            painel("B", cor_b)
        with colA:
            painel("A", cor_a)

