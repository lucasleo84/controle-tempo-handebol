import streamlit as st
import time

# =====================================================
# 🔧 Inicialização de estado
# =====================================================
if "equipes" not in st.session_state:
    st.session_state["equipes"] = {"A": [], "B": []}
if "cores" not in st.session_state:
    st.session_state["cores"] = {"A": "#00AEEF", "B": "#EC008C"}
if "titulares_definidos" not in st.session_state:
    st.session_state["titulares_definidos"] = {"A": False, "B": False}

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
# ABA 1 — CONFIGURAÇÃO DA EQUIPE
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
    if st.button("🔄 Inverter Lados", key="invert_lados_main"):
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
# =====================================================
# ABA 3 — CONTROLE DO JOGO (sem conflitos, usando o cronômetro do topo)
# =====================================================

# ⬇️ Helpers específicos desta aba (não conflitam com os do topo)
def atualizar_estado(eq: str, numero: int, novo_estado: str):
    """Altera o estado do jogador (jogando/banco/excluido/expulso)."""
    for j in st.session_state["equipes"][eq]:
        if j["numero"] == numero:
            j["estado"] = novo_estado
            return

def jogadores_por_estado(eq: str, estado: str):
    """Lista de números de jogadores por estado, apenas elegíveis."""
    return [
        j["numero"]
        for j in st.session_state["equipes"][eq]
        if j.get("estado") == estado and j.get("elegivel", True)
    ]

def aplicar_exclusao(eq: str, numero: int):
    """Marca exclusão (2 min). Soma contagem e expulsa ao atingir 3."""
    for j in st.session_state["equipes"][eq]:
        if j["numero"] == numero:
            j["estado"] = "excluido"
            j["exclusoes"] = int(j.get("exclusoes", 0)) + 1
            # expulsão automática com 3 exclusões
            if j["exclusoes"] >= 3:
                j["estado"] = "expulso"
                j["elegivel"] = False
            return

def render_cronometro_exclusao():
    """Cronômetro regressivo de 2 minutos com alerta sonoro (visual JS)."""
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
          try { beep.play(); } catch(e) {}
        }
      }, 1000);
    </script>
    """
    components.html(html, height=90)

def painel_equipe(eq: str, cor: str):
    st.markdown(
        f"<h4 style='text-align:center; color:{cor}; margin-bottom:6px;'>Equipe {eq}</h4>",
        unsafe_allow_html=True
    )

    jogando  = jogadores_por_estado(eq, "jogando")
    banco    = jogadores_por_estado(eq, "banco")
    excluido = jogadores_por_estado(eq, "excluido")

    c1, c2, c3 = st.columns([1, 1, 1])

    # 🔁 Substituição
    with c1:
        st.markdown("**🔁 Substituição**")
        sai   = st.selectbox("Sai", jogando, key=f"sai_{eq}")
        entra = st.selectbox("Entra", banco,   key=f"entra_{eq}")
        if st.button("Confirmar", key=f"sub_{eq}"):
            if sai and entra:
                atualizar_estado(eq, sai,   "banco")
                atualizar_estado(eq, entra, "jogando")
                st.success(f"Sai {sai}, Entra {entra}")

    # ⏱ 2 minutos + ✅ Completou
    with c2:
        st.markdown("**⏱ 2 minutos**")
        jog_exc = st.selectbox("Jogador", jogando, key=f"exc_{eq}")
        if st.button("Aplicar", key=f"btn_exc_{eq}"):
            if jog_exc:
                aplicar_exclusao(eq, jog_exc)
                # se chegou a 3, já foi expulso; caso contrário, 2 minutos visual
                j = next((x for x in st.session_state["equipes"][eq] if x["numero"] == jog_exc), None)
                if j and j.get("estado") == "expulso":
                    st.error(f"{jog_exc} expulso (3 exclusões).")
                else:
                    st.warning(f"{jog_exc} fora por 2 minutos")
                    render_cronometro_exclusao()

        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
        st.markdown("**✅ Completou / Retorna**")
        elegiveis_retorno = excluido + banco  # agora pode escolher excluído OU banco
        jog_ret = st.selectbox("Jogador que retorna", elegiveis_retorno, key=f"comp_{eq}")
        if st.button("Confirmar Retorno", key=f"btn_comp_{eq}"):
            if jog_ret:
                atualizar_estado(eq, jog_ret, "jogando")
                st.success(f"{jog_ret} entrou em quadra")

    # 🟥 Expulsão manual
    with c3:
        st.markdown("**🟥 Expulsão**")
        lista_exp = jogando + banco + excluido
        jog_exp = st.selectbox("Jogador", lista_exp, key=f"exp_{eq}")
        if st.button("Expulsar", key=f"btn_exp_{eq}"):
            if jog_exp:
                atualizar_estado(eq, jog_exp, "expulso")
                for j in st.session_state["equipes"][eq]:
                    if j["numero"] == jog_exp:
                        j["elegivel"] = False
                st.error(f"{jog_exp} expulso do jogo!")

# ---------------------- RENDERIZAÇÃO DA ABA 3 ----------------------
with abas[2]:
    st.subheader("Controle do Jogo")

    # Controles do cronômetro (usam o estado já definido no topo)
    cc1, cc2, cc3, cc4 = st.columns([1,1,1,2])
    with cc1:
        if st.button("▶️ Iniciar", key="clk_start"):
            if not st.session_state["cron_running"]:
                st.session_state["cron_running"] = True
                st.session_state["cron_start_epoch"] = time.time()
                st.toast("⏱️ Iniciado", icon="▶️")
    with cc2:
        if st.button("⏸️ Pausar", key="clk_pause"):
            if st.session_state["cron_running"]:
                # consolida
                agora = time.time()
                st.session_state["cron_base"] = (
                    st.session_state["cron_base"] + (agora - st.session_state["cron_start_epoch"])
                )
                st.session_state["cron_running"] = False
                st.session_state["cron_start_epoch"] = None
                st.toast("⏸️ Pausado", icon="⏸️")
    with cc3:
        if st.button("🔁 Zerar", key="clk_reset"):
            st.session_state["cron_running"] = False
            st.session_state["cron_base"] = 0.0
            st.session_state["cron_start_epoch"] = None
            st.toast("🔁 Zerado", icon="🔁")
    with cc4:
        st.session_state["periodo"] = st.selectbox(
            "Período",
            ["1º Tempo", "2º Tempo"],
            index=0 if st.session_state["periodo"] == "1º Tempo" else 1,
            key="sel_periodo"
        )

    # Mostra o cronômetro visual JS **usando a função que você já definiu no topo**
    render_cronometro_js()
    st.markdown("<br>", unsafe_allow_html=True)

    # Botão de inverter lados
    if "invertido" not in st.session_state:
        st.session_state["invertido"] = False
    if st.button("🔄 Inverter Lados"):
        st.session_state["invertido"] = not st.session_state["invertido"]

    # Cores vindas da aba de configuração
    cor_a = st.session_state["cores"].get("A", "#1976D2")
    cor_b = st.session_state["cores"].get("B", "#D32F2F")

    # Equipes lado a lado
    if not st.session_state["invertido"]:
        colA, colB = st.columns(2)
        with colA:
            painel_equipe("A", cor_a)
        with colB:
            painel_equipe("B", cor_b)
    else:
        colB, colA = st.columns(2)
        with colB:
            painel_equipe("B", cor_b)
        with colA:
            painel_equipe("A", cor_a)
        with colA:
            painel("A", cor_a)

