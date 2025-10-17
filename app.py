# app.py
import time
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from string import Template

st.set_page_config(page_title="Controle de Tempo Handebol", page_icon="⏱", layout="wide")

# =====================================================
# 🔧 ESTADO GLOBAL / HELPERS BÁSICOS
# =====================================================

def _init_globals():
    """Inicializa todo estado global usado no app (idempotente)."""
    # Estrutura das equipes e metadados
    if "equipes" not in st.session_state:
        st.session_state["equipes"] = {"A": [], "B": []}  # cada item: {"numero", "estado", "elegivel", "exclusoes"}
    if "cores" not in st.session_state:
        st.session_state["cores"] = {"A": "#00AEEF", "B": "#EC008C"}
    if "nome_A" not in st.session_state:
        st.session_state["nome_A"] = "Equipe A"
    if "nome_B" not in st.session_state:
        st.session_state["nome_B"] = "Equipe B"

    # Controle de titulares
    if "titulares_definidos" not in st.session_state:
        st.session_state["titulares_definidos"] = {"A": False, "B": False}

    # Cronômetro principal
    if "iniciado" not in st.session_state:
        st.session_state["iniciado"] = False
    if "ultimo_tick" not in st.session_state:
        st.session_state["ultimo_tick"] = time.time()
    if "cronometro" not in st.session_state:
        st.session_state["cronometro"] = 0.0
    if "periodo" not in st.session_state:
        st.session_state["periodo"] = "1º Tempo"
    if "invert_lados" not in st.session_state:
        st.session_state["invert_lados"] = False

    # Penalidades 2' (exclusões)
    if "penalties" not in st.session_state:
        # por equipe: lista de dicts {numero:int, start:float(elapsed), end:float(elapsed), consumido:bool}
        st.session_state["penalties"] = {"A": [], "B": []}

    # Estatísticas de tempo (segundos)
    if "stats" not in st.session_state:
        # por equipe: num -> {"jogado_1t":0.0, "jogado_2t":0.0, "banco":0.0, "doismin":0.0}
        st.session_state["stats"] = {"A": {}, "B": {}}

def get_team_name(eq: str) -> str:
    """Nome configurado da equipe, com fallback."""
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"

def atualizar_estado(eq: str, numero: int, novo_estado: str) -> bool:
    """
    Atualiza 'estado' de um jogador na equipe:
      estados possíveis: "jogando", "banco", "excluido", "expulso"
    Retorna True se encontrou e atualizou.
    """
    for j in st.session_state["equipes"][eq]:
        if int(j["numero"]) == int(numero):
            j["estado"] = novo_estado
            return True
    return False

def jogadores_por_estado(eq: str, estado: str):
    """Lista números (int) dos jogadores da equipe em um determinado estado e elegíveis."""
    return [
        int(j["numero"])
        for j in st.session_state["equipes"][eq]
        if j.get("elegivel", True) and j.get("estado") == estado
    ]

def elenco(eq: str):
    """Lista números (int) de todos os jogadores elegíveis da equipe (independente do estado)."""
    return [
        int(j["numero"])
        for j in st.session_state["equipes"][eq]
        if j.get("elegivel", True)
    ]

def _ensure_player_stats(eq: str, numero: int):
    """Garante o dicionário de stats do jogador e o retorna (em segundos)."""
    return st.session_state["stats"][eq].setdefault(int(numero), {
        "jogado_1t": 0.0, "jogado_2t": 0.0, "banco": 0.0, "doismin": 0.0
    })

def tempo_logico_atual() -> float:
    """
    Retorna o 'elapsed' lógico do cronômetro principal, em segundos:
      - se rodando: cronometro + (agora - ultimo_tick)
      - se pausado: cronometro
    """
    if st.session_state.get("iniciado"):
        return st.session_state["cronometro"] + (time.time() - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def _parse_mmss(txt: str) -> int | None:
    """Converte 'MM:SS' -> segundos (int). Retorna None se formato inválido."""
    try:
        mm, ss = txt.strip().split(":")
        m = int(mm); s = int(ss)
        if m < 0 or s < 0 or s >= 60:
            return None
        return m * 60 + s
    except Exception:
        return None

# inicializa o estado global (idempotente)
__initialized = st.session_state.get("__init_globals_done__", False)
if not __initialized:
    _init_globals()
    st.session_state["__init_globals_done__"] = True

# =====================================================
# ⏱️ CRONÔMETRO / PENALIDADES (REGISTRO)
# =====================================================

def iniciar():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()

def pausar():
    if st.session_state["iniciado"]:
        agora = time.time()
        st.session_state["cronometro"] += agora - st.session_state["ultimo_tick"]
        st.session_state["iniciado"] = False

def zerar():
    st.session_state["iniciado"] = False
    st.session_state["cronometro"] = 0.0
    st.session_state["ultimo_tick"] = time.time()

def _registrar_exclusao(eq: str, numero: int, start_elapsed: float):
    st.session_state["penalties"][eq].append({
        "numero": int(numero),
        "start": float(start_elapsed),
        "end": float(start_elapsed) + 120.0,  # 2'
        "consumido": False
    })
    atualizar_estado(eq, numero, "excluido")

def _penalidades_ativas(eq: str, agora_elapsed: float):
    return [
        p for p in st.session_state["penalties"].get(eq, [])
        if (agora_elapsed < p["end"]) and not p["consumido"]
    ]

def _penalidades_concluidas_nao_consumidas(eq: str, agora_elapsed: float):
    return [
        p for p in st.session_state["penalties"].get(eq, [])
        if (agora_elapsed >= p["end"]) and not p["consumido"]
    ]

def _penalidade_top(eq: str, agora_elapsed: float):
    ativas = _penalidades_ativas(eq, agora_elapsed)
    if not ativas:
        return (None, 0)
    p = min(ativas, key=lambda x: x["end"])
    restante = max(0, int(round(p["end"] - agora_elapsed)))
    return (int(p["numero"]), int(restante))

# =====================================================
# 🧢 PLACAR GLOBAL (ACIMA DAS ABAS)
# =====================================================

def render_top_scoreboard():
    # CSS do placar (cabeçalho fixo)
    st.markdown("""
    <style>
      .top-sticky {
        position: sticky; top: 0; z-index: 10000;
        background: linear-gradient(180deg, #0a0a0a 0%, #0e0e0e 100%);
        padding: 12px 14px 10px; border-bottom: 2px solid #222;
        box-shadow: 0 6px 12px rgba(0,0,0,.35);
      }
      .placar-grid {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center; gap: 16px;
      }
      .side-box { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
      .side-box.right { align-items: flex-end; }
      .team-tag {
        color: #fff; font-weight: 800; padding: 6px 10px; border-radius: 10px; font-size: 15px;
        letter-spacing: .3px; box-shadow: 0 2px 6px rgba(0,0,0,.35);
      }
      .main-clock {
        font-family: 'Courier New', monospace;
        font-size: 72px; line-height: 1; font-weight: 900;
        color: #FFD700; background: #000; padding: 10px 24px; border-radius: 14px;
        letter-spacing: 4px;
        box-shadow: 0 0 22px rgba(255,215,0,.35), inset 0 0 18px rgba(255,255,255,.06);
        border: 1px solid #333; text-align:center; min-width: 320px;
        text-shadow: 0 0 10px rgba(255,215,0,.45);
      }
      .mini2 {
        font-family: 'Courier New', monospace;
        font-size: 26px; font-weight: 800;
        color: #FF5555; background:#111; padding: 6px 12px; border-radius: 10px;
        text-shadow: 0 0 6px rgba(255,0,0,.6);
        border: 1px solid #333; min-width: 120px; text-align:center;
        box-shadow: inset 0 0 10px rgba(255,255,255,.04);
      }
      .mini2.muted { color: #888; text-shadow: none; }
      .controls-row { margin-top: 8px; display:flex; gap:10px; justify-content:center; }
      .stButton > button {
        border-radius: 10px; padding: 6px 14px; border: 1px solid #333;
        background: #161616; color: #eee; font-weight: 700;
      }
      .stButton > button:hover { background:#1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

    iniciado_js = "true" if st.session_state["iniciado"] else "false"
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if st.session_state["iniciado"] else None

    # 2' — menor restante de cada lado
    agora = tempo_logico_atual()
    numA, restA = _penalidade_top("A", agora)
    numB, restB = _penalidade_top("B", agora)

    corA = st.session_state["cores"].get("A", "#00AEEF")
    corB = st.session_state["cores"].get("B", "#EC008C")
    nomeA = get_team_name("A")
    nomeB = get_team_name("B")

    html_tpl = Template("""
    <div class="top-sticky">
      <div class="placar-grid">
        <div class="side-box">
          <div class="team-tag" style="background: $corA;">$nomeA</div>
          <div id="penA" class="mini2 $muteA">$penA_text</div>
        </div>
        <div id="mainclock" class="main-clock">00:00</div>
        <div class="side-box right">
          <div class="team-tag" style="background: $corB;">$nomeB</div>
          <div id="penB" class="mini2 $muteB">$penB_text</div>
        </div>
      </div>
    </div>
    <script>
    (function(){
      // clock principal
      const el = document.getElementById('mainclock');
      const iniciado = $iniciado;
      const baseElapsed = $baseElapsed;
      const startEpoch = $startEpoch;
      function fmt(sec){
        sec = Math.max(0, Math.floor(sec));
        const m = Math.floor(sec/60), s = sec % 60;
        return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
      }
      function tickMain(){
        let elapsed = baseElapsed;
        if (iniciado && startEpoch){
          const now = Date.now()/1000;
          elapsed = baseElapsed + (now - startEpoch);
        }
        el.textContent = fmt(elapsed);
      }
      tickMain();
      if (window.__top_mainclock) clearInterval(window.__top_mainclock);
      window.__top_mainclock = setInterval(tickMain, 250);

      // 2' A
      let rA = $restA;
      const penA = document.getElementById('penA');
      const beep = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
      function tickA(){
        if (!penA) return;
        if (rA <= 0) return;
        rA = Math.max(0, rA - 1);
        const m = String(Math.floor(rA/60)).padStart(2,'0');
        const s = String(rA%60).padStart(2,'0');
        penA.textContent = (rA>0? m + ':' + s : '—');
        if (rA === 0){ try{ beep.play(); }catch(e){} }
      }
      if (window.__top_penA) clearInterval(window.__top_penA);
      if (rA > 0) window.__top_penA = setInterval(tickA, 1000);

      // 2' B
      let rB = $restB;
      const penB = document.getElementById('penB');
      function tickB(){
        if (!penB) return;
        if (rB <= 0) return;
        rB = Math.max(0, rB - 1);
        const m = String(Math.floor(rB/60)).padStart(2,'0');
        const s = String(rB%60).padStart(2,'0');
        penB.textContent = (rB>0? m + ':' + s : '—');
        if (rB === 0){ try{ beep.play(); }catch(e){} }
      }
      if (window.__top_penB) clearInterval(window.__top_penB);
      if (rB > 0) window.__top_penB = setInterval(tickB, 1000);
    })();
    </script>
    """)
    penA_text = f"#{numA} – {restA//60:02d}:{restA%60:02d}" if numA is not None else "—"
    penB_text = f"#{numB} – {restB//60:02d}:{restB%60:02d}" if numB is not None else "—"
    muteA = "" if numA is not None else "muted"
    muteB = "" if numB is not None else "muted"
    html = html_tpl.substitute(
        corA=corA, nomeA=nomeA, penA_text=penA_text, muteA=muteA,
        corB=corB, nomeB=nomeB, penB_text=penB_text, muteB=muteB,
        iniciado=iniciado_js,
        baseElapsed=json.dumps(base_elapsed),
        startEpoch=json.dumps(start_epoch),
        restA=int(restA), restB=int(restB)
    )
    components.html(html, height=140)

    # Botões (toggle Play/Pause + Zerar)
    c1, c2 = st.columns([1,1])
    with c1:
        if st.session_state["iniciado"]:
            if st.button("⏸️ Pausar", key="top_pause"):
                pausar(); st.rerun()
        else:
            if st.button("▶️ Iniciar", key="top_play"):
                iniciar(); st.rerun()
    with c2:
        if st.button("🔁 Zerar", key="top_reset"):
            zerar(); st.rerun()

# Render do placar (acima das abas)
render_top_scoreboard()

# =====================================================
# 🧭 ABAS
# =====================================================

abas = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização de Dados",
])

# =====================================================
# ABA 1 — CONFIGURAÇÃO
# =====================================================
with abas[0]:
    st.subheader("Configuração da Equipe")

    def ensure_num_list(team_key: str, qtd: int):
        list_key = f"numeros_{team_key}"
        if list_key not in st.session_state:
            st.session_state[list_key] = [i + 1 for i in range(qtd)]
        else:
            nums = st.session_state[list_key]
            if len(nums) < qtd:
                nums.extend(list(range(len(nums) + 1, qtd + 1)))
            elif len(nums) > qtd:
                st.session_state[list_key] = nums[:qtd]

    colA, colB = st.columns(2)
    for eq, col in zip(["A", "B"], [colA, colB]):
        with col:
            st.session_state.setdefault(f"nome_{eq}", f"Equipe {eq}")
            st.session_state.setdefault("equipes", {"A": [], "B": []})
            st.session_state.setdefault("cores", {"A": "#00AEEF", "B": "#EC008C"})

            st.markdown(f"### {st.session_state[f'nome_{eq}']}")

            # sem atribuição ao session_state — o widget cuida disso
            st.text_input(
                f"Nome da equipe {eq}",
                value=st.session_state[f"nome_{eq}"],
                key=f"nome_{eq}"
            )

            qtd_default = len(st.session_state["equipes"][eq]) or 7
            qtd = st.number_input(
                f"Quantidade de jogadores ({eq})",
                min_value=1, max_value=20, step=1,
                value=qtd_default, key=f"qtd_{eq}"
            )
            ensure_num_list(eq, int(qtd))

            st.markdown("**Números das camisetas:**")
            cols = st.columns(5)
            for i, num in enumerate(st.session_state[f"numeros_{eq}"]):
                with cols[i % 5]:
                    novo = st.number_input(
                        f"Jogador {i+1}",
                        min_value=0, max_value=999, step=1,
                        value=int(num), key=f"{eq}_num_{i}"
                    )
                    st.session_state[f"numeros_{eq}"][i] = int(novo)

            st.session_state["cores"][eq] = st.color_picker(
                f"Cor da equipe {eq}",
                value=st.session_state["cores"][eq],
                key=f"cor_{eq}"
            )

            if st.button(f"Salvar equipe {eq}", key=f"save_team_{eq}"):
                numeros = list(dict.fromkeys(st.session_state[f"numeros_{eq}"]))
                st.session_state["equipes"][eq] = [
                    {"numero": int(n), "estado": "banco", "elegivel": True, "exclusoes": 0}
                    for n in numeros
                ]
                # limpa seleções/estados relacionados
                for k in (f"sai_{eq}", f"entra_{eq}", f"doismin_sel_{eq}", f"comp_sel_{eq}", f"exp_sel_{eq}"):
                    st.session_state.pop(k, None)
                st.session_state["penalties"][eq] = []
                st.session_state["stats"][eq] = {}
                st.session_state["titulares_definidos"][eq] = False
                st.success(f"Equipe {eq} salva com {len(numeros)} jogadores.")
                st.rerun()

# =====================================================
# ABA 2 — TITULARES
# =====================================================
with abas[1]:
    st.subheader("Definir Titulares")
    for eq in ["A", "B"]:
        st.markdown(f"### {get_team_name(eq)}")
        jogadores = st.session_state["equipes"][eq]
        if not jogadores:
            st.info(f"Cadastre primeiro a {get_team_name(eq)} na aba anterior.")
            continue
        numeros = [j["numero"] for j in jogadores]
        disabled = bool(st.session_state["titulares_definidos"][eq])
        if disabled:
            st.success("Titulares já registrados. Clique em **Corrigir** para editar.")
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
                    sel = set(map(int, titulares_sel))
                    for j in st.session_state["equipes"][eq]:
                        j["estado"] = "jogando" if j["numero"] in sel else "banco"
                        j["elegivel"] = True
                    st.session_state["titulares_definidos"][eq] = True
                    st.success(f"Titulares de {get_team_name(eq)} registrados.")
        with c2:
            if st.button(f"Corrigir ({eq})", key=f"corrigir_tit_{eq}"):
                st.session_state["titulares_definidos"][eq] = False
                st.info("Edição de titulares liberada.")

# =====================================================
# ABA 3 — CONTROLE DO JOGO (somente controles)
# =====================================================
def painel_equipe(eq: str):
    # Cabeçalho do time + linha “quadra”
    cor = st.session_state["cores"].get(eq, "#333")
    nome = get_team_name(eq)
    st.markdown(
        f"<div style='color:#fff;background:{cor};padding:6px 10px;border-radius:8px;font-weight:700;margin-bottom:6px;'>{nome}</div>",
        unsafe_allow_html=True
    )

    jogadores = st.session_state["equipes"].get(eq, [])
    on_court = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "jogando" and j.get("elegivel", True)])
    excluidos = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "excluido" and j.get("elegivel", True)])

    # chips
    chip_html = []
    for n in on_court:
        chip_html.append("<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#e8ffe8;color:#0b5;border:1px solid #bfe6bf;'>#{}</span>".format(n))
    for n in excluidos:
        chip_html.append("<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#f2f3f5;color:#888;border:1px solid #dcdfe3;opacity:.8;'>#{}</span>".format(n))
    st.markdown(f"<div style='margin:6px 0 10px;'>{''.join(chip_html) if chip_html else '<span style=\"color:#666;\">Nenhum jogador em quadra.</span>'}</div>", unsafe_allow_html=True)

    # Substituição
    st.markdown("**🔁 Substituição**")
    cols_sub = st.columns([1, 1, 1])
    list_sai = jogadores_por_estado(eq, "jogando")
    list_entra = jogadores_por_estado(eq, "banco")
    sai = cols_sub[0].selectbox("Sai", list_sai, key=f"sai_{eq}")
    entra = cols_sub[1].selectbox("Entra", list_entra, key=f"entra_{eq}")
    if cols_sub[2].button("Confirmar", key=f"btn_sub_{eq}", disabled=(not list_sai or not list_entra)):
        if (sai in list_sai) and (entra in list_entra):
            atualizar_estado(eq, sai, "banco")
            atualizar_estado(eq, entra, "jogando")
            st.success(f"Substituição: Sai {sai} / Entra {entra}", icon="🔁")
            st.markdown(
                f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#ffe5e5;color:#a30000;'>Sai {sai}</span>"
                f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#e7ffe7;color:#005a00;'>Entra {entra}</span>",
                unsafe_allow_html=True
            )
        else:
            st.error("Seleção inválida para substituição.")
    st.markdown("---")

    # 2 minutos (registrar penalidade) — timers aparecem só no cabeçalho
    st.markdown("**⛔ 2 minutos**")
    jogadores_all = elenco(eq)
    jog_2m = st.selectbox("Jogador", jogadores_all, key=f"doismin_sel_{eq}")
    if st.button("Aplicar 2'", key=f"btn_2min_{eq}", disabled=(len(jogadores_all) == 0)):
        start = tempo_logico_atual()
        _registrar_exclusao(eq, jog_2m, start_elapsed=start)
        st.warning(f"Jogador {jog_2m} excluído por 2 minutos. (Timer no topo)")

    # Completou (retorno após 2')
    st.markdown("---")
    st.markdown("**✅ Completou**")
    agora = tempo_logico_atual()
    concluidas = _penalidades_concluidas_nao_consumidas(eq, agora)
    elegiveis_retorno = jogadores_por_estado(eq, "banco") + jogadores_por_estado(eq, "excluido")
    comp = st.selectbox("Jogador que entra", elegiveis_retorno, key=f"comp_sel_{eq}")
    if st.button("Confirmar retorno", key=f"btn_comp_{eq}", disabled=(len(elegiveis_retorno) == 0)):
        if not concluidas:
            st.error("Ainda não há exclusões concluídas (2' completos). Aguarde.")
        else:
            concluidas.sort(key=lambda p: p["end"])
            concluidas[0]["consumido"] = True
            atualizar_estado(eq, comp, "jogando")
            st.success(f"Jogador {comp} entrou após 2'.")

    # Expulsão
    st.markdown("---")
    st.markdown("**🟥 Expulsão**")
    exp = st.selectbox("Jogador", jogadores_all, key=f"exp_sel_{eq}")
    if st.button("Confirmar expulsão", key=f"btn_exp_{eq}", disabled=(len(jogadores_all) == 0)):
        ok = False
        for j in st.session_state["equipes"][eq]:
            if int(j["numero"]) == int(exp):
                j["estado"] = "expulso"
                j["elegivel"] = False
                ok = True
                break
        if ok:
            st.error(f"Jogador {exp} expulso.")
        else:
            st.error("Não foi possível expulsar o jogador selecionado.")

with abas[2]:
    st.subheader("Controle do Jogo")
    st.session_state["periodo"] = st.selectbox(
        "Período", ["1º Tempo", "2º Tempo"],
        index=0 if st.session_state["periodo"] == "1º Tempo" else 1,
        key="sel_periodo"
    )
    st.session_state["invert_lados"] = st.toggle("Inverter lados (A ⇄ B)", value=st.session_state["invert_lados"])

    lados = ("A", "B") if not st.session_state["invert_lados"] else ("B", "A")
    col_esq, col_dir = st.columns(2)
    with col_esq:
        if st.session_state["equipes"][lados[0]]:
            st.markdown(f"#### {get_team_name(lados[0])}")
            painel_equipe(lados[0])
        else:
            st.info(f"Cadastre a {get_team_name(lados[0])} na aba de Configuração.")
    with col_dir:
        if st.session_state["equipes"][lados[1]]:
            st.markdown(f"#### {get_team_name(lados[1])}")
            painel_equipe(lados[1])
        else:
            st.info(f"Cadastre a {get_team_name(lados[1])} na aba de Configuração.")

    # Retroativas (mensagem “chipada” logo abaixo do botão)
    st.divider()
    st.markdown("## 📝 Substituições avulsas (retroativas)")

    col_eq, col_time = st.columns([1, 1])
    with col_eq:
        equipe_sel = st.radio("Equipe", ["A", "B"], horizontal=True, key="retro_eq", format_func=lambda x: get_team_name(x))
    with col_time:
        periodo_sel = st.selectbox("Período da jogada", ["1º Tempo", "2º Tempo"], key="retro_periodo")

    all_nums = elenco(equipe_sel)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        sai_num = st.selectbox("Sai", all_nums, key="retro_sai")
    with c2:
        entra_opcoes = [n for n in all_nums if n != sai_num]
        entra_num = st.selectbox("Entra", entra_opcoes, key="retro_entra")
    with c3:
        tempo_str = st.text_input("Tempo do jogo (MM:SS)", value="00:00", key="retro_tempo", help="Ex.: 12:34 = ocorreu aos 12min34s.")

    def aplicar_retro():
        t_mark = _parse_mmss(tempo_str)
        if t_mark is None:
            st.error("Tempo inválido. Use o formato MM:SS (ex.: 07:45).")
            return
        if sai_num == entra_num:
            st.error("Os jogadores de 'Sai' e 'Entra' precisam ser diferentes.")
            return

        now_elapsed = tempo_logico_atual()
        dt = max(0.0, float(now_elapsed) - float(t_mark))
        if dt <= 0:
            st.warning("O tempo informado é igual ou maior que o tempo atual — nada a corrigir.")
            return

        jog_key = "jogado_1t" if periodo_sel == "1º Tempo" else "jogado_2t"
        s_out = _ensure_player_stats(equipe_sel, int(sai_num))
        s_in  = _ensure_player_stats(equipe_sel, int(entra_num))

        s_out[jog_key]  = max(0.0, s_out[jog_key] - dt)
        s_out["banco"] += dt
        s_in["banco"]   = max(0.0, s_in["banco"] - dt)
        s_in[jog_key]  += dt

        atualizar_estado(equipe_sel, int(sai_num), "banco")
        atualizar_estado(equipe_sel, int(entra_num), "jogando")

        # flash message + chips (após rerun)
        st.session_state["flash_text"] = f"Substituição retroativa realizada: Sai {sai_num} / Entra {entra_num}"
        st.session_state["flash_html"] = (
            f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#ffe5e5;color:#a30000;'>Sai {sai_num}</span>"
            f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#e7ffe7;color:#005a00;'>Entra {entra_num}</span>"
        )

        # limpa seleções dessa equipe
        for k in (f"sai_{equipe_sel}", f"entra_{equipe_sel}", f"doismin_sel_{equipe_sel}", f"comp_sel_{equipe_sel}", f"exp_sel_{equipe_sel}"):
            st.session_state.pop(k, None)

        st.rerun()

    if st.button("➕ Inserir substituição retroativa", use_container_width=True, key="retro_btn"):
        aplicar_retro()

    # Mensagem flash aqui (logo abaixo do botão)
    if "flash_text" in st.session_state or "flash_html" in st.session_state:
        if "flash_text" in st.session_state:
            st.success(st.session_state["flash_text"], icon="🔁")
        if "flash_html" in st.session_state:
            st.markdown(st.session_state["flash_html"], unsafe_allow_html=True)
        st.session_state.pop("flash_text", None)
        st.session_state.pop("flash_html", None)

# =====================================================
# ABA 4 — VISUALIZAÇÃO DE DADOS
# =====================================================
with abas[3]:
    st.subheader("Visualização de Dados")

    # Estados internos desta aba
    if "last_accum" not in st.session_state:
        st.session_state["last_accum"] = time.time()
    if "viz_auto" not in st.session_state:
        st.session_state["viz_auto"] = False
    if "viz_interval" not in st.session_state:
        st.session_state["viz_interval"] = 1.0

    def _accumulate_time_tick():
        now = time.time()
        dt = max(0.0, now - st.session_state["last_accum"])
        st.session_state["last_accum"] = now
        jogado_key = "jogado_1t" if st.session_state["periodo"] == "1º Tempo" else "jogado_2t"
        for eq in ["A", "B"]:
            for j in st.session_state["equipes"].get(eq, []):
                num = int(j["numero"])
                s = _ensure_player_stats(eq, num)
                estado = j.get("estado", "banco")
                if estado == "jogando":
                    s[jogado_key] += dt
                elif estado == "banco":
                    s["banco"] += dt
                elif estado == "excluido":
                    s["doismin"] += dt

    def _doismin_por_jogador_agora(eq: str, numero: int, agora_elapsed: float) -> float:
        total_sec = 0.0
        for p in st.session_state.get("penalties", {}).get(eq, []):
            if int(p["numero"]) != int(numero): 
                continue
            a, b = float(p["start"]), float(p["end"])
            cumprido = max(0.0, min(tempo_logico_atual(), b) - a)
            total_sec += cumprido
        return total_sec / 60.0

    def _stats_to_dataframe():
        rows = []
        for eq in ["A", "B"]:
            for j in st.session_state["equipes"].get(eq, []):
                num = int(j["numero"])
                est = j.get("estado", "banco")
                exc = j.get("exclusoes", 0)
                s = st.session_state["stats"][eq].get(num, {"jogado_1t":0, "jogado_2t":0, "banco":0, "doismin":0})
                j1 = s["jogado_1t"] / 60.0
                j2 = s["jogado_2t"] / 60.0
                jog_total = j1 + j2
                banco_min = s["banco"] / 60.0
                dois_min = round(_doismin_por_jogador_agora(eq, num, tempo_logico_atual()), 1)
                rows.append({
                    "Equipe": get_team_name(eq),
                    "Número": num,
                    "Estado": est,
                    "Exclusões": exc,
                    "Jogado 1ºT (min)": round(j1, 1),
                    "Jogado 2ºT (min)": round(j2, 1),
                    "Jogado Total (min)": round(jog_total, 1),
                    "Banco (min)": round(banco_min, 1),
                    "2 min (min)": round(dois_min, 1),
                })
        return pd.DataFrame(rows).sort_values(["Equipe", "Número"]) if rows else pd.DataFrame()

    # um tick por render desta aba
    _accumulate_time_tick()

    df = _stats_to_dataframe()
    if df.empty:
        st.info("Sem dados ainda. Cadastre equipes, defina titulares e use os controles do jogo.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar CSV", data=csv, file_name="relatorio_tempos.csv", mime="text/csv")

    if st.session_state["viz_auto"]:
        st.session_state["viz_interval"] = st.number_input("Intervalo (s)", min_value=0.5, max_value=5.0, step=0.5,
                                                           value=float(st.session_state["viz_interval"]))
        time.sleep(float(st.session_state["viz_interval"]))
        st.rerun()
    else:
        st.toggle("Atualizar automaticamente", key="viz_auto")
