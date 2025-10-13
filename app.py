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
    """Nome configurado da equipe (A/B), com fallback."""
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"

def atualizar_estado(eq: str, numero: int, novo_estado: str) -> bool:
    """Muda o estado do jogador (jogando|banco|excluido|expulso)."""
    for j in st.session_state["equipes"][eq]:
        if int(j["numero"]) == int(numero):
            j["estado"] = novo_estado
            return True
    return False

def jogadores_por_estado(eq: str, estado: str):
    """Lista de jogadores elegíveis (não-expulsos) no estado informado."""
    return [
        int(j["numero"])
        for j in st.session_state["equipes"][eq]
        if j.get("elegivel", True) and j.get("estado") == estado
    ]

def elenco(eq: str):
    """Todos os jogadores elegíveis (não-expulsos)."""
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
        """Garante uma lista editável de números por equipe de tamanho 'qtd'."""
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

            nome = st.text_input(f"Nome da equipe {eq}", key=f"nome_{eq}")
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
                numeros = list(dict.fromkeys(st.session_state[f"numeros_{eq}"]))  # sem duplicatas
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

# ---------- Estado mínimo do relógio e dados ----------
def _init_clock_state():
    if "iniciado" not in st.session_state: st.session_state["iniciado"] = False
    if "ultimo_tick" not in st.session_state: st.session_state["ultimo_tick"] = time.time()
    if "cronometro" not in st.session_state: st.session_state["cronometro"] = 0.0
    if "periodo" not in st.session_state: st.session_state["periodo"] = "1º Tempo"
    if "invert_lados" not in st.session_state: st.session_state["invert_lados"] = False
    if "penalties" not in st.session_state:
        # penalties[eq] = [{numero, start, end, consumido}]
        st.session_state["penalties"] = {"A": [], "B": []}
    if "stats" not in st.session_state:
        st.session_state["stats"] = {"A": {}, "B": {}}

# ---------- Penalidades: helpers ----------
def _equipe_penalidades(eq: str):
    return st.session_state["penalties"].get(eq, [])

def _registrar_exclusao(eq: str, numero: int, start_elapsed: float):
    st.session_state["penalties"][eq].append({
        "numero": int(numero),
        "start": float(start_elapsed),
        "end": float(start_elapsed) + 120.0,  # 2 minutos = 120s
        "consumido": False
    })

def _penalidades_ativas(eq: str, agora_elapsed: float):
    return [p for p in _equipe_penalidades(eq) if (agora_elapsed < p["end"]) and not p["consumido"]]

def _penalidades_concluidas_nao_consumidas(eq: str, agora_elapsed: float):
    return [p for p in _equipe_penalidades(eq) if (agora_elapsed >= p["end"]) and not p["consumido"]]

# ---------- Cronômetro principal (JS fixo) ----------
def render_cronometro_js():
    iniciado = "true" if st.session_state["iniciado"] else "false"
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if st.session_state["iniciado"] else None

    st.markdown("""
        <style>
        .cronofixo { position: sticky; top: 0; z-index: 999; text-align:center; padding:6px 0; background:#fff;
                     border-bottom:1px solid #e5e7eb; margin-bottom:10px; }
        .digital { font-family:'Courier New', monospace; font-size:28px; font-weight:700;
                   color:#FFD700; background:#000; padding:6px 16px; border-radius:8px;
                   letter-spacing:2px; box-shadow:0 0 8px rgba(255,215,0,.4); display:inline-block; }
        .team-head { color:#fff; padding:6px 10px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:8px; }
        .sec-title { font-size:14px; font-weight:700; margin:6px 0 4px; }
        .compact .stSelectbox label, .compact .stButton button, .compact .stRadio label { font-size:13px!important; }
        .chip { display:inline-block; padding:2px 6px; border-radius:6px; font-size:12px; margin-left:6px; }
        .chip-sai { background:#ffe5e5; color:#a30000; } .chip-ent { background:#e7ffe7; color:#005a00; }
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
    components.html(html, height=62)

# ---------- Botões do relógio ----------
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

# ---------- Utilitários de tempo / stats (compartilhados) ----------
def _ensure_player_stats(eq: str, numero: int):
    if "stats" not in st.session_state:
        st.session_state["stats"] = {"A": {}, "B": {}}
    return st.session_state["stats"][eq].setdefault(int(numero), {
        "jogado_1t": 0.0, "jogado_2t": 0.0, "banco": 0.0, "doismin": 0.0
    })

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

# ---------- Painel da equipe ----------
def painel_equipe(eq: str):
    cor = st.session_state["cores"].get(eq, "#333")
    nome = get_team_name(eq)
    st.markdown(f"<div class='team-head' style='background:{cor};'>{nome}</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='compact'>", unsafe_allow_html=True)

        # --- Substituição ---
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

        # --- 2 minutos & Completou ---
        cols_pen = st.columns([1, 1])

        with cols_pen[0]:
            st.markdown("<div class='sec-title'>⛔ 2 minutos</div>", unsafe_allow_html=True)
            jogadores_all = elenco(eq)
            jog_2m = st.selectbox("Jogador", jogadores_all, key=f"doismin_sel_{eq}")
            if st.button("Aplicar 2'", key=f"btn_2min_{eq}", disabled=(len(jogadores_all) == 0)):
                atualizar_estado(eq, jog_2m, "excluido")
                start = tempo_logico_atual()
                _registrar_exclusao(eq, jog_2m, start_elapsed=start)
                st.warning(f"Jogador {jog_2m} excluído por 2 minutos.")

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

        st.markdown("---")

        # --- Expulsão ---
        st.markdown("<div class='sec-title'>🟥 Expulsão</div>", unsafe_allow_html=True)
        jogadores_all = elenco(eq)
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

        st.markdown("</div>", unsafe_allow_html=True)

# ---------- Render da ABA 3 ----------
with abas[2]:
    _init_clock_state()
    st.subheader("Controle do Jogo")

    # Linha do relógio e período
    cc1, cc2, cc3, cc4, cc5 = st.columns([1, 1, 1, 1, 1])
    with cc1:
        if st.button("▶️ Iniciar", key="clk_start"): iniciar()
    with cc2:
        if st.button("⏸️ Pausar", key="clk_pause"): pausar()
    with cc3:
        if st.button("🔁 Zerar", key="clk_reset"): zerar()
    with cc4:
        st.session_state["periodo"] = st.selectbox(
            "Período", ["1º Tempo", "2º Tempo"],
            index=0 if st.session_state["periodo"] == "1º Tempo" else 1,
            key="sel_periodo"
        )
    with cc5:
        st.session_state["invert_lados"] = st.toggle("Inverter lados (A ⇄ B)", value=st.session_state["invert_lados"])

    # Cronômetro JS
    render_cronometro_js()

    # Painéis lado a lado — respeitando “Inverter lados”
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

    # -------------------- Penalidades ativas (persistentes) --------------------
    st.markdown("### Penalidades ativas")
    agora = tempo_logico_atual()

    def _render_pen_timers(eq: str):
        ativas = _penalidades_ativas(eq, agora)
        if not ativas:
            st.caption(f"{get_team_name(eq)}: nenhuma penalidade ativa.")
            return
        st.markdown(f"**{get_team_name(eq)}**")
        for p in ativas:
            restante = max(0, int(round(p["end"] - agora)))
            minutos = restante // 60
            segundos = restante % 60
            elem_id = f"pen_{eq}_{p['numero']}_{int(p['start'])}"  # id único

            html_tpl = Template("""
            <div style="margin:6px 0;">
              <div style="display:flex;align-items:center;gap:8px;">
                <div style="font-size:13px;">#$numero — resta:</div>
                <div id="$elem_id" style="font-family:'Courier New';font-size:18px;color:#FF3333;background:#111;padding:3px 10px;border-radius:6px;display:inline-block;text-shadow:0 0 6px red;">$mm:$ss</div>
              </div>
            </div>
            <script>
              (function(){
                let r = $restante;
                const el = document.getElementById("$elem_id");
                const beep = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
                function tick(){
                  r = Math.max(0, r-1);
                  const m = String(Math.floor(r/60)).padStart(2,'0');
                  const s = String(r%60).padStart(2,'0');
                  if (el) el.textContent = m + ":" + s;
                  if (r <= 0) { try { beep.play(); } catch(e) {} clearInterval(window["timer_$elem_id"]); }
                }
                if (window["timer_$elem_id"]) clearInterval(window["timer_$elem_id"]);
                window["timer_$elem_id"] = setInterval(tick, 1000);
              })();
            </script>
            """)
            html = html_tpl.substitute(
                numero=int(p["numero"]),
                elem_id=elem_id,
                mm=f"{minutos:02d}",
                ss=f"{segundos:02d}",
                restante=int(restante),
            )
            components.html(html, height=48)

    colA_t, colB_t = st.columns(2)
    with colA_t: _render_pen_timers(lados[0])
    with colB_t: _render_pen_timers(lados[1])

    # -----------------------------------------------------
    # Substituições avulsas (retroativas) — sempre aplica ao estado atual
    # -----------------------------------------------------
    st.divider()
    st.markdown("## 📝 Substituições avulsas (retroativas)")

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
        st.success(
            f"Retroativo aplicado ({periodo_sel}) em {get_team_name(equipe_sel)}: "
            f"Sai {sai_num} (−{mm_dt:02d}:{ss_dt:02d} jogado, + banco) | "
            f"Entra {entra_num} (+ jogado, − banco) a partir de {tempo_str} até agora."
        )

        # 💬 Feedback visual como nas outras ações
        st.success(f"Substituição retroativa realizada: Sai {sai_num} / Entra {entra_num}", icon="🔁")
        st.markdown(
            f"<span class='chip chip-sai'>Sai {sai_num}</span>"
            f"<span class='chip chip-ent'>Entra {entra_num}</span>",
            unsafe_allow_html=True
        )
        # (opcional) toast discreto no canto
        st.toast("Substituição retroativa registrada", icon="✅")
     
        # --- NOVO: limpa seleções de UI dessa equipe para não “grudar” valores antigos
        for k in (
            f"sai_{equipe_sel}",
            f"entra_{equipe_sel}",
            f"doismin_sel_{equipe_sel}",
            f"comp_sel_{equipe_sel}",
            f"exp_sel_{equipe_sel}",
        ):
            
            # 💬 preparar mensagem "flash" para aparecer após o rerun
            st.session_state["flash_text"] = f"Substituição retroativa realizada: Sai {sai_num} / Entra {entra_num}"
            st.session_state["flash_html"] = (
                f"<span class='chip chip-sai'>Sai {sai_num}</span>"
                f"<span class='chip chip-ent'>Entra {entra_num}</span>"
            )

    # Limpa seleções de UI dessa equipe e força re-render
    for k in (
        f"sai_{equipe_sel}", f"entra_{equipe_sel}", f"doismin_sel_{equipe_sel}",
        f"comp_sel_{equipe_sel}", f"exp_sel_{equipe_sel}",
    ):
        st.session_state.pop(k, None)

    st.rerun()


        
        # --- NOVO: força re-render IMEDIATO (listas “jogando”/“banco” sobem atualizadas)
        st.rerun()

    if st.button("➕ Inserir substituição retroativa", use_container_width=True, key="retro_btn"):
        aplicar_retro()


# =====================================================
# ABA 4 — VISUALIZAÇÃO DE DADOS (auto opcional)
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
