import time

POSICOES_VALIDAS = ["Goleiro", "Pivô", "Ponta Esquerda", "Armação Esquerda",
                    "Armação Central", "Armação Direita", "Ponta Direita"]

def inicializar_equipes_se_nao_existirem(state):
    for eq in ["A", "B"]:
        if not state["equipes"][eq]:
            # inicializa com 7 jogadores default (1..7)
            state["equipes"][eq] = [{
                "numero": i+1,
                "estado": "banco",
                "tempo_jogado": 0,
                "tempo_banco": 0,
                "tempo_penalidade": 0,
                "exclusoes": 0,
                "elegivel": True,
                "expulso": False
            } for i in range(7)]

def formato_mmss(segundos):
    m = segundos // 60
    s = segundos % 60
    return f"{m:02d}:{s:02d}"

def atualizar_tempos(state):
    for eq in ["A", "B"]:
        for j in state["equipes"][eq]:
            if j["estado"] == "jogando":
                j["tempo_jogado"] += 1
            elif j["estado"] == "banco":
                j["tempo_banco"] += 1
            elif j["estado"] == "penalidade":
                j["tempo_penalidade"] += 1

def atualizar_penalidades(state):
    """Retorna True se alguma penalidade terminou (para tocar alarme)."""
    terminou = False
    for p in state["penalidades"]:
        if p["restante"] > 0:
            p["restante"] -= 1
            if p["restante"] == 0:
                terminou = True
    # Remove as que acabaram (mas manter slot aberto para 'completou')
    state["penalidades"] = [p for p in state["penalidades"] if p["restante"] > 0]
    return terminou

# ---------- Titulares ----------
def definir_titulares(state, equipe, numeros_titulares):
    # Zera estados e marca titulares como "jogando"
    for j in state["equipes"][equipe]:
        j["estado"] = "jogando" if j["numero"] in numeros_titulares else "banco"
    state["titulares_definidos"][equipe] = True

def corrigir_titulares(state, equipe):
    state["titulares_definidos"][equipe] = False

def set_posicao_titular(state, equipe, numero, posicao):
    if posicao is not None and posicao not in POSICOES_VALIDAS:
        return
    state["funcoes"][equipe][numero] = posicao

# ---------- Regras rápidas ----------
def get_jogador(state, equipe, numero):
    for j in state["equipes"][equipe]:
        if j["numero"] == numero:
            return j
    return None

def pode_substituir(state, equipe, selecao):
    if len(selecao) != 2:
        return False
    j1 = get_jogador(state, equipe, selecao[0])
    j2 = get_jogador(state, equipe, selecao[1])
    if not j1 or not j2: return False
    # não pode se houver penalidade/expulsão/inelegível
    bloqueios = {"penalidade", "expulso", "inelegivel"}
    if j1["estado"] in bloqueios or j2["estado"] in bloqueios:
        return False
    # precisa um jogando e outro banco (entrada/saída)
    estados = {j1["estado"], j2["estado"]}
    return ("jogando" in estados) and ("banco" in estados)

def pode_penalizar(state, equipe, numero):
    j = get_jogador(state, equipe, numero)
    if not j: return False
    if not j["elegivel"] or j["expulso"]:
        return False
    # só faz sentido penalizar quem está jogando
    return j["estado"] == "jogando"

def efetuar_substituicao(state, equipe, selecao):
    if not pode_substituir(state, equipe, selecao):
        return False, "Selecione exatamente 2 (um jogando e um no banco), sem penalidades/expulsões."
    n1, n2 = selecao
    j1 = get_jogador(state, equipe, n1)
    j2 = get_jogador(state, equipe, n2)
    # troca estados
    if j1["estado"] == "jogando":
        j1["estado"], j2["estado"] = "banco", "jogando"
        msg = f"Substituição: {equipe} #{n1} ⇄ #{n2}"
    else:
        j1["estado"], j2["estado"] = "jogando", "banco"
        msg = f"Substituição: {equipe} #{n2} ⇄ #{n1}"
    return True, msg

def aplicar_exclusao_2min(state, equipe, numero):
    """Retorna (ok, msg, virou_inelegivel). 2 min sempre abre 1 slot para 'completou'."""
    j = get_jogador(state, equipe, numero)
    if not pode_penalizar(state, equipe, numero):
        return False, "Jogador não pode receber 2 minutos (verifique estado).", False

    # Sair da quadra: para de contar jogado, vai para 'penalidade'
    j["estado"] = "penalidade"
    j["exclusoes"] += 1

    # Registra penalidade com 120s
    state["penalidades"].append({
        "equipe": equipe,
        "jogador": numero,
        "tipo": "2min",
        "inicio": time.strftime("%H:%M:%S"),
        "restante": 120
    })
    # Abre slot para COMPLETOU
    state["slots_abertos"][equipe] += 1

    inelegivel = False
    if j["exclusoes"] >= 3:
        j["elegivel"] = False
        j["estado"] = "inelegivel"
        inelegivel = True

    return True, f"{equipe} #{numero} recebeu 2 minutos.", inelegivel

def aplicar_expulsao(state, equipe, numero):
    """Expulsão também abre 1 slot para COMPLETOU e coloca 2 min no painel (como você solicitou)."""
    j = get_jogador(state, equipe, numero)
    if not pode_penalizar(state, equipe, numero):
        return False, "Jogador não pode ser expulso (verifique estado)."

    j["expulso"] = True
    j["elegivel"] = False
    j["estado"] = "expulso"

    state["penalidades"].append({
        "equipe": equipe,
        "jogador": numero,
        "tipo": "expulsao",
        "inicio": time.strftime("%H:%M:%S"),
        "restante": 120
    })
    state["slots_abertos"][equipe] += 1
    return True, f"{equipe} #{numero} expulso (2 min exibidos; jogador inelegível)."

def pode_completar(state, equipe, numero_entrante):
    if state["slots_abertos"][equipe] <= 0:
        return False
    j = get_jogador(state, equipe, numero_entrante)
    if not j: return False
    # precisa estar no banco e ser elegível
    return (j["estado"] == "banco") and j["elegivel"] and not j["expulso"]

def completar_substituicao(state, equipe, numero_entrante):
    if not pode_completar(state, equipe, numero_entrante):
        return False, "Sem slot aberto ou jogador não elegível para entrar."
    j = get_jogador(state, equipe, numero_entrante)
    j["estado"] = "jogando"
    state["slots_abertos"][equipe] -= 1
    return True, f"{equipe} #{numero_entrante} entrou em quadra (completou)."
