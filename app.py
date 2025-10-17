# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime
from typing import Dict, List

import streamlit as st
import streamlit.components.v1 as components

# =====================================================
# 🔧 ESTADO GLOBAL / HELPERS BÁSICOS
# =====================================================
def _init_state():
    if "equipas_inicializado" in st.session_state:
        return

    st.session_state.equipas_inicializado = True

    # relógio principal
    st.session_state.iniciado = False
    st.session_state.cronometro = 0.0       # elapsed base em segundos
    st.session_state.ultimo_tick = None     # epoch quando iniciou

    # nomes das equipes e cores
    st.session_state["nome_A"] = "Equipe A"
    st.session_state["nome_B"] = "Equipe B"
    st.session_state["cores"] = {"A": "#16c1f3", "B": "#11e5cf"}

    # elenco (lista de dicts por equipe)
    st.session_state["equipes"] = {
        "A": [{"numero": i + 1, "estado": "banco", "elegivel": True, "exclusoes": 0} for i in range(7)],
        "B": [{"numero": i + 1, "estado": "banco", "elegivel": True, "exclusoes": 0} for i in range(7)],
    }

    # penalidades ativas [{numero,start,end,consumido}], por equipe
    st.session_state["penalties"] = {"A": [], "B": []}

    # flags auxiliares de UI
    for eq in ("A", "B"):
        st.session_state[f"titulares_definidos_{eq}"] = False

def get_team_name(eq: str) -> str:
    return st.session_state.get(f"nome_{eq}") or f"Equipe {eq}"

def tempo_logico_atual() -> float:
    """Segundos 'lógicos' do jogo em relação ao relógio principal."""
    base = float(st.session_state["cronometro"])
    if st.session_state["iniciado"] and st.session_state["ultimo_tick"]:
        base += time.time() - float(st.session_state["ultimo_tick"])
    return base

# =====================================================
# ⏱️ CONTROLES DO CRONÔMETRO
# =====================================================
def iniciar():
    if not st.session_state["iniciado"]:
        st.session_state["iniciado"] = True
        st.session_state["ultimo_tick"] = time.time()

def pausar():
    if st.session_state["iniciado"]:
        now = time.time()
        st.session_state["cronometro"] += now - float(st.session_state["ultimo_tick"])
        st.session_state["ultimo_tick"] = None
        st.session_state["iniciado"] = False

def zerar():
    st.session_state["iniciado"] = False
    st.session_state["cronometro"] = 0.0
    st.session_state["ultimo_tick"] = None

# =====================================================
# 👥 JOGADORES / ESTADOS
# =====================================================
def _lista(eq: str) -> List[Dict]:
    return st.session_state["equipes"][eq]

def jogadores(eq: str, estado: str = None, elegiveis=True) -> List[int]:
    lst = []
    for j in _lista(eq):
        if (estado is None or j["estado"] == estado) and (not elegiveis or j["elegivel"]):
            lst.append(j["numero"])
    return sorted(lst)

def _find(eq: str, numero: int) -> Dict:
    for j in _lista(eq):
        if j["numero"] == numero:
            return j
    raise KeyError("Jogador não encontrado")

def atualizar_estado(eq: str, numero: int, novo: str):
    j = _find(eq, numero)
    j["estado"] = novo

def aplicar_substituicao(eq: str, sai: int, entra: int) -> (bool, str):
    if sai == entra:
        return False, "Jogadores iguais."
    j_sai = _find(eq, sai)
    j_en  = _find(eq, entra)
    if j_sai["estado"] != "jogando":
        return False, f"#{sai} não está jogando."
    if j_en["estado"] != "banco":
        return False, f"#{entra} não está no banco."
    if not j_en["elegivel"]:
        return False, f"#{entra} está inelegível."
    j_sai["estado"] = "banco"
    j_en["estado"]  = "jogando"
    return True, f"Substituição: Sai #{sai} / Entra #{entra}"

def aplicar_dois_minutos(eq: str, numero: int) -> (bool, str):
    j = _find(eq, numero)
    if not j["elegivel"]:
        return False, f"#{numero} já está inelegível."
    # registra 2'
    now = tempo_logico_atual()
    st.session_state["penalties"][eq].append({
        "numero": int(numero),
        "start":  now,
        "end":    now + 120.0,
        "consumido": False
    })
    # sai da quadra (se estiver jogando)
    if j["estado"] == "jogando":
        j["estado"] = "banco"
    j["exclusoes"] += 1
    if j["exclusoes"] >= 3:
        j["elegivel"] = False
        return True, f"#{numero} recebeu a 3ª exclusão e está inelegível."
    return True, f"#{numero} excluído por 2 minutos (placar mostra # e contagem)."

def aplicar_completou(eq: str, numero: int) -> (bool, str):
    """Jogador volta a ser marcado como 'jogando' (após 2')."""
    j = _find(eq, numero)
    if not j["elegivel"]:
        return False, "Jogador inelegível."
    j["estado"] = "jogando"
    return True, f"#{numero} voltou (completou)."

# =====================================================
# 🧷 PLACAR FIXO: relógio + 2 minutos
# =====================================================
def render_top_scoreboard():
    """Placar esportivo fixo no topo; abas fixas logo abaixo; só o conteúdo rola."""
    iniciado     = bool(st.session_state["iniciado"])
    base_elapsed = float(st.session_state["cronometro"])
    start_epoch  = float(st.session_state["ultimo_tick"]) if iniciado else None

    def _pen_top(eq: str):
        now  = tempo_logico_atual()
        ats  = [p for p in st.session_state["penalties"].get(eq, []) if (now < p["end"]) and not p["consumido"]]
        if not ats:
            return (None, 0)
        p = min(ats, key=lambda x: x["end"])
        return (int(p["numero"]), max(0, int(round(p["end"] - now))))

    numA, restA = _pen_top("A")
    numB, restB = _pen_top("B")

    corA, corB = st.session_state["cores"]["A"], st.session_state["cores"]["B"]
    nomeA, nomeB = get_team_name("A"), get_team_name("B")

    SCORE_H = 120
    TABS_H  = 46

    st.markdown(f"""
    <style>
      :root {{
        --scoreH:{SCORE_H}px;
        --tabsH:{TABS_H}px;
      }}
      .block-container {{
        padding-top: calc(var(--scoreH) + var(--tabsH) + 12px) !important;
      }}
      .score-fixed {{
        position: fixed; left: 0; right: 0; top: 0;
        z-index: 1100;
        background: radial-gradient( circle at 50% 20%, #101010 0%, #090909 60%, #050505 100% );
        border-bottom: 1px solid #1f1f1f;
        box-shadow: 0 8px 24px rgba(0,0,0,.35);
      }}
      .score-wrap {{
        max-width: 1200px; margin: 0 auto; height: var(--scoreH);
        display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 20px;
        padding: 10px 16px;
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
        padding:12px 28px; border-radius:14px; min-width: 340px; text-align:center;
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
        z-index: 1000; background: rgba(20,20,20,.66); backdrop-filter: blur(6px);
        box-shadow: 0 6px 14px rgba(0,0,0,.18);
      }}
      div[data-baseweb="tab-list"] > div {{ max-width: 1200px; margin: 0 auto; }}
    </style>
    """, unsafe_allow_html=True)

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
            unsafe_allow_html=True
        )

    with center:
        st.markdown('<div class="clock-box">', unsafe_allow_html=True)
        components.html(f"""
          <div id="clock" class="clock">00:00</div>
          <script>
            (function(){{
              const el = document.currentScript.previousElementSibling;
              const iniciado   = {str(iniciado).lower()};
              const baseElapsed= {base_elapsed};
              const startEpoch = {json.dumps(start_epoch) if start_epoch is not None else 'null'};
              function fmt(sec){{
                sec = Math.max(0, Math.floor(sec));
                const m = Math.floor(sec/60), s = sec%60;
                return (m<10?'0':'')+m+':' + (s<10?'0':'')+s;
              }}
              function draw(){{
                let e = baseElapsed;
                if (iniciado && startEpoch){{
                  const now = Date.now()/1000;
                  e = baseElapsed + (now - startEpoch);
                }}
                el.textContent = fmt(e);
                window.__raf_clock && cancelAnimationFrame(window.__raf_clock);
                window.__raf_clock = requestAnimationFrame(draw);
              }}
              draw();
            }})();
          </script>
        """, height=96)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⏯ Iniciar / Pausar", key="sc_toggle", use_container_width=True):
                st.session_state["iniciado"] and pausar() or iniciar()
                st.rerun()
        with c2:
            if st.button("🔁 Zerar", key="sc_reset", use_container_width=True):
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
            unsafe_allow_html=True
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # 2 minutos (# + contagem)
    numA_js = json.dumps(numA) if numA is not None else "null"
    numB_js = json.dumps(numB) if numB is not None else "null"
    components.html(f"""
      <script>
        (function(){{
          if (window.__penIntA) {{ clearInterval(window.__penIntA); window.__penIntA = null; }}
          if (window.__penIntB) {{ clearInterval(window.__penIntB); window.__penIntB = null; }}
          const boxA = parent.document.querySelector('#penA');
          const boxB = parent.document.querySelector('#penB');
          if (boxA) boxA.textContent = '-';
          if (boxB) boxB.textContent = '-';

          let nA = {numA_js}, rA = {int(restA)};
          let nB = {numB_js}, rB = {int(restB)};
          const beep = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

          function upd(el, secs, num){{
            if(!el) return;
            if(num===null || !secs || secs<=0) {{ el.textContent='-'; return; }}
            const m = String(Math.floor(secs/60)).padStart(2,'0');
            const s = String(secs%60).padStart(2,'0');
            el.textContent = '#' + String(num) + ' ' + m + ':' + s;
          }}
          upd(boxA, rA, nA); upd(boxB, rB, nB);

          function tickA(){{
            if(rA<=0) return;
            rA = Math.max(0, rA-1);
            upd(boxA, rA, nA);
            if(rA===0) {{ try{{beep.play();}}catch(e){{}} clearInterval(window.__penIntA); }}
          }}
          function tickB(){{
            if(rB<=0) return;
            rB = Math.max(0, rB-1);
            upd(boxB, rB, nB);
            if(rB===0) {{ try{{beep.play();}}catch(e){{}} clearInterval(window.__penIntB); }}
          }}
          if (rA>0) window.__penIntA = setInterval(tickA, 1000);
          if (rB>0) window.__penIntB = setInterval(tickB, 1000);
        }})();
      </script>
    """, height=0)

# =====================================================
# 🧭 ABAS
# =====================================================
def aba_configuracao():
    st.subheader("Configuração da Equipe")
    colA, colB = st.columns(2)

    def bloco(eq: str, col):
        with col:
            st.markdown(f"### {get_team_name(eq)}")
            st.session_state[f"nome_{eq}"] = st.text_input(f"Nome da equipe {eq}", value=st.session_state[f"nome_{eq}"])
            qtd = st.number_input(f"Quantidade de jogadores ({eq})", 1, 20, value=len(_lista(eq)), step=1, key=f"qtd_{eq}")
            # ajustar tamanho do elenco
            atual = _lista(eq)
            if len(atual) != qtd:
                base = [{"numero": i + 1, "estado": "banco", "elegivel": True, "exclusoes": 0} for i in range(qtd)]
                # tenta preservar o que existir
                for i, it in enumerate(base):
                    if i < len(atual):
                        it.update({k: atual[i][k] for k in ("estado", "elegivel", "exclusoes")})
                st.session_state["equipes"][eq] = base

            st.markdown("**Números das camisetas:**")
            cols = st.columns(5)
            data = _lista(eq)
            for i, j in enumerate(data):
                c = cols[i % 5]
                with c:
                    novo = st.number_input(f"Jogador {i+1}", min_value=0, max_value=999, value=int(j["numero"]), step=1, key=f"num_{eq}_{i}")
                    j["numero"] = int(novo)

            st.markdown("**Cor da equipe:**")
            st.session_state["cores"][eq] = st.color_picker(f"Cor da equipe {eq}", value=st.session_state["cores"][eq], key=f"cor_{eq}")

            if st.button(f"Salvar equipe {eq}"):
                st.success(f"Equipe {eq} salva.")
                # não travamos titulares; pode definir depois

    bloco("A", colA)
    bloco("B", colB)

def aba_titulares():
    st.subheader("Definir Titulares")
    colA, colB = st.columns(2)

    def bloco(eq: str, col):
        with col:
            st.markdown(f"### {get_team_name(eq)}")
            # escolhe titulares a partir de todos
            todos = sorted(j["numero"] for j in _lista(eq))
            escolha = st.multiselect("Titulares", todos, default=[n for n in todos[:7]], key=f"tit_{eq}")
            if st.button("Registrar/Atualizar titulares", key=f"reg_tit_{eq}"):
                # quem está na lista vira 'jogando', os demais 'banco'
                jogando = set(escolha)
                for j in _lista(eq):
                    j["estado"] = "jogando" if j["numero"] in jogando and j["elegivel"] else "banco"
                st.session_state[f"titulares_definidos_{eq}"] = True
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
            bnk  = jogadores(eq, "banco")
            if not jogs:
                st.info("Nenhum jogador em quadra.")
            st.markdown("**Substituição**")
            c1, c2, c3 = st.columns([1, 1, 0.6])
            with c1:
                sai = st.selectbox("Sai", options=jogs, key=f"sai_{eq}")
            with c2:
                entra = st.selectbox("Entra", options=bnk if bnk else [None], key=f"entra_{eq}")
            with c3:
                if st.button("Confirmar", key=f"sub_{eq}", use_container_width=True):
                    ok, msg = aplicar_substituicao(eq, int(sai), int(entra))
                    ok and st.success(msg) or st.error(msg)

            st.divider()
            st.markdown("**2 minutos**")
            jall = sorted(j["numero"] for j in _lista(eq))
            sel2 = st.selectbox("Jogador", jall, key=f"dois_{eq}")
            if st.button("Aplicar 2'", key=f"ap2_{eq}"):
                ok, msg = aplicar_dois_minutos(eq, int(sel2))
                ok and st.success(msg) or st.error(msg)

            st.divider()
            st.markdown("**Completou**")
            selc = st.selectbox("Jogador que entra", jall, key=f"comp_{eq}")
            if st.button("Confirmar retorno", key=f"ret_{eq}"):
                ok, msg = aplicar_completou(eq, int(selc))
                ok and st.success(msg) or st.error(msg)

    painel(lados[0], colA)
    painel(lados[1], colB)

def aba_dados():
    st.subheader("Visualização de Dados")
    rows = []
    for eq in ("A", "B"):
        for j in _lista(eq):
            rows.append({
                "Equipe": get_team_name(eq),
                "Número": j["numero"],
                "Estado": j["estado"],
                "Exclusões": j["exclusoes"],
                "2 min (ativo?)": any(tempo_logico_atual() < p["end"] and not p["consumido"] and p["numero"] == j["numero"]
                                      for p in st.session_state["penalties"][eq]),
                "Elegível": j["elegivel"],
            })
    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# =====================================================
# 🚀 APP
# =====================================================
_init_state()
render_top_scoreboard()

abas = st.tabs(["Configuração da Equipe", "Definir Titulares", "Controle do Jogo", "Visualização de Dados"])

with abas[0]:
    aba_configuracao()

with abas[1]:
    aba_titulares()

with abas[2]:
    aba_controle()

with abas[3]:
    aba_dados()
