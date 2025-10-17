# -*- coding: utf-8 -*-
import json
import time
from typing import Dict, List

import streamlit as st
import streamlit.components.v1 as components

# =====================================================
# 🔧 ESTADO GLOBAL / HELPERS
# =====================================================
def _init_state():
    """Garante que todas as chaves do session_state existam."""
    ss = st.session_state
    if ss.get("_boot_ok"):
        return

    # Relógio principal
    ss.setdefault("iniciado", False)
    ss.setdefault("cronometro", 0.0)      # segundos acumulados
    ss.setdefault("ultimo_tick", None)    # epoch quando iniciou

    # Nomes e cores
    ss.setdefault("nome_A", "Equipe A")
    ss.setdefault("nome_B", "Equipe B")
    ss.setdefault("cores", {"A": "#16c1f3", "B": "#11e5cf"})

    # Elencos
    def _mk(qtd):
        return [{"numero": i + 1, "estado": "banco", "elegivel": True, "exclusoes": 0} for i in range(qtd)]
    ss.setdefault("equipes", {"A": _mk(7), "B": _mk(7)})

    # Penalidades ativas
    ss.setdefault("penalties", {"A": [], "B": []})

    ss["_boot_ok"] = True


def get_team_name(eq: str) -> str:
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"


def tempo_logico_atual() -> float:
    """Segundos do jogo considerando pausa/execução."""
    ss = st.session_state
    base = float(ss["cronometro"])
    if ss["iniciado"] and ss["ultimo_tick"]:
        base += time.time() - float(ss["ultimo_tick"])
    return base


def fmt_mmss(seg: int) -> str:
    seg = max(0, int(seg))
    m, s = divmod(seg, 60)
    return f"{m:02d}:{s:02d}"


# =====================================================
# ⏱️ CONTROLES DO CRONÔMETRO
# =====================================================
def iniciar():
    ss = st.session_state
    if not ss["iniciado"]:
        ss["iniciado"] = True
        ss["ultimo_tick"] = time.time()


def pausar():
    ss = st.session_state
    if ss["iniciado"]:
        now = time.time()
        ss["cronometro"] += now - float(ss["ultimo_tick"])
        ss["ultimo_tick"] = None
        ss["iniciado"] = False


def zerar():
    ss = st.session_state
    ss["iniciado"] = False
    ss["cronometro"] = 0.0
    ss["ultimo_tick"] = None


# =====================================================
# 👥 JOGADORES / ESTADOS
# =====================================================
def _lista(eq: str) -> List[Dict]:
    return st.session_state["equipes"][eq]


def jogadores(eq: str, estado: str = None, elegiveis=True) -> List[int]:
    out = []
    for j in _lista(eq):
        if (estado is None or j["estado"] == estado) and (not elegiveis or j["elegivel"]):
            out.append(int(j["numero"]))
    return sorted(out)


def _find(eq: str, numero: int) -> Dict:
    for j in _lista(eq):
        if int(j["numero"]) == int(numero):
            return j
    raise KeyError("Jogador não encontrado")


def atualizar_estado(eq: str, numero: int, novo: str):
    _find(eq, numero)["estado"] = novo


def aplicar_substituicao(eq: str, sai: int, entra: int):
    if sai == entra:
        return False, "Jogadores iguais."
    j_sai = _find(eq, sai)
    j_ent = _find(eq, entra)
    if j_sai["estado"] != "jogando":
        return False, f"#{sai} não está jogando."
    if j_ent["estado"] != "banco":
        return False, f"#{entra} não está no banco."
    if not j_ent["elegivel"]:
        return False, f"#{entra} está inelegível."
    j_sai["estado"] = "banco"
    j_ent["estado"] = "jogando"
    return True, f"Substituição: Sai #{sai} / Entra #{entra}"


def aplicar_dois_minutos(eq: str, numero: int):
    j = _find(eq, numero)
    if not j["elegivel"]:
        return False, f"#{numero} já está inelegível."
    now = tempo_logico_atual()
    st.session_state["penalties"][eq].append(
        {"numero": int(numero), "start": now, "end": now + 120.0, "consumido": False}
    )
    if j["estado"] == "jogando":
        j["estado"] = "banco"
    j["exclusoes"] += 1
    if j["exclusoes"] >= 3:
        j["elegivel"] = False
        return True, f"#{numero} recebeu a 3ª exclusão e está inelegível."
    return True, f"#{numero} excluído por 2 minutos."


def aplicar_completou(eq: str, numero: int):
    j = _find(eq, numero)
    if not j["elegivel"]:
        return False, "Jogador inelegível."
    j["estado"] = "jogando"
    return True, f"#{numero} voltou (completou)."


# =====================================================
# 🧷 PLACAR FIXO (somente “cartucho” central; fundo transparente)
# =====================================================
def render_top_scoreboard():
    ss = st.session_state

    iniciado = bool(ss["iniciado"])
    base_elapsed = float(ss["cronometro"])
    start_epoch = float(ss["ultimo_tick"]) if (iniciado and ss["ultimo_tick"]) else None

    def _pen(eq: str):
        now = tempo_logico_atual()
        ativas = [p for p in ss["penalties"].get(eq, []) if (now < p["end"]) and not p["consumido"]]
        if not ativas:
            return (None, 0)
        p = min(ativas, key=lambda x: x["end"])
        return (int(p["numero"]), max(0, int(round(p["end"] - now))))

    nA, rA = _pen("A")
    nB, rB = _pen("B")

    corA, corB = ss["cores"]["A"], ss["cores"]["B"]
    nomeA, nomeB = get_team_name("A"), get_team_name("B")

    SCORE_H = 120
    TABS_H = 46

    # CSS — fundo transparente; apenas a “caixa” central tem fundo
    st.markdown(
        f"""
    <style>
      :root {{
        --scoreH:{SCORE_H}px;
        --tabsH:{TABS_H}px;
      }}
      /* só conteúdo rola (placar e abas fixos) */
      .block-container {{
        padding-top: calc(var(--scoreH) + var(--tabsH) + 16px) !important;
      }}

      /* barra fixa transparente */
      .score-fixed {{
        position: fixed; top: 0; left: 0; right: 0; z-index: 1100;
        background: transparent;  /* <<< sem faixa preta na tela inteira */
        pointer-events: none;     /* botões seguem clicáveis dentro da caixa */
      }}

      /* caixa central esportiva */
      .score-wrap {{
        max-width: 1200px; margin: 10px auto 0 auto; height: var(--scoreH);
        display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px;
        padding: 8px 14px; pointer-events: auto;
        border-radius: 18px;
        background: radial-gradient(circle at 50% 20%, #111 0%, #0a0a0a 60%, #050505 100%);
        border: 1px solid #1f1f1f; box-shadow: 0 10px 24px rgba(0,0,0,.35);
      }}

      .team-box {{ display:flex; flex-direction:column; gap:8px; }}
      .team-name {{
        color:#0b0b0b; font-weight:900; letter-spacing:.3px;
        padding:10px 14px; border-radius:12px; box-shadow: 0 2px 8px rgba(0,0,0,.25);
      }}
      .mini-pen {{
        font-family:"Courier New", monospace; font-weight:800; font-size:18px; text-align:center;
        color:#ff5656; background:#111; border:1px solid #2d2d2d; border-radius:10px;
        box-shadow: inset 0 0 12px rgba(255,255,255,.06);
        min-height: 36px; padding:6px 10px;
      }}
      .clock-box {{ display:flex; flex-direction:column; align-items:center; gap:8px; }}
      .clock {{
        font-family:"Courier New", monospace; font-weight:900; letter-spacing:6px;
        font-size:64px; line-height:1; color:#FFD700; background:#000;
        padding:12px 28px; border-radius:14px; min-width:340px; text-align:center;
        border:1px solid #333;
        box-shadow: 0 0 26px rgba(255,215,0,.35), inset 0 0 22px rgba(255,255,255,.05);
        text-shadow: 0 0 14px rgba(255,215,0,.45);
      }}
      .stButton>button.score-btn {{
        background:#222; color:#fff; border:1px solid #444; border-radius:10px;
        padding:6px 12px; font-weight:700; margin: 0 6px;
      }}
      .stButton>button.score-btn:hover {{ background:#2e2e2e; }}

      /* Abas fixas logo abaixo do placar */
      div[data-baseweb="tab-list"] {{
        position: fixed; top: var(--scoreH); left: 0; right: 0;
        z-index: 1000; background: rgba(255,255,255,.65); backdrop-filter: blur(6px);
        box-shadow: 0 6px 14px rgba(0,0,0,.18);
      }}
      div[data-baseweb="tab-list"] > div {{ max-width: 1200px; margin: 0 auto; }}
    </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="score-fixed"><div class="score-wrap">', unsafe_allow_html=True)
    left, center, right = st.columns([1, 1, 1])

    with left:
        st.markdown(
            f"""
            <div class="team-box">
              <div class="team-name" style="background:{corA};">{nomeA}</div>
              <div id="penA" class="mini-pen">-</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with center:
        st.markdown('<div class="clock-box">', unsafe_allow_html=True)
        components.html(
            f"""
          <div id="clock" class="clock">00:00</div>
          <script>
            (function(){{
              const el = document.currentScript.previousElementSibling;
              const iniciado = {str(iniciado).lower()};
              const base = {base_elapsed};
              const start = {json.dumps(start_epoch) if start_epoch is not None else 'null'};
              function fmt(sec){{
                sec = Math.max(0, Math.floor(sec));
                const m = Math.floor(sec/60), s = sec%60;
                return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
              }}
              function draw(){{
                let e = base;
                if (iniciado && start){{
                  const now = Date.now()/1000;
                  e = base + (now - start);
                }}
                el.textContent = fmt(e);
                window.__raf && cancelAnimationFrame(window.__raf);
                window.__raf = requestAnimationFrame(draw);
              }}
              draw();
            }})();
          </script>
            """,
            height=96,
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⏯ Iniciar / Pausar", key="btn_toggle", use_container_width=True):
                st.session_state["iniciado"] and pausar() or iniciar()
                st.rerun()
        with c2:
            if st.button("🔁 Zerar", key="btn_reset", use_container_width=True):
                zerar()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            f"""
            <div class="team-box" style="align-items:end;">
              <div class="team-name" style="background:{corB};">{nomeB}</div>
              <div id="penB" class="mini-pen">-</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Script dos 2' (com # + MM:SS)
    components.html(
        f"""
      <script>
        (function(){{
          if (window.__penA) {{ clearInterval(window.__penA); window.__penA=null; }}
          if (window.__penB) {{ clearInterval(window.__penB); window.__penB=null; }}
          const a = parent.document.querySelector('#penA');
          const b = parent.document.querySelector('#penB');
          const beep = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

          let numA = {json.dumps(nA) if nA is not None else "null"};
          let restA = {int(rA)};
          let numB = {json.dumps(nB) if nB is not None else "null"};
          let restB = {int(rB)};

          function show(el, secs, num){{
            if (!el) return;
            if (!secs || secs<=0 || num===null) {{ el.textContent='-'; return; }}
            const m = String(Math.floor(secs/60)).padStart(2,'0');
            const s = String(secs%60).padStart(2,'0');
            el.textContent = '#' + String(num) + ' ' + m + ':' + s;
          }}
          function tickA(){{
            if (restA<=0) return;
            restA = Math.max(0, restA-1); show(a, restA, numA);
            if (restA===0) {{ try{{beep.play();}}catch(e){{}} clearInterval(window.__penA); }}
          }}
          function tickB(){{
            if (restB<=0) return;
            restB = Math.max(0, restB-1); show(b, restB, numB);
            if (restB===0) {{ try{{beep.play();}}catch(e){{}} clearInterval(window.__penB); }}
          }}
          show(a, restA, numA); show(b, restB, numB);
          if (restA>0) window.__penA = setInterval(tickA, 1000);
          if (restB>0) window.__penB = setInterval(tickB, 1000);
        }})();
      </script>
        """,
        height=0,
    )


# =====================================================
# 🧭 ABAS
# =====================================================
def aba_configuracao():
    st.subheader("Configuração da Equipe")
    colA, colB = st.columns(2)

    def bloco(eq: str, col):
        with col:
            st.markdown(f"### {get_team_name(eq)}")

            # Nome (seguro para inicialização)
            nome_atual = st.session_state.get(f"nome_{eq}", f"Equipe {eq}")
            novo_nome = st.text_input(f"Nome da equipe {eq}", value=nome_atual, key=f"nome_input_{eq}")
            st.session_state[f"nome_{eq}"] = novo_nome

            # Tamanho do elenco
            qtd = st.number_input(f"Quantidade de jogadores ({eq})", 1, 20, value=len(_lista(eq)), step=1, key=f"qtd_{eq}")
            elenco = _lista(eq)
            if len(elenco) != qtd:
                # recria preservando o que for possível
                base = [{"numero": i + 1, "estado": "banco", "elegivel": True, "exclusoes": 0} for i in range(qtd)]
                for i, it in enumerate(base):
                    if i < len(elenco):
                        it.update({k: elenco[i][k] for k in ("estado", "elegivel", "exclusoes")})
                st.session_state["equipes"][eq] = base

            st.markdown("**Números das camisetas:**")
            cols = st.columns(5)
            for i, j in enumerate(_lista(eq)):
                with cols[i % 5]:
                    val = st.number_input(f"Jogador {i+1}", 0, 999, value=int(j["numero"]), step=1, key=f"num_{eq}_{i}")
                    j["numero"] = int(val)

            st.markdown("**Cor da equipe:**")
            st.session_state["cores"][eq] = st.color_picker(
                f"Cor da equipe {eq}", value=st.session_state["cores"][eq], key=f"cor_{eq}"
            )

    bloco("A", colA)
    bloco("B", colB)


def aba_titulares():
    st.subheader("Definir Titulares")
    colA, colB = st.columns(2)

    def bloco(eq: str, col):
        with col:
            st.markdown(f"### {get_team_name(eq)}")
            todos = sorted(j["numero"] for j in _lista(eq))
            esc = st.multiselect("Titulares", todos, default=[n for n in todos[:7]], key=f"tit_{eq}")
            if st.button("Registrar/Atualizar titulares", key=f"reg_{eq}"):
                jogando = set(map(int, esc))
                for j in _lista(eq):
                    j["estado"] = "jogando" if (int(j["numero"]) in jogando and j["elegivel"]) else "banco"
                st.success("Titulares definidos/atualizados.")

    bloco("A", colA)
    bloco("B", colB)


def aba_controle():
    st.subheader("Controle do Jogo")

    inv = st.toggle("Inverter lados (A ⇄ B)", value=False, key="inv_lados")
    lados = ("B", "A") if inv else ("A", "B")

    colA, colB = st.columns(2)

    def painel(eq: str, col):
        with col:
            st.markdown(f"### {get_team_name(eq)}")
            jogs = jogadores(eq, "jogando")
            bnk = jogadores(eq, "banco")
            if not jogs:
                st.info("Nenhum jogador em quadra.")
            st.markdown("**Substituição**")
            c1, c2, c3 = st.columns([1, 1, 0.6])
            with c1:
                sai = st.selectbox("Sai", options=jogs or [None], key=f"sai_{eq}")
            with c2:
                entra = st.selectbox("Entra", options=bnk or [None], key=f"entra_{eq}")
            with c3:
                if st.button("Confirmar", key=f"sub_{eq}", use_container_width=True, disabled=(not jogs or not bnk)):
                    ok, msg = aplicar_substituicao(eq, int(sai), int(entra))
                    st.success(msg) if ok else st.error(msg)

            st.divider()
            st.markdown("**2 minutos**")
            jall = sorted(j["numero"] for j in _lista(eq))
            sel2 = st.selectbox("Jogador", jall, key=f"dois_{eq}")
            if st.button("Aplicar 2'", key=f"ap2_{eq}"):
                ok, msg = aplicar_dois_minutos(eq, int(sel2))
                st.success(msg) if ok else st.error(msg)

            st.divider()
            st.markdown("**Completou**")
            selc = st.selectbox("Jogador que entra", jall, key=f"comp_{eq}")
            if st.button("Confirmar retorno", key=f"ret_{eq}"):
                ok, msg = aplicar_completou(eq, int(selc))
                st.success(msg) if ok else st.error(msg)

    painel(lados[0], colA)
    painel(lados[1], colB)


def aba_dados():
    st.subheader("Visualização de Dados")
    import pandas as pd
    rows = []
    now = tempo_logico_atual()
    for eq in ("A", "B"):
        for j in _lista(eq):
            ativo2 = any((now < p["end"]) and not p["consumido"] and p["numero"] == j["numero"]
                         for p in st.session_state["penalties"][eq])
            rows.append({
                "Equipe": get_team_name(eq),
                "Número": j["numero"],
                "Estado": j["estado"],
                "Exclusões": j["exclusoes"],
                "2' ativo?": ativo2,
                "Elegível": j["elegivel"],
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# =====================================================
# 🚀 APP
# =====================================================
_init_state()
render_top_scoreboard()

tabs = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

with tabs[0]:
    aba_configuracao()

with tabs[1]:
    aba_titulares()

with tabs[2]:
    aba_controle()

with tabs[3]:
    aba_dados()
