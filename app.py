import streamlit as st
import time

# =====================================================
# 🔧 Inicialização de estado
# =====================================================
if "cronometro" not in st.session_state:
    st.session_state.cronometro = 0
if "rodando" not in st.session_state:
    st.session_state.rodando = False
if "ultimo_tick" not in st.session_state:
    st.session_state.ultimo_tick = None
if "equipes" not in st.session_state:
    st.session_state.equipes = {"A": [], "B": []}
if "cores" not in st.session_state:
    st.session_state.cores = {"A": "#FFD700", "B": "#87CEEB"}
if "sub_msg_time" not in st.session_state:
    st.session_state.sub_msg_time = {"A": 0, "B": 0}

# =====================================================
# ⏱️ Cronômetro em tempo real
# =====================================================
def atualizar_cronometro():
    if st.session_state.rodando and st.session_state.ultimo_tick:
        agora = time.time()
        st.session_state.cronometro += agora - st.session_state.ultimo_tick
        st.session_state.ultimo_tick = agora

def iniciar():
    if not st.session_state.rodando:
        st.session_state.rodando = True
        st.session_state.ultimo_tick = time.time()

def pausar():
    if st.session_state.rodando:
        atualizar_cronometro()
        st.session_state.rodando = False

def zerar():
    st.session_state.cronometro = 0
    st.session_state.ultimo_tick = None
    st.session_state.rodando = False

def formatar_tempo(segundos):
    m = int(segundos // 60)
    s = int(segundos % 60)
    return f"{m:02d}:{s:02d}"

# =====================================================
# ⚙️ Funções de controle de jogadores
# =====================================================
def efetuar_substituicao(state, equipe, numeros):
    sai, entra = numeros
    jogadores = state["equipes"][equipe]
    for j in jogadores:
        if j["numero"] == int(sai):
            j["estado"] = "banco"
        if j["numero"] == int(entra):
            j["estado"] = "jogando"
    return True, f"Substituição realizada: Sai {sai}, Entra {entra}"

def aplicar_exclusao_2min(state, equipe, numero):
    for j in state["equipes"][equipe]:
        if j["numero"] == int(numero):
            if j["estado"] != "jogando":
                return False, "Jogador não pode receber 2 minutos (verifique estado).", False
            j["exclusoes"] += 1
            if j["exclusoes"] >= 3:
                j["elegivel"] = False
                j["estado"] = "expulso"
                return True, f"Jogador {numero} recebeu 2 minutos e foi expulso (3 exclusões).", True
            j["estado"] = "penalizado"
            return True, f"Jogador {numero} recebeu 2 minutos.", False
    return False, "Jogador não encontrado.", False

def aplicar_expulsao(state, equipe, numero):
    for j in state["equipes"][equipe]:
        if j["numero"] == int(numero):
            if not j["elegivel"]:
                return False, "Jogador já expulso."
            j["elegivel"] = False
            j["estado"] = "expulso"
            return True, f"Jogador {numero} foi expulso."
    return False, "Jogador não encontrado."

def completar_substituicao(state, equipe, numero):
    for j in state["equipes"][equipe]:
        if j["numero"] == int(numero):
            if j["estado"] != "penalizado":
                return False, "Jogador não está em penalidade."
            j["estado"] = "banco"
            return True, f"Jogador {numero} completou os 2 minutos."
    return False, "Jogador não encontrado."

# =====================================================
# ⚙️ ABA 1 - CONFIGURAÇÃO DA EQUIPE
# =====================================================
st.title("Controle de Tempo - Handebol")

abas = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

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

            # Cor da equipe (mantendo seu padrão atual)
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
                # Ao salvar nova configuração, desbloqueia titulares para nova seleção
                st.session_state["titulares_definidos"][eq] = False

# =====================================================
# ⚙️ Função de painel de substituições (corrigida)
# =====================================================
def painel(equipe: str):
    st.markdown(
        f"<span class='side-head' style='background:{st.session_state['cores'][equipe]};'>Equipe {equipe}</span>",
        unsafe_allow_html=True
    )

    jogando = [j["numero"] for j in st.session_state["equipes"][equipe]
               if j["estado"] == "jogando" and j["elegivel"]]
    banco = [j["numero"] for j in st.session_state["equipes"][equipe]
             if j["estado"] == "banco" and j["elegivel"]]

    sai_key = f"sai_{equipe}"
    entra_key = f"entra_{equipe}"
    unico_key = f"unico_{equipe}"

    c1, c2, c3 = st.columns([1, 1, 1.1])
    sai = c1.selectbox("🟥 Sai (jogando)", [None] + sorted(jogando), key=sai_key)
    entra = c2.selectbox("🟩 Entra (banco)", [None] + sorted(banco), key=entra_key)

    if c3.button("Substituir", key=f"substituir_{equipe}",
                 disabled=(sai is None or entra is None or sai == entra)):
        ok, msg = efetuar_substituicao(st.session_state, equipe, [str(sai), str(entra)])
        if ok:
            st.session_state.update({sai_key: None, entra_key: None})
            st.session_state["sub_msg_time"][equipe] = time.time()
            st.success(msg)
        else:
            st.error(msg)

    now = time.time()
    if now - st.session_state["sub_msg_time"][equipe] < 3 and (sai or entra):
        s = "—" if sai is None else str(sai)
        e = "—" if entra is None else str(entra)
        st.markdown(
            f"<span class='chip chip-sai'>Sai {s}</span> <span class='chip chip-entra'>Entra {e}</span>",
            unsafe_allow_html=True
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    unico = st.selectbox("Jogador (2min / Expulsão / Completou)",
                         [None] + sorted(jogando + banco), key=unico_key)
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

# =====================================================
# ⚙️ ABA 2 - DEFINIR TITULARES
# =====================================================
# =====================================================
# ABA 2 — DEFINIR TITULARES
# =====================================================
with abas[1]:
    with abas[1]:
    st.header("Definir Titulares")
    for eq in ["A", "B"]:
        if len(st.session_state["equipes"][eq]) == 0:
            st.info(f"Registre primeiro a equipe {eq}.")
            continue
        titulares = st.multiselect(f"Titulares da equipe {eq}",
                                   [j["numero"] for j in st.session_state["equipes"][eq]],
                                   max_selections=7,
                                   key=f"titulares_{eq}")
        for j in st.session_state["equipes"][eq]:
            j["estado"] = "jogando" if j["numero"] in titulares else "banco"
        st.success(f"Títulos definidos para equipe {eq}.")

# =====================================================
# ⚙️ ABA 4 - VISUALIZAÇÃO
# =====================================================
with abas[3]:
    st.header("Visualização de Dados")
    for eq in ["A", "B"]:
        st.subheader(f"Equipe {eq}")
        for j in st.session_state["equipes"][eq]:
            st.text(f"Nº {j['numero']} | Estado: {j['estado']} | Elegível: {j['elegivel']} | Exclusões: {j['exclusoes']}")
