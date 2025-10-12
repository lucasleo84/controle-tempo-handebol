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
# ABA 3 — CONTROLE DO JOGO (entradas, saídas e penalidades)
# =====================================================
import time, json
import streamlit.components.v1 as components

# --- Funções auxiliares ---
def atualizar_estado(eq, numero, novo_estado):
    for j in st.session_state["equipes"][eq]:
        if j["numero"] == numero:
            j["estado"] = novo_estado
            return

def jogadores_por_estado(eq, estado):
    return [j["numero"] for j in st.session_state["equipes"][eq] if j["estado"] == estado and j["elegivel"]]

# --- Cronômetro JS fixo (mantido do modelo anterior) ---
def render_cronometro_js():
    iniciado = "true" if st.session_state["iniciado"] else "false"
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if st.session_state["iniciado"] else None

    st.markdown("""
        <style>
        .cronofixo { position: sticky; top: 0; z-index: 999; text-align:center; padding:6px 0 0 0; background:#fff; border-bottom:1px solid #e5e7eb; }
        .digital {
            font-family: 'Courier New', monospace; font-size: 36px; font-weight: bold;
            color: #FFD700; background:#000; padding: 6px 20px; border-radius: 6px;
            display:inline-block; letter-spacing: 2px; box-shadow: 0 0 10px rgba(255,215,0,.5);
        }
        </style>
    """, unsafe_allow_html=True)

    html = f"""
    <div class="cronofixo">
      <div id="cronovisual" class="digital">⏱ 00:00</div>
    </div>
    <script>
      (function(){{
        const el = document.getElementById('cronovisual');
        const iniciado = {iniciado};
        const baseElapsed = {json.dumps(base_elapsed)};
        const startEpoch = {json.dumps(start_epoch)};
        function fmt(sec) {{
          sec = Math.max(0, Math.floor(sec));
          const m = Math.floor(sec/60), s = sec % 60;
          return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
        }}
        function tick() {{
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
    components.html(html, height=68)

# --- Cronômetro 2 minutos com som ---
def render_cronometro_exclusao():
    html = """
    <div style="text-align:center;margin-top:20px;">
      <div id="exclusao" style="
        font-family:'Courier New';font-size:30px;color:#FF3333;
        background:#111;padding:8px 16px;border-radius:8px;display:inline-block;
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
    components.html(html, height=120)

# --- Inicialização ---
with abas[2]:
    st.subheader("Controle do Jogo")
    render_cronometro_js()

    eq = st.radio("Selecione equipe", ["A", "B"], horizontal=True)
    jogando = jogadores_por_estado(eq, "jogando")
    banco = jogadores_por_estado(eq, "banco")
    excluidos = jogadores_por_estado(eq, "excluido")

    st.divider()

    col1, col2, col3 = st.columns(3)

    # ------------------ SUBSTITUIÇÃO ------------------
    with col1:
        st.markdown("### 🔁 Substituição")
        sai = st.selectbox("Sai", jogando, key=f"sai_{eq}")
        entra = st.selectbox("Entra", banco, key=f"entra_{eq}")
        if st.button("Confirmar Substituição", key=f"sub_{eq}"):
            if sai and entra:
                atualizar_estado(eq, sai, "banco")
                atualizar_estado(eq, entra, "jogando")
                st.success(f"Substituição realizada: Sai {sai}, Entra {entra}")

    # ------------------ EXCLUSÃO ------------------
    with col2:
        st.markdown("### ⛔ Exclusão (2 minutos)")
        jogador_ex = st.selectbox("Jogador", jogando, key=f"exc_{eq}")
        if st.button("Aplicar Exclusão", key=f"btn_exc_{eq}"):
            if jogador_ex:
                atualizar_estado(eq, jogador_ex, "excluido")
                st.warning(f"Jogador {jogador_ex} excluído por 2 minutos.")
                render_cronometro_exclusao()

    # ------------------ EXPULSÃO ------------------
    with col3:
        st.markdown("### 🟥 Expulsão")
        jogador_exp = st.selectbox("Jogador", jogando + excluidos + banco, key=f"exp_{eq}")
        if st.button("Confirmar Expulsão", key=f"btn_exp_{eq}"):
            if jogador_exp:
                atualizar_estado(eq, jogador_exp, "expulso")
                for j in st.session_state["equipes"][eq]:
                    if j["numero"] == jogador_exp:
                        j["elegivel"] = False
                st.error(f"Jogador {jogador_exp} expulso do jogo!")

    st.divider()

      # ------------------ COMPLETOU ------------------
    st.markdown("### ✅ Completou 2 minutos")
    # Agora mostra jogadores excluídos + banco
    elegiveis_retorno = jogadores_por_estado(eq, "excluido") + jogadores_por_estado(eq, "banco")
    if not elegiveis_retorno:
        st.info("Nenhum jogador disponível para retorno ou substituição.")
    else:
        jogador_comp = st.selectbox("Jogador que retorna ao jogo", elegiveis_retorno, key=f"comp_{eq}")
        if st.button("Confirmar Retorno", key=f"btn_comp_{eq}"):
            if jogador_comp:
                atualizar_estado(eq, jogador_comp, "jogando")
                st.success(f"Jogador {jogador_comp} entrou no jogo (retorno ou substituição após 2 minutos).")

# =====================================================
# ABA 4 — VISUALIZAÇÃO DE DADOS
# =====================================================
with abas[3]:
    st.subheader("Visualização de Dados")

    for eq in ["A", "B"]:
        st.markdown(f"### Equipe {eq}")
        if not st.session_state["equipes"][eq]:
            st.info("Nenhuma equipe registrada.")
            continue

        for j in st.session_state["equipes"][eq]:
            tempo_jogado = j.get("tempo_jogado", 0.0)
            st.text(f"Jogador {j['numero']} | Estado: {j['estado']} | Tempo jogado: {tempo_jogado/60:.1f} min")
