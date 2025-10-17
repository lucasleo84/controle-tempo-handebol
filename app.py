# app.py
import time
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Controle de Tempo Handebol", page_icon="⏱", layout="wide")

# =====================================================
# 🔧 ESTADO GLOBAL / HELPERS
# =====================================================
def _init_globals():
    if "equipes" not in st.session_state:
        st.session_state["equipes"] = {"A": [], "B": []}
    if "cores" not in st.session_state:
        st.session_state["cores"] = {"A": "#00AEEF", "B": "#00D1C7"}
    if "nome_A" not in st.session_state:
        st.session_state["nome_A"] = "Equipe A"
    if "nome_B" not in st.session_state:
        st.session_state["nome_B"] = "Equipe B"

    # cronômetro principal
    if "iniciado" not in st.session_state:
        st.session_state["iniciado"] = False
    if "ultimo_tick" not in st.session_state:
        st.session_state["ultimo_tick"] = time.time()
    if "cronometro" not in st.session_state:
        st.session_state["cronometro"] = 0.0
    if "periodo" not in st.session_state:
        st.session_state["periodo"] = "1º Tempo"
    if "period_start_elapsed" not in st.session_state:
        st.session_state["period_start_elapsed"] = 0.0

    if "invert_lados" not in st.session_state:
        st.session_state["invert_lados"] = False

    # penalidades 2'
    if "penalties" not in st.session_state:
        st.session_state["penalties"] = {"A": [], "B": []}  # {numero,start,end,consumido}

    # estatísticas (segundos)
    if "stats" not in st.session_state:
        st.session_state["stats"] = {"A": {}, "B": {}}

_init_globals()

def get_team_name(eq: str) -> str:
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"

def _ensure_player_stats(eq: str, numero: int):
    return st.session_state["stats"][eq].setdefault(int(numero), {
        "jogado_1t": 0.0, "jogado_2t": 0.0, "banco": 0.0, "doismin": 0.0
    })

def atualizar_estado(eq: str, numero: int, novo_estado: str) -> bool:
    for j in st.session_state["equipes"][eq]:
        if int(j["numero"]) == int(numero):
            j["estado"] = novo_estado
            return True
    return False

def jogadores_por_estado(eq: str, estado: str):
    return [int(j["numero"]) for j in st.session_state["equipes"][eq]
            if j.get("elegivel", True) and j.get("estado") == estado]

def elenco(eq: str):
    return [int(j["numero"]) for j in st.session_state["equipes"][eq] if j.get("elegivel", True)]

def tempo_logico_atual() -> float:
    if st.session_state["iniciado"]:
        return st.session_state["cronometro"] + (time.time() - st.session_state["ultimo_tick"])
    return st.session_state["cronometro"]

def _parse_mmss(txt: str) -> int | None:
    try:
        mm, ss = txt.strip().split(":")
        m, s = int(mm), int(ss)
        if m < 0 or s < 0 or s >= 60:
            return None
        return m*60 + s
    except Exception:
        return None

# =====================================================
# CRONÔMETRO / PENALIDADES – estado
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
    st.session_state["period_start_elapsed"] = 0.0

def _registrar_exclusao(eq: str, numero: int, start_elapsed: float):
    st.session_state["penalties"][eq].append({
        "numero": int(numero),
        "start": float(start_elapsed),
        "end": float(start_elapsed) + 120.0,
        "consumido": False
    })
    atualizar_estado(eq, numero, "excluido")

def _penalidades_ativas(eq: str, agora_elapsed: float):
    return [p for p in st.session_state["penalties"].get(eq, []) if (agora_elapsed < p["end"]) and not p["consumido"]]

def _penalidades_concluidas_nao_consumidas(eq: str, agora_elapsed: float):
    return [p for p in st.session_state["penalties"].get(eq, []) if (agora_elapsed >= p["end"]) and not p["consumido"]]

def _penalidade_top(eq: str, agora_elapsed: float):
    ativas = _penalidades_ativas(eq, agora_elapsed)
    if not ativas:
        return (None, 0)
    p = min(ativas, key=lambda x: x["end"])
    restante = max(0, int(round(p["end"] - agora_elapsed)))
    return (int(p["numero"]), int(restante))

# =====================================================
# 🎛️ LAYOUT: PLACAR FIXO + ABAS FIXAS (só o conteúdo rola)
# =====================================================
def render_top_scoreboard():
    iniciado    = bool(st.session_state["iniciado"])
    base_elapsed= float(st.session_state["cronometro"])
    start_epoch = float(st.session_state["ultimo_tick"]) if iniciado else None

    agora = tempo_logico_atual()
    numA, restA = _penalidade_top("A", agora)
    numB, restB = _penalidade_top("B", agora)

    corA  = st.session_state["cores"].get("A", "#00AEEF")
    corB  = st.session_state["cores"].get("B", "#00D1C7")
    nomeA = get_team_name("A")
    nomeB = get_team_name("B")

    SCORE_H = 120   # altura do placar
    TABS_H  = 46    # altura aproximada da barra de abas do Streamlit

    st.markdown(f"""
    <style>
      :root {{
        --scoreH: {SCORE_H}px;
        --tabsH:  {TABS_H}px;
      }}
      /* Desloca conteúdo para baixo do placar + tabs */
      .block-container {{
        padding-top: calc(var(--scoreH) + var(--tabsH) + 12px) !important;
      }}

      /* ===== PLACAR FIXO ===== */
      .score-fixed {{
        position: fixed; top: 0; left: 0; right: 0;
        z-index: 1000;
        background: linear-gradient(180deg,#0a0a0a 0%, #0e0e0e 100%);
        border-bottom: 2px solid #222;
        box-shadow: 0 6px 14px rgba(0,0,0,.35);
      }}
      .score-inner {{ max-width: 1100px; margin: 6px auto; padding: 8px 12px; }}
      .score-grid {{ display:grid; grid-template-columns: 1fr auto 1fr; gap:16px; align-items:center; }}

      .team-box   {{ display:flex; flex-direction:column; gap:6px; }}
      .team-name  {{ color:#fff; font-weight:800; padding:8px 14px; border-radius:12px; font-size:16px;
                     letter-spacing:.3px; box-shadow:0 2px 6px rgba(0,0,0,.35); }}
      .mini-box   {{ font-family:'Courier New', monospace; font-size:20px; font-weight:800; text-align:center;
                     color:#FF5555; background:#111; padding:6px 10px; border-radius:10px;
                     border:1px solid #333; box-shadow: inset 0 0 10px rgba(255,255,255,.04); min-height:36px; }}

      .clock      {{ font-family:'Courier New', monospace; font-size:64px; line-height:1; font-weight:900;
                     color:#FFD700; background:#000; padding:10px 24px; border-radius:14px;
                     letter-spacing:4px; text-align:center; min-width: 320px;
                     border:1px solid #333; box-shadow:0 0 22px rgba(255,215,0,.35),
                                               inset 0 0 18px rgba(255,255,255,.06);
                     text-shadow:0 0 10px rgba(255,215,0,.45); }}

      .stButton>button.score-btn {{ background:#222; color:#fff; border:1px solid #444; border-radius:10px;
                                   padding:6px 12px; font-weight:700; }}
      .stButton>button.score-btn:hover {{ background:#2d2d2d; }}

      /* ===== ABAS FIXAS ===== */
      div[data-baseweb="tab-list"] {{
        position: fixed;
        top: var(--scoreH);
        left: 0; right: 0;
        z-index: 900;
        background: var(--background-color, #0e0e0e00);
        backdrop-filter: blur(2px);
        padding: 6px 16px 6px 16px;
        box-shadow: 0 4px 10px rgba(0,0,0,.12);
      }}
      div[data-baseweb="tab-list"] > div {{ max-width: 1100px; margin: 0 auto; }}
    </style>
    """, unsafe_allow_html=True)

    # HTML do placar fixo
    st.markdown('<div class="score-fixed"><div class="score-inner">', unsafe_allow_html=True)
    colL, colC, colR = st.columns([1, 1, 1])

    with colL:
        st.markdown(
            f'<div class="team-box"><div class="team-name" style="background:{corA};">{nomeA}</div>'
            f'<div id="penA" class="mini-box">-</div></div>',
            unsafe_allow_html=True
        )
    with colC:
        components.html(f"""
          <div id="clock" class="clock">00:00</div>
          <script>
            (function(){{
              const el = document.currentScript.previousElementSibling;
              const iniciado   = {str(iniciado).lower()};
              const baseElapsed= {base_elapsed};
              const startEpoch = {json.dumps(start_epoch)};
              function fmt(sec){{
                sec = Math.max(0, Math.floor(sec));
                const m = Math.floor(sec/60), s = sec%60;
                return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
              }}
              function tick(){{
                let e = baseElapsed;
                if (iniciado && startEpoch) {{
                  const now = Date.now()/1000;
                  e = baseElapsed + (now - startEpoch);
                }}
                el.textContent = fmt(e);
                window.__raf_clock && cancelAnimationFrame(window.__raf_clock);
                window.__raf_clock = requestAnimationFrame(tick);
              }}
              tick();
            }})();
          </script>
        """, height=96)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⏯ Iniciar / Pausar", key="btn_toggle", use_container_width=True,
                         help="Alterna entre iniciar e pausar", type="secondary", kwargs=None):
                if st.session_state["iniciado"]:
                    pausar()
                else:
                    iniciar()
                st.rerun()
        with c2:
            if st.button("🔁 Zerar", key="btn_reset", use_container_width=True, type="secondary"):
                zerar()
                st.rerun()

    with colR:
        st.markdown(
            f'<div class="team-box" style="align-items:end;"><div class="team-name" style="background:{corB};">{get_team_name("B")}</div>'
            f'<div id="penB" class="mini-box">-</div></div>',
            unsafe_allow_html=True
        )

    # timers 2' no placar
    components.html(f"""
      <script>
        (function(){{
          const boxA = parent.document.querySelector('div#penA');
          const boxB = parent.document.querySelector('div#penB');
          let nA = {json.dumps(numA)}, rA = {int(restA)};
          let nB = {json.dumps(numB)}, rB = {int(restB)};
          const beep = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
          function upd(el,secs,num){{
            if(!el) return;
            if(!secs || secs<=0 || !num){{ el.textContent='-'; return; }}
            const m = String(Math.floor(secs/60)).padStart(2,'0');
            const s = String(secs%60).padStart(2,'0');
            el.textContent = '#' + String(num) + ' ' + m + ':' + s;  // <- ajuste o formato aqui, se quiser
          }}
          function tickA(){{
            if(!rA) return;
            rA = Math.max(0, rA-1); upd(boxA,rA,nA); if(rA===0){{try{{beep.play();}}catch(e){{}}}}
          }}
          function tickB(){{
            if(!rB) return;
            rB = Math.max(0, rB-1); upd(boxB,rB,nB); if(rB===0){{try{{beep.play();}}catch(e){{}}}}
          }}
          upd(boxA,rA,nA); upd(boxB,rB,nB);
          if(window.__intA) clearInterval(window.__intA);
          if(window.__intB) clearInterval(window.__intB);
          if(rA>0) window.__intA = setInterval(tickA,1000);
          if(rB>0) window.__intB = setInterval(tickB,1000);
        }})();
      </script>
    """, height=0)

    st.markdown('</div></div>', unsafe_allow_html=True)

# — desenha placar + fixa abas —
render_top_scoreboard()

# =====================================================
# 🧭 ABAS
# =====================================================
abas = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

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
            st.markdown(f"### {get_team_name(eq)}")
            # Nome sem value= (evita sobrescrever ao salvar a outra equipe)
            st.text_input(f"Nome da equipe {eq}", key=f"nome_{eq}")
            qtd_default = len(st.session_state["equipes"][eq]) or 7
            qtd = st.number_input(f"Quantidade de jogadores ({eq})",
                                  min_value=1, max_value=20, step=1,
                                  value=qtd_default, key=f"qtd_{eq}")
            ensure_num_list(eq, int(qtd))

            st.markdown("**Números das camisetas:**")
            cols = st.columns(5)
            for i, num in enumerate(st.session_state[f"numeros_{eq}"]):
                with cols[i % 5]:
                    novo = st.number_input(f"Jogador {i+1}", min_value=0, max_value=999, step=1,
                                           value=int(num), key=f"{eq}_num_{i}")
                    st.session_state[f"numeros_{eq}"][i] = int(novo)

            st.session_state["cores"][eq] = st.color_picker(f"Cor da equipe {eq}",
                                                            value=st.session_state["cores"][eq],
                                                            key=f"cor_{eq}")

            if st.button(f"Salvar equipe {eq}", key=f"save_team_{eq}"):
                numeros = list(dict.fromkeys(st.session_state[f"numeros_{eq}"]))
                st.session_state["equipes"][eq] = [
                    {"numero": int(n), "estado": "banco", "elegivel": True, "exclusoes": 0} for n in numeros
                ]
                st.session_state["penalties"][eq] = []
                st.session_state["stats"][eq] = {}
                for k in (f"sai_{eq}", f"entra_{eq}", f"doismin_sel_{eq}", f"comp_sel_{eq}", f"exp_sel_{eq}"):
                    st.session_state.pop(k, None)
                st.success(f"Equipe {eq} salva com {len(numeros)} jogadores.")

# =====================================================
# ABA 2 — TITULARES (opcional; corrige retroativamente)
# =====================================================
with abas[1]:
    st.subheader("Definir Titulares (opcional; corrige retroativamente o período atual)")

    for eq in ["A", "B"]:
        st.markdown(f"### {get_team_name(eq)}")
        jogadores = st.session_state["equipes"][eq]
        if not jogadores:
            st.info(f"Cadastre primeiro {get_team_name(eq)} na aba anterior.")
            continue

        numeros = [j["numero"] for j in jogadores]
        titulares_sel = st.multiselect(
            "Selecione quem está/esteve em quadra desde o início do período",
            options=numeros,
            default=[j["numero"] for j in jogadores if j.get("estado") == "jogando"],
            key=f"titulares_sel_{eq}",
        )

        if st.button(f"Aplicar titulares ({eq})", key=f"registrar_tit_{eq}"):
            elapsed_period = max(0.0, tempo_logico_atual() - st.session_state["period_start_elapsed"])
            jog_key = "jogado_1t" if st.session_state["periodo"] == "1º Tempo" else "jogado_2t"
            sel = set(map(int, titulares_sel))

            for j in st.session_state["equipes"][eq]:
                num = int(j["numero"])
                s = _ensure_player_stats(eq, num)

                # ignora expulso/excluído
                if j.get("estado") in ("excluido", "expulso"):
                    continue

                if num in sel:
                    desired = elapsed_period
                    cur     = s[jog_key]
                    if desired > cur:
                        delta = desired - cur
                        s[jog_key] += delta
                        s["banco"] = max(0.0, s["banco"] - delta)
                    j["estado"] = "jogando"; j["elegivel"] = True
                else:
                    cur = s[jog_key]
                    if cur > 0:
                        s["banco"] += cur
                        s[jog_key] = 0.0
                    j["estado"] = "banco"; j["elegivel"] = True

            st.success("Titulares aplicados com correção retroativa do período.")

# =====================================================
# ABA 3 — CONTROLE DO JOGO
# =====================================================
def painel_equipe(eq: str):
    cor = st.session_state["cores"].get(eq, "#333")
    nome = get_team_name(eq)
    st.markdown(
        f"<div style='color:#fff;background:{cor};padding:6px 10px;border-radius:8px;font-weight:700;margin-bottom:6px;'>{nome}</div>",
        unsafe_allow_html=True
    )

    jogadores = st.session_state["equipes"][eq]
    on_court  = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "jogando" and j.get("elegivel", True)])
    excluidos = sorted([int(j["numero"]) for j in jogadores if j.get("estado") == "excluido" and j.get("elegivel", True)])

    chips = []
    for n in on_court:
        chips.append(f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#e8ffe8;color:#0b5;border:1px solid #bfe6bf;'>#{n}</span>")
    for n in excluidos:
        chips.append(f"<span style='display:inline-block;padding:2px 6px;border-radius:6px;font-size:12px;margin-right:6px;background:#f2f3f5;color:#888;border:1px solid #dcdfe3;opacity:.8;'>#{n}</span>")
    st.markdown(f"<div style='margin:6px 0 10px;'>{''.join(chips) if chips else '<span style=\"color:#666;\">Nenhum jogador em quadra.</span>'}</div>", unsafe_allow_html=True)

    # Substituição
    st.markdown("**🔁 Substituição**")
    c1, c2, c3 = st.columns([1, 1, 1])
    list_sai   = jogadores_por_estado(eq, "jogando")
    list_entra = jogadores_por_estado(eq, "banco")
    sai   = c1.selectbox("Sai",   list_sai,   key=f"sai_{eq}")
    entra = c2.selectbox("Entra", list_entra, key=f"entra_{eq}")
    if c3.button("Confirmar", key=f"btn_sub_{eq}", disabled=(not list_sai or not list_entra)):
        atualizar_estado(eq, sai, "banco")
        atualizar_estado(eq, entra, "jogando")
        st.success(f"Substituição: Sai {sai} / Entra {entra}", icon="🔁")
    st.markdown("---")

    # 2 minutos
    st.markdown("**⛔ 2 minutos**")
    jogadores_all = elenco(eq)
    jog_2m = st.selectbox("Jogador", jogadores_all, key=f"doismin_sel_{eq}")
    if st.button("Aplicar 2'", key=f"btn_2min_{eq}", disabled=(len(jogadores_all) == 0)):
        start = tempo_logico_atual()
        _registrar_exclusao(eq, jog_2m, start_elapsed=start)
        st.warning(f"Jogador {jog_2m} excluído por 2 minutos (placar no topo mostra # e contagem).")

    # Completou
    st.markdown("---")
    st.markdown("**✅ Completou**")
    agora = tempo_logico_atual()
    concluidas = _penalidades_concluidas_nao_consumidas(eq, agora)
    elegiveis_retorno = jogadores_por_estado(eq, "banco") + jogadores_por_estado(eq, "excluido")
    comp = st.selectbox("Jogador que entra", elegiveis_retorno, key=f"comp_sel_{eq}")
    if st.button("Confirmar retorno", key=f"btn_comp_{eq}", disabled=(len(elegiveis_retorno) == 0)):
        if not concluidas:
            st.error("Ainda não há exclusões concluídas. Aguarde.")
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
        for j in st.session_state["equipes"][eq]:
            if int(j["numero"]) == int(exp):
                j["estado"] = "expulso"
                j["elegivel"] = False
                break
        st.error(f"Jogador {exp} expulso.")

with abas[2]:
    st.subheader("Controle do Jogo")

    new_period = st.selectbox("Período", ["1º Tempo", "2º Tempo"],
                              index=0 if st.session_state["periodo"] == "1º Tempo" else 1, key="sel_periodo")
    if new_period != st.session_state["periodo"]:
        st.session_state["periodo"] = new_period
        st.session_state["period_start_elapsed"] = tempo_logico_atual()
        st.info(f"Início lógico do {new_period} marcado em {int(st.session_state['period_start_elapsed'])}s.")

    st.session_state["invert_lados"] = st.toggle("Inverter lados (A ⇄ B)", value=st.session_state["invert_lados"])
    lados = ("A", "B") if not st.session_state["invert_lados"] else ("B", "A")

    col_esq, col_dir = st.columns(2)
    with col_esq:
        if st.session_state["equipes"][lados[0]]:
            st.markdown(f"#### {get_team_name(lados[0])}")
            painel_equipe(lados[0])
        else:
            st.info(f"Cadastre {get_team_name(lados[0])} na aba de Configuração.")
    with col_dir:
        if st.session_state["equipes"][lados[1]]:
            st.markdown(f"#### {get_team_name(lados[1])}")
            painel_equipe(lados[1])
        else:
            st.info(f"Cadastre {get_team_name(lados[1])} na aba de Configuração.")

    st.divider()
    st.markdown("## 📝 Substituições avulsas (retroativas)")
    col_eq, col_time = st.columns([1, 1])
    with col_eq:
        equipe_sel = st.radio("Equipe", ["A", "B"], horizontal=True, key="retro_eq",
                              format_func=lambda x: get_team_name(x))
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
        tempo_str = st.text_input("Tempo do jogo (MM:SS)", value="00:00", key="retro_tempo",
                                  help="Ex.: 12:34 = ocorreu aos 12min34s.")

    def aplicar_retro():
        t_mark = _parse_mmss(tempo_str)
        if t_mark is None:
            st.error("Tempo inválido. Use o formato MM:SS.")
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

        st.success(f"Substituição retroativa realizada: Sai {sai_num} / Entra {entra_num}", icon="🔁")

    if st.button("➕ Inserir substituição retroativa", use_container_width=True, key="retro_btn"):
        aplicar_retro()

# =====================================================
# ABA 4 — VISUALIZAÇÃO
# =====================================================
with abas[3]:
    st.subheader("Visualização de Dados")

    if "last_accum" not in st.session_state:
        st.session_state["last_accum"] = time.time()

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

    def _doismin_por_jogador_agora(eq: str, numero: int) -> float:
        total_sec = 0.0
        now = tempo_logico_atual()
        for p in st.session_state["penalties"].get(eq, []):
            if int(p["numero"]) != int(numero):
                continue
            a, b = float(p["start"]), float(p["end"])
            cumprido = max(0.0, min(now, b) - a)
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
                j1 = s["jogado_1t"]/60.0; j2 = s["jogado_2t"]/60.0
                rows.append({
                    "Equipe": get_team_name(eq),
                    "Número": num,
                    "Estado": est,
                    "Exclusões": exc,
                    "Jogado 1ºT (min)": round(j1,1),
                    "Jogado 2ºT (min)": round(j2,1),
                    "Jogado Total (min)": round(j1+j2,1),
                    "Banco (min)": round(s["banco"]/60.0,1),
                    "2 min (min)": round(_doismin_por_jogador_agora(eq, num),1),
                })
        return pd.DataFrame(rows).sort_values(["Equipe","Número"]) if rows else pd.DataFrame()

    _accumulate_time_tick()
    df = _stats_to_dataframe()
    if df.empty:
        st.info("Sem dados ainda. Cadastre equipes, (opcionalmente) defina titulares e use os controles do jogo.")
    else:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Baixar CSV", data=df.to_csv(index=False).encode("utf-8"),
                           file_name="relatorio_tempos.csv", mime="text/csv")
