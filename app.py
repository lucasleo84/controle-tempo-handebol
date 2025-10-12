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
# ABA 1 — CONFIGURAÇÃO DA EQUIPE
# (exatamente como você mandou)
# =====================================================
with abas[0]:
    st.subheader("Configuração da Equipe")

    def ensure_num_list(team_key: str, qtd: int):
        """Garante que existe uma lista editável de números por equipe e com o tamanho 'qtd'."""
        list_key = f"numeros_{team_key}"
        if list_key not in st.session_state:
            st.session_state[list_key] = [i + 1 for i in range(qtd)]
        else:
            nums = st.session_state[list_key]
            # Ajusta tamanho se usuário mudar 'qtd'
            if len(nums) < qtd:
                nums.extend(list(range(len(nums) + 1, qtd + 1)))
            elif len(nums) > qtd:
                st.session_state[list_key] = nums[:qtd]

    colA, colB = st.columns(2)

    for eq, col in zip(["A", "B"], [colA, colB]):
        with col:
            st.markdown(f"### Equipe {eq}")

            # Nome e quantidade
            nome = st.text_input(f"Nome da equipe {eq}", key=f"nome_{eq}")
            qtd = st.number_input(
                f"Quantidade de jogadores ({eq})",
                min_value=1, max_value=20, step=1,
                value=len(st.session_state["equipes"][eq]) or 7,
                key=f"qtd_{eq}"
            )

            # Garante lista de números do tamanho certo
            ensure_num_list(eq, int(qtd))

            # Editor de números (camisetas)
            st.markdown("**Números das camisetas:**")
            cols = st.columns(5)
            for i, num in enumerate(st.session_state[f"numeros_{eq}"]):
                with cols[i % 5]:
                    novo = st.number_input(
                        f"Jogador {i+1}",
                        min_value=0, max_value=999, step=1,
                        value=int(num),
                        key=f"{eq}_num_{i}"
                    )
                    st.session_state[f"numeros_{eq}"][i] = int(novo)

            # Cor da equipe
            cor = st.color_picker(
                f"Cor da equipe {eq}",
                value=st.session_state["cores"][eq],
                key=f"cor_{eq}"
            )
            st.session_state["cores"][eq] = cor

            # Salvar/registrar equipe
            if st.button(f"Salvar equipe {eq}", key=f"save_team_{eq}"):
                numeros = st.session_state[f"numeros_{eq}"]
                st.session_state["equipes"][eq] = [
                    {"numero": int(n), "estado": "banco", "elegivel": True, "exclusoes": 0}
                    for n in numeros
                ]
                st.success(f"Equipe {eq} salva com {len(numeros)} jogadores.")
                st.session_state["titulares_definidos"][eq] = False


# =====================================================
# ABA 2 — DEFINIR TITULARES
# (exatamente como você mandou)
# =====================================================
with abas[1]:
    st.subheader("Definir Titulares")

    for eq in ["A", "B"]:
        st.markdown(f"### Equipe {eq}")

        jogadores = st.session_state["equipes"][eq]
        if not jogadores:
            st.info(f"Cadastre primeiro a equipe {eq} na aba anterior.")
            continue

        numeros = [j["numero"] for j in jogadores]

        # Mostra aviso se já estiver travado
        if st.session_state["titulares_definidos"][eq]:
            st.success("Titulares já registrados. Clique em **Corrigir** para editar.")
            disabled = True
        else:
            disabled = False

        # Multiselect com os números (caixinha “adicionando um a um”)
        tit_key = f"titulares_sel_{eq}"
        titulares_sel = st.multiselect(
            "Selecione titulares (adicione um a um)",
            options=numeros,
            default=[j["numero"] for j in jogadores if j.get("estado") == "jogando"],
            key=tit_key,
            disabled=disabled
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"Registrar titulares ({eq})", key=f"registrar_tit_{eq}", disabled=disabled):
                if not titulares_sel:
                    st.error("Selecione pelo menos 1 titular.")
                else:
                    # Define estados: titulares jogando, demais banco
                    sel = set(map(int, titulares_sel))
                    for j in st.session_state["equipes"][eq]:
                        j["estado"] = "jogando" if j["numero"] in sel else "banco"
                        j["elegivel"] = True
                    st.session_state["titulares_definidos"][eq] = True
                    st.success(f"Titulares da equipe {eq} registrados.")
        with c2:
            if st.button(f"Corrigir ({eq})", key=f"corrigir_tit_{eq}"):
                st.session_state["titulares_definidos"][eq] = False
                st.info("Edição de titulares liberada.")

# =====================================================
# ABA 3 — CONTROLE DO JOGO (cronômetro 100% estável)
# =====================================================
import streamlit.components.v1 as components
import json, time

with abas[2]:
    st.subheader("Controle do Jogo")

    # Estado inicial
    if "tempo_salvo" not in st.session_state:
        st.session_state.tempo_salvo = []
    if "periodo" not in st.session_state:
        st.session_state.periodo = "1º Tempo"

    # --- Estilo fixo do cronômetro ---
    st.markdown("""
        <style>
        .cronometro-box {
            position: sticky;
            top: 0;
            background-color: #111;
            border-radius: 10px;
            padding: 10px;
            text-align: center;
            color: white;
            font-family: 'Courier New', monospace;
            z-index: 100;
        }
        .cronometro {
            font-size: 48px;
            color: #FFD700;
            text-shadow: 0 0 10px #FFD700;
            margin: 8px 0;
        }
        .btn {
            background-color: #222;
            color: white;
            border: 1px solid #555;
            padding: 6px 10px;
            margin: 4px;
            border-radius: 5px;
            cursor: pointer;
        }
        .btn:hover { background-color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # --- HTML + JavaScript do cronômetro ---
    js_html = f"""
    <div class="cronometro-box">
        <div id="cronometro" class="cronometro">00:00</div>
        <div>
            <button class="btn" onclick="iniciar()">▶️ Iniciar</button>
            <button class="btn" onclick="pausar()">⏸️ Pausar</button>
            <button class="btn" onclick="zerar()">🔁 Zerar</button>
            <button class="btn" onclick="salvar()">💾 Salvar</button>
        </div>
        <div style="margin-top:8px;">
            <label>Período:</label>
            <select id="periodo">
                <option value="1º Tempo" {'selected' if st.session_state.periodo == '1º Tempo' else ''}>1º Tempo</option>
                <option value="2º Tempo" {'selected' if st.session_state.periodo == '2º Tempo' else ''}>2º Tempo</option>
            </select>
        </div>
    </div>

    <script>
        let segundos = 0;
        let rodando = false;
        let intervalo;

        function formatar(seg) {{
            const m = String(Math.floor(seg / 60)).padStart(2, '0');
            const s = String(seg % 60).padStart(2, '0');
            return `${{m}}:${{s}}`;
        }}

        function atualizar() {{
            document.getElementById("cronometro").innerText = formatar(segundos);
        }}

        function iniciar() {{
            if (!rodando) {{
                rodando = true;
                intervalo = setInterval(() => {{
                    segundos++;
                    atualizar();
                }}, 1000);
            }}
        }}

        function pausar() {{
            rodando = false;
            clearInterval(intervalo);
        }}

        function zerar() {{
            rodando = false;
            clearInterval(intervalo);
            segundos = 0;
            atualizar();
        }}

        function salvar() {{
            const periodo = document.getElementById("periodo").value;
            const data = {{ tempo: segundos, periodo: periodo }};
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "cronometro_data";
            input.value = JSON.stringify(data);
            document.body.appendChild(input);
            document.forms[0].submit();
        }}

        atualizar();
    </script>
    """

    # Renderiza o cronômetro
    components.html(js_html, height=320)

    # Captura dados enviados (sem travar o app)
    cronometro_json = st.experimental_get_query_params().get("cronometro_data")
    if cronometro_json:
        try:
            data = json.loads(cronometro_json[0])
            st.session_state.tempo_salvo.append(data)
            st.session_state.periodo = data["periodo"]
            st.success(f"Tempo salvo: {data['tempo']} segundos ({data['periodo']})")
        except Exception:
            pass
