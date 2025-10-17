# app.py
import time, json
import streamlit as st
import streamlit.components.v1 as components
from string import Template

# =====================================================
# 🔧 Inicialização de estado global
# =====================================================
if "equipes" not in st.session_state:
    st.session_state["equipes"] = {"A": [], "B": []}
if "cores" not in st.session_state:
    st.session_state["cores"] = {"A": "#00AEEF", "B": "#EC008C"}
if "titulares_definidos" not in st.session_state:
    st.session_state["titulares_definidos"] = {"A": False, "B": False}
if "nome_A" not in st.session_state:
    st.session_state["nome_A"] = "Equipe A"
if "nome_B" not in st.session_state:
    st.session_state["nome_B"] = "Equipe B"

# =====================================================
# 🧭 Abas
# =====================================================
abas = st.tabs([
    "Configuração da Equipe",
    "Definir Titulares",
    "Controle do Jogo",
    "Visualização de Dados"
])

# =====================================================
# Helpers básicos compartilhados
# =====================================================
def get_team_name(eq: str) -> str:
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"

def atualizar_estado(eq: str, numero: int, novo_estado: str) -> bool:
    for j in st.session_state["equipes"][eq]:
        if int(j["numero"]) == int(numero):
            j["estado"] = novo_estado
            return True
    return False

def jogadores_por_estado(eq: str, estado: str):
    return [
        int(j["numero"])
        for j in st.session_state["equipes"][eq]
        if j.get("elegivel", True) and j.get("estado") == estado
    ]

def elenco(eq: str):
    return [
        int(j["numero"])
        for j in st.session_state["equipes"][eq]
        if j.get("elegivel", True)
    ]


# =====================================================
# ABA 1 — CONFIGURAÇÃO DA EQUIPE
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
            st.markdown(f"### {get_team_name(eq)}")

            _ = st.text_input(f"Nome da equipe {eq}", key=f"nome_{eq}")
            qtd = st.number_input(
                f"Quantidade de jogadores ({eq})",
                min_value=1, max_value=20, step=1,
                value=len(st.session_state["equipes"][eq]) or 7,
                key=f"qtd_{eq}"
            )

            ensure_num_list(eq, int(qtd))

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

            cor = st.color_picker(
                f"Cor da equipe {eq}",
                value=st.session_state["cores"][eq],
                key=f"cor_{eq}"
            )
            st.session_state["cores"][eq] = cor

            if st.button(f"Salvar equipe {eq}", key=f"save_team_{eq}"):
                numeros = list(dict.fromkeys(st.session_state[f"numeros_{eq}"]))
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
# ABA 3 — CONTROLE DO JOGO (entradas, saídas e penalidades)
# =====================================================
import time, json
import streamlit.components.v1 as components
from string import Template

def _init_clock_state():
    if "iniciado" not in st.session_state: st.session_state["iniciado"] = False
    if "ultimo_tick" not in st.session_state: st.session_state["ultimo_tick"] = time.time()
    if "cronometro" not in st.session_state: st.session_state["cronometro"] = 0.0
    if "periodo" not in st.session_state: st.session_state["periodo"] = "1º Tempo"
    if "invert_lados" not in st.session_state: st.session_state["invert_lados"] = False
    if "penalties" not in st.session_state:
        st.session_state["penalties"] = {"A": [], "B": []}
    if "stats" not in st.session_state:
        st.session_state["stats"] = {"A": {}, "B": {}}

def _equipe_penalidades(eq: str):
    return st.session_state["penalties"].get(eq, [])

def _registrar_exclusao(eq: str, numero: int, start_elapsed: float):
    st.session_state["penalties"][eq].append({
        "numero": int(numero),
        "start": float(start_elapsed),
        "end": float(start_elapsed) + 120.0,
        "consumido": False
    })

def _penalidades_ativas(eq: str, agora_elapsed: float):
    return [p for p in _equipe_penalidades(eq) if (agora_elapsed < p["end"]) and not p["consumido"]]

def _penalidades_concluidas_nao_consumidas(eq: str, agora_elapsed: float):
    return [p for p in _equipe_penalidades(eq) if (agora_elapsed >= p["end"]) and not p["consumido"]]

# ---------- relógio principal: start/pause/reset ----------
def iniciar():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()
        st.toast("⏱️ Iniciado", icon="▶️")

def pausar():
    if st.session_state["iniciado"]:
        agora = time.time()
        st.session_state["cronometro"] += agora - st.session_state["ultimo_tick"]
        st.session_state["iniciado"] = False
        st.toast("⏸️ Pausado", icon="⏸️")

def zerar():
    st.session_state["iniciado"] = False
    st.session_state["cronometro"] = 0.0
    st.session_state["ultimo_tick"] = time.time()
    st.toast("🔁 Zerado", icon="🔁")

def toggle_cronometro():
    if st.session_state.get("iniciado", False): pausar()
    else: iniciar()

def tempo_logico_atual() -> float:
    if st.session_state["iniciado"]:
        return st.session_state["cronometro"] + (time.time() - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def _parse_mmss(txt: str) -> int | None:
    try:
        mm, ss = txt.strip().split(":")
        m = int(mm); s = int(ss)
        if m < 0 or s < 0 or s >= 60: return None
        return m*60 + s
    except Exception:
        return None

# ---------- PLACAR ELETRÔNICO STICKY (com 2' e botões) ----------
def render_top_scoreboard(lado_esq: str, lado_dir: str):
    """Barra fixa com nomes, cronômetro e 2' acumulativos."""
    iniciado = "true" if st.session_state["iniciado"] else "false"
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if st.session_state["iniciado"] else None

    nomeA = get_team_name(lado_esq)
    nomeB = get_team_name(lado_dir)
    corA  = st.session_state["cores"].get(lado_esq, "#0bf")
    corB  = st.session_state["cores"].get(lado_dir, "#0bf")

    # CSS do cabeçalho
    st.markdown(f"""
    <style>
      .sb-wrap {{
        position: sticky; top: 0; z-index: 9999;
        background: #0b0b0b;
        box-shadow: 0 4px 18px rgba(0,0,0,.35);
        border-bottom: 1px solid rgba(255,255,255,.06);
        padding: 10px 12px 14px 12px;
      }}
      .sb-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
      .sb-badge {{
         color:#111; font-weight:800; border-radius:10px; padding:8px 14px;
         background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.85));
         text-shadow: none; letter-spacing:.2px; min-width: 130px; text-align:center;
      }}
      .sb-badge.a {{ background:{corA}; color:#fff; }}
      .sb-badge.b {{ background:{corB}; color:#fff; }}
      .sb-digital {{
         font-family:'Segment7', 'DS-Digital', 'Courier New', monospace;
         font-size:64px; color:#FFD400; background:#000; padding:8px 26px; border-radius:18px;
         box-shadow: inset 0 0 18px rgba(255,255,0,.22), 0 0 32px rgba(255,255,0,.12);
         border: 1px solid #222;
      }}
      .sb-subrow {{ display:flex; align-items:center; justify-content:center; gap:12px; margin-top:8px; }}
      .sb-btn button {{ border-radius:10px!important; padding:8px 16px!important; }}
      .pen-line {{ display:flex; align-items:center; gap:8px; }}
      .pen-box {{
         background:#101214; border:1px solid #2a2f36; color:#f66; padding:6px 10px; border-radius:10px;
         font-family:'Courier New', monospace; font-size:16px; box-shadow: inset 0 0 10px rgba(255,0,0,.15);
      }}
      .pen-title {{ color:#ddd; font-size:12px; margin-bottom:4px; }}
      @media (max-width: 900px) {{
        .sb-digital {{ font-size:48px; }}
        .sb-badge {{ min-width: 100px; }}
      }}
    </style>
    """, unsafe_allow_html=True)

    # Linha 1: badge A | cronômetro | badge B
    colA, colC, colB = st.columns([3, 6, 3], gap="small")
    with colA:
        st.markdown(f"<div class='sb-wrap'><div class='sb-row'>", unsafe_allow_html=True)
        st.markdown(f"<div class='sb-badge a'>{nomeA}</div>", unsafe_allow_html=True)
    with colC:
        # relógio central em JS (fica dentro do sticky)
        components.html(f"""
        <div class="sb-digital" id="sb_clock">00:00</div>
        <script>
          (function(){{
            const el = document.getElementById('sb_clock');
            const iniciado = {iniciado};
            const baseElapsed = {json.dumps(base_elapsed)};
            const startEpoch = {json.dumps(start_epoch)};
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
              el.textContent = fmt(elapsed);
            }}
            tick();
            if (window.__sb_timer) clearInterval(window.__sb_timer);
            window.__sb_timer = setInterval(tick, 250);
          }})();
        </script>
        """, height=90)
    with colB:
        st.markdown(f"<div class='sb-badge b'>{nomeB}</div></div>", unsafe_allow_html=True)

    # Linha 2: 2' A | botões | 2' B
    cA, cBtns, cB = st.columns([3, 6, 3], gap="small")
    # 2' Equipe A (lado_esq)
    with cA:
        st.markdown("<div class='pen-title'>2 minutos — lado esquerdo</div>", unsafe_allow_html=True)
        penA = _penalidades_ativas(lado_esq, tempo_logico_atual())
        if penA:
            st.markdown("<div class='pen-line'>", unsafe_allow_html=True)
            for p in penA:
                restante = max(0, int(round(p["end"] - tempo_logico_atual())))
                mm, ss = restante // 60, restante % 60
                elem_id = f"__ol_pen{lado_esq}_{p['numero']}_{int(p['start'])}"
                components.html(f"""
                  <div class="pen-box"><span>#{int(p['numero'])} </span>
                    <span id="{elem_id}">{mm:02d}:{ss:02d}</span>
                  </div>
                  <script>
                    (function(){{
                      let r = {restante};
                      const el = document.getElementById("{elem_id}");
                      const beep = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
                      function tick(){{
                        r = Math.max(0, r-1);
                        const m = String(Math.floor(r/60)).padStart(2,'0');
                        const s = String(r%60).padStart(2,'0');
                        if (el) el.textContent = m + ":" + s;
                        if (r<=0) {{ try{{ beep.play(); }}catch(e){{}} clearInterval(window["tm_{elem_id}"]); }}
                      }}
                      if (window["tm_{elem_id}"]) clearInterval(window["tm_{elem_id}"]);
                      window["tm_{elem_id}"] = setInterval(tick, 1000);
                    }})();
                  </script>
                """, height=40)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("—")

    # Botões centrais (dentro do placar)
    with cBtns:
        st.markdown("<div class='sb-subrow'>", unsafe_allow_html=True)
        colb1, colb2 = st.columns([1,1], gap="small")
        with colb1:
            rotulo = "⏸️ Pausar" if st.session_state["iniciado"] else "▶️ Iniciar"
            if st.button(rotulo, key="sb_toggle"): toggle_cronometro()
        with colb2:
            if st.button("🔁 Zerar", key="sb_reset"): zerar()
        st.markdown("</div>", unsafe_allow_html=True)

    # 2' Equipe B (lado_dir)
    with cB:
        st.markdown("<div class='pen-title'>2 minutos — lado direito</div>", unsafe_allow_html=True)
        penB = _penalidades_ativas(lado_dir, tempo_logico_atual())
        if penB:
            st.markdown("<div class='pen-line'>", unsafe_allow_html=True)
            for p in penB:
                restante = max(0, int(round(p["end"] - tempo_logico_atual())))
                mm, ss = restante // 60, restante % 60
                elem_id = f"__ol_pen{lado_dir}_{p['numero']}_{int(p['start'])}"
                components.html(f"""
                  <div class="pen-box"><span>#{int(p['numero'])} </span>
                    <span id="{elem_id}">{mm:02d}:{ss:02d}</span>
                  </div>
                  <script>
                    (function(){{
                      let r = {restante};
                      const el = document.getElementById("{elem_id}");
                      const beep = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
                      function tick(){{
                        r = Math.max(0, r-1);
                        const m = String(Math.floor(r/60)).padStart(2,'0');
                        const s = String(r%60).padStart(2,'0');
                        if (el) el.textContent = m + ":" + s;
                        if (r<=0) {{ try{{ beep.play(); }}catch(e){{}} clearInterval(window["tm_{elem_id}"]); }}
                      }}
                      if (window["tm_{elem_id}"]) clearInterval(window["tm_{elem_id}"]);
                      window["tm_{elem_id}"] = setInterval(tick, 1000);
                    }})();
                  </script>
                """, height=40)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("—")

    # fecha wrapper
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Painel da equipe (mesmo de antes) ----------
def painel_equipe(eq: str):
    cor = st.session_state["cores"].get(eq, "#333")
    nome = get_team_name(eq)
    st.markdown(f"<div class='team-head' style='background:{cor};color:#fff;padding:6px 10px;border-radius:8px;font-weight:700;margin:8px 0 6px 0;'>{nome}</div>", unsafe_allow_html=True)

    jogadores = st.session_state["equipes"].get(eq, [])
    on_court = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "jogando" and j.get("elegivel", True)])
    excluidos = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "excluido" and j.get("elegivel", True)])

    st.markdown("""
        <style>
          .sec-title { font-size:14px; font-weight:700; margin:6px 0 4px; }
          .chip { display:inline-block; padding:2px 6px; border-radius:6px; font-size:12px; margin:0 6px 6px 0; }
          .chip-quadra { background:#e8ffe8; color:#0b5; border:1px solid #bfe6bf; }
          .chip-inelegivel { background:#f2f3f5; color:#888; border:1px solid #dcdfe3; opacity:.85; }
          .chip-sai { background:#ffe5e5; color:#a30000; }
          .chip-ent { background:#e7ffe7; color:#005a00; }
        </style>
    """, unsafe_allow_html=True)

    if on_court or excluidos:
        chips = []
        for num in on_court:
            chips.append(f"<span class='chip chip-quadra' title='Jogando'>#{num}</span>")
        for num in excluidos:
            chips.append(f"<span class='chip chip-inelegivel' title='Cumprindo 2 minutos'>#{num}</span>")
        st.markdown("".join(chips), unsafe_allow_html=True)
    else:
        st.caption("Nenhum jogador em quadra no momento.")

    with st.container():
        st.markdown("<div>", unsafe_allow_html=True)

        st.markdown("<div class='sec-title'>🔁 Substituição</div>", unsafe_allow_html=True)
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
                    f"<span class='chip chip-sai'>Sai {sai}</span><span class='chip chip-ent'>Entra {entra}</span>",
                    unsafe_allow_html=True
                )
            else:
                st.error("Seleção inválida para substituição.")
        st.markdown("---")

        cols_pen = st.columns([1, 1])
        with cols_pen[0]:
            st.markdown("<div class='sec-title'>⛔ 2 minutos</div>", unsafe_allow_html=True)
            jogadores_all = elenco(eq)
            jog_2m = st.selectbox("Jogador", jogadores_all, key=f"doismin_sel_{eq}")
            if st.button("Aplicar 2'", key=f"btn_2min_{eq}", disabled=(len(jogadores_all) == 0)):
                atualizar_estado(eq, jog_2m, "excluido")
                start = tempo_logico_atual()
                _registrar_exclusao(eq, jog_2m, start_elapsed=start)
                st.warning(f"Jogador {jog_2m} excluído por 2 minutos (placar no topo mostra # e contagem).")

        with cols_pen[1]:
            st.markdown("<div class='sec-title'>✅ Completou</div>", unsafe_allow_html=True)
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

        st.markdown("<hr>", unsafe_allow_html=True)


# ---------- Render da ABA 3 ----------
with abas[2]:
    _init_clock_state()
    st.subheader("Controle do Jogo")

    # Lados (inverter A/B)
    st.session_state["periodo"] = st.selectbox(
        "Período", ["1º Tempo", "2º Tempo"],
        index=0 if st.session_state["periodo"] == "1º Tempo" else 1,
        key="sel_periodo_ctl"
    )
    st.session_state["invert_lados"] = st.toggle("Inverter lados (A ⇄ B)", value=st.session_state["invert_lados"])

    lados = ("A", "B") if not st.session_state["invert_lados"] else ("B", "A")

    # Placar eletrônico (NOVIDADE)
    render_top_scoreboard(lados[0], lados[1])

    # Painéis lado a lado
    col_esq, col_dir = st.columns(2)
    with col_esq:
        if st.session_state["equipes"][lados[0]]:
            painel_equipe(lados[0])
        else:
            st.info(f"Cadastre a {get_team_name(lados[0])} na aba de Configuração.")
    with col_dir:
        if st.session_state["equipes"][lados[1]]:
            painel_equipe(lados[1])
        else:
            st.info(f"Cadastre a {get_team_name(lados[1])} na aba de Configuração.")

    # ---------- Substituições retroativas (idêntico ao seu) ----------
    st.divider()
    st.markdown("## 📝 Substituições avulsas (retroativas)")

    if "stats" not in st.session_state:
        st.session_state["stats"] = {"A": {}, "B": {}}

    col_eq, col_time = st.columns([1, 1])
    with col_eq:
        equipe_sel = st.radio(
            "Equipe", ["A", "B"],
            horizontal=True, key="retro_eq",
            format_func=lambda x: get_team_name(x),
        )
    with col_time:
        periodo_sel = st.selectbox(
            "Período da jogada",
            ["1º Tempo", "2º Tempo"],
            key="retro_periodo",
        )

    all_nums = elenco(equipe_sel)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        sai_num = st.selectbox("Sai", all_nums, key="retro_sai")
    with c2:
        entra_opcoes = [n for n in all_nums if n != sai_num]
        entra_num = st.selectbox("Entra", entra_opcoes, key="retro_entra")
    with c3:
        tempo_str = st.text_input(
            "Tempo do jogo (MM:SS)",
            value="00:00",
            key="retro_tempo",
            help="Ex.: 12:34 = ocorreu aos 12min34s.",
        )

    def _ensure_player_stats(eq: str, numero: int):
        if "stats" not in st.session_state:
            st.session_state["stats"] = {"A": {}, "B": {}}
        return st.session_state["stats"][eq].setdefault(int(numero), {
            "jogado_1t": 0.0, "jogado_2t": 0.0, "banco": 0.0, "doismin": 0.0
        })

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

        mm_dt, ss_dt = int(dt // 60), int(dt % 60)
        st.info(
            f"Retroativo aplicado ({periodo_sel}) em {get_team_name(equipe_sel)}: "
            f"Sai {sai_num} (−{mm_dt:02d}:{ss_dt:02d} jogado, + banco) | "
            f"Entra {entra_num} (+ jogado, − banco) a partir de {tempo_str} até agora."
        )
        st.session_state["flash_text"] = f"Substituição retroativa realizada: Sai {sai_num} / Entra {entra_num}"
        st.session_state["flash_html"] = (
            f"<span class='chip chip-sai'>Sai {sai_num}</span>"
            f"<span class='chip chip-ent'>Entra {entra_num}</span>"
        )

        for k in (
            f"sai_{equipe_sel}", f"entra_{equipe_sel}", f"doismin_sel_{equipe_sel}",
            f"comp_sel_{equipe_sel}", f"exp_sel_{equipe_sel}",
        ):
            st.session_state.pop(k, None)
        st.rerun()

    if st.button("➕ Inserir substituição retroativa", use_container_width=True, key="retro_btn"):
        aplicar_retro()

    if "flash_text" in st.session_state or "flash_html" in st.session_state:
        if "flash_text" in st.session_state:
            st.success(st.session_state["flash_text"], icon="🔁")
        if "flash_html" in st.session_state:
            st.markdown(st.session_state["flash_html"], unsafe_allow_html=True)
        st.session_state.pop("flash_text", None)
        st.session_state.pop("flash_html", None)


# =====================================================
# ABA 4 — VISUALIZAÇÃO DE DADOS (auto)
# =====================================================
with abas[3]:
    import pandas as pd

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
                s = st.session_state["stats"][eq].setdefault(num, {"jogado_1t":0,"jogado_2t":0,"banco":0,"doismin":0})
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
            if int(p["numero"]) != int(numero): continue
            a, b = float(p["start"]), float(p["end"])
            cumprido = max(0.0, min(agora_elapsed, b) - a)
            total_sec += cumprido
        return total_sec / 60.0

    def _stats_to_dataframe():
        rows = []
        for eq in ["A", "B"]:
            cor = st.session_state["cores"].get(eq, "#333")
            for j in st.session_state["equipes"].get(eq, []):
                num = int(j["numero"])
                est = j.get("estado", "banco")
                exc = j.get("exclusoes", 0)
                s = st.session_state["stats"][eq].get(num, {"jogado_1t":0, "jogado_2t":0, "banco":0, "doismin":0})
                j1 = s["jogado_1t"] / 60.0
                j2 = s["jogado_2t"] / 60.0
                jog_total = j1 + j2
                banco_min = s["banco"] / 60.0
                agora_elapsed = tempo_logico_atual()
                dois_min = round(_doismin_por_jogador_agora(eq, num, agora_elapsed), 1)
                rows.append({
                    "Equipe": eq,
                    "Número": num,
                    "Estado": est,
                    "Exclusões": exc,
                    "Jogado 1ºT (min)": round(j1, 1),
                    "Jogado 2ºT (min)": round(j2, 1),
                    "Jogado Total (min)": round(jog_total, 1),
                    "Banco (min)": round(banco_min, 1),
                    "2 min (min)": round(dois_min, 1),
                    "CorEquipe": cor,
                })
        return pd.DataFrame(rows).sort_values(["Equipe", "Número"]) if rows else pd.DataFrame()

    st.subheader("Visualização de Dados")

    cauto1, cauto2 = st.columns([1, 1])
    with cauto1:
        st.session_state["viz_auto"] = st.toggle(
            "Atualizar automaticamente (1s)",
            value=st.session_state["viz_auto"],
            help="Recalcula os tempos a cada segundo apenas nesta aba."
        )
    with cauto2:
        st.session_state["viz_interval"] = st.number_input(
            "Intervalo (s)", min_value=0.5, max_value=5.0, step=0.5,
            value=float(st.session_state["viz_interval"]),
            help="Intervalo da atualização automática desta aba."
        )

    _accumulate_time_tick()

    df = _stats_to_dataframe()
    if df.empty:
        st.info("Sem dados ainda. Cadastre equipes, defina titulares e inicie o controle do jogo.")
    else:
        for eq in ["A", "B"]:
            sub = df[df["Equipe"] == eq].copy()
            if sub.empty: continue
            cor = sub["CorEquipe"].iloc[0]
            st.markdown(
                f"<div style='background:{cor};color:#fff;padding:6px 10px;border-radius:8px;font-weight:700;margin-top:8px;'>{get_team_name(eq)}</div>",
                unsafe_allow_html=True
            )
            st.dataframe(sub.drop(columns=["CorEquipe"]), use_container_width=True)

        st.markdown("---")
        st.markdown("#### Relatório combinado")
        st.dataframe(df.drop(columns=["CorEquipe"]), use_container_width=True)

        csv = df.drop(columns=["CorEquipe"]).to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar CSV (todas as equipes)", data=csv, file_name="relatorio_tempos.csv", mime="text/csv")

    if st.session_state["viz_auto"]:
        time.sleep(float(st.session_state["viz_interval"]))
        st.rerun()
