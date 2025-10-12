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
# ABA 3 — CONTROLE DO JOGO (Cronômetro JS estável)
# =====================================================
import time, json
import streamlit as st
import streamlit.components.v1 as components

# --- helpers mínimos (adicione no topo do arquivo caso ainda não existam) ---
def _init_clock_state():
    if "iniciado" not in st.session_state: st.session_state["iniciado"] = False
    if "ultimo_tick" not in st.session_state: st.session_state["ultimo_tick"] = time.time()
    if "cronometro" not in st.session_state: st.session_state["cronometro"] = 0.0
    if "periodo" not in st.session_state: st.session_state["periodo"] = "1º Tempo"
    if "marcacoes" not in st.session_state: st.session_state["marcacoes"] = []  # snapshots

def tempo_logico_atual() -> float:
    if st.session_state["iniciado"]:
        return st.session_state["cronometro"] + (time.time() - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def iniciar():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()
        st.toast("⏱️ Iniciado", icon="▶️")

def pausar():
    if st.session_state["iniciado"]:
        st.session_state["cronometro"] = tempo_logico_atual()
        st.session_state["iniciado"] = False
        st.toast("⏸️ Pausado", icon="⏸️")

def zerar():
    st.session_state["iniciado"] = False
    st.session_state["cronometro"] = 0.0
    st.session_state["ultimo_tick"] = time.time()
    st.toast("🔁 Zerado", icon="🔁")

def render_cronometro_js():
    # Passa o estado Python -> JS e o JS atualiza a cada 250ms no navegador
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
        const startEpoch = {json.dumps(start_epoch)}; // epoch seg ou null

        function fmt(sec){{
          sec = Math.max(0, Math.floor(sec));
          const m = Math.floor(sec/60), s = sec % 60;
          return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
        }}
        function tick(){{
          let elapsed = baseElapsed;
          if (iniciado && startEpoch){{
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

# ---------- A B A  3 ----------
with abas[2]:
    _init_clock_state()
    st.subheader("Controle do Jogo")

    # Botões primeiro (para o JS receber estado já atualizado)
    b1, b2, b3, b4 = st.columns([1,1,1,1])
    with b1:
        if st.button("▶️ Iniciar", key="clk_start"): iniciar()
    with b2:
        if st.button("⏸️ Pausar", key="clk_pause"): pausar()
    with b3:
        if st.button("🔁 Zerar", key="clk_reset"): zerar()
    with b4:
        st.session_state["periodo"] = st.selectbox(
            "Período", ["1º Tempo","2º Tempo"],
            index=0 if st.session_state["periodo"]=="1º Tempo" else 1,
            key="sel_periodo"
        )

    # Render cronômetro JS com o estado pós-botões
    render_cronometro_js()

    # Salvar marcação (snapshot do tempo atual + período)
    if st.button("💾 Salvar marcação", key="clk_mark"):
        t = tempo_logico_atual()
        st.session_state["marcacoes"].append({"periodo": st.session_state["periodo"], "elapsed": float(t), "ts": time.time()})
        mm, ss = int(t//60), int(t%60)
        st.success(f"Salvo: {mm:02d}:{ss:02d} — {st.session_state['periodo']}")

    # (Opcional) Lista rápida das marcações
    if st.session_state["marcacoes"]:
        st.caption("Marcações salvas:")
        for i, m in enumerate(st.session_state["marcacoes"], 1):
            mm, ss = int(m["elapsed"]//60), int(m["elapsed"]%60)
            st.write(f"{i}. {mm:02d}:{ss:02d} — {m['periodo']}")

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
