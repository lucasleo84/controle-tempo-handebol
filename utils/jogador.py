import time

def formato_mmss(segundos):
    segundos = int(segundos)
    m, s = divmod(segundos, 60)
    return f"{m:02d}:{s:02d}"

def inicializar_equipes_se_nao_existirem(state):
    if "equipes" not in state:
        state["equipes"] = {"A": [], "B": []}
    if "penalidades" not in state:
        state["penalidades"] = []
    if "titulares_definidos" not in state:
        state["titulares_definidos"] = {"A": False, "B": False}
    if "funcoes" not in state:
        state["funcoes"] = {"A": {}, "B": {}}
    if "slots_abertos" not in state:
        state["slots_abertos"] = {"A": 0, "B": 0}

# =============== TITULARES ===============
def definir_titulares(state, equipe, numeros_titulares):
    for j in state["equipes"][equipe]:
        j["estado"] = "banco"
        j["elegivel"] = True
        j["expulso"] = False
        j["exclusoes"] = j.get("exclusoes", 0)
    for j in state["equipes"][equipe]:
        if j["numero"] in numeros_titulares:
            j["estado"] = "jogando"
    state["titulares_definidos"][equipe] = True
    return True

def corrigir_titulares(state, equipe):
    state["titulares_definidos"][equipe] = False
    return True

def set_posicao_titular(state, equipe, numero, posicao):
    state["funcoes"][equipe][numero] = posicao

# =============== SUBSTITUIÇÃO ===============
def efetuar_substituicao(state, equipe, selecionados):
    if len(selecionados) != 2:
        return False, "Selecione quem sai e quem entra."
    sai, entra = str(selecionados[0]), str(selecionados[1])
    jog_sai = _get_jogador(state, equipe, sai)
    jog_entra = _get_jogador(state, equipe, entra)
    if not jog_sai or not jog_entra:
        return False, "Jogador inválido."
    if jog_sai["estado"] != "jogando":
        return False, "Jogador selecionado para sair não está jogando."
    if jog_entra["estado"] != "banco":
        return False, "Jogador selecionado para entrar não está no banco."
    jog_sai["estado"] = "banco"
    jog_entra["estado"] = "jogando"
    return True, f"Substituição feita: sai #{sai}, entra #{entra}"

# =============== 2 MINUTOS ===============
def aplicar_exclusao_2min(state, equipe, numero):
    j = _get_jogador(state, equipe, numero)
    if not j:
        return False, "Jogador inválido.", False
    if j["estado"] != "jogando" or not j.get("elegivel", True):
        return False, "Jogador não pode receber 2 minutos (verifique estado).", False
    j["estado"] = "penalizado"
    j["exclusoes"] = j.get("exclusoes", 0) + 1
    state["penalidades"].append({
        "tipo": "2min",
        "equipe": equipe,
        "jogador": str(numero),
        "restante": 120,
        "ultimo_tick": time.time(),
        "ativo": True
    })
    state["slots_abertos"][equipe] += 1
    terminou3 = False
    if j["exclusoes"] >= 3:
        j["elegivel"] = False
        j["estado"] = "expulso"
        terminou3 = True
    return True, f"Exclusão de 2 minutos aplicada ao jogador #{numero}.", terminou3

# =============== EXPULSÃO ===============
def aplicar_expulsao(state, equipe, numero):
    j = _get_jogador(state, equipe, numero)
    if not j:
        return False, "Jogador inválido."
    if j["estado"] != "jogando":
        return False, "Jogador não pode ser expulso (verifique estado)."
    j["estado"] = "expulso"
    j["elegivel"] = False
    state["penalidades"].append({
        "tipo": "2min",
        "equipe": equipe,
        "jogador": str(numero),
        "restante": 120,
        "ultimo_tick": time.time(),
        "ativo": True
    })
    state["slots_abertos"][equipe] += 1
    return True, f"Jogador #{numero} expulso. Equipe cumpre 2 minutos."

# =============== COMPLETOU ===============
def completar_substituicao(state, equipe, numero_entrante):
    if state["slots_abertos"][equipe] <= 0:
        return False, "Sem slot aberto ou jogador não elegível para entrar."
    j = _get_jogador(state, equipe, numero_entrante)
    if not j:
        return False, "Jogador inválido."
    if j["estado"] != "banco" or not j.get("elegivel", True):
        return False, "Jogador precisa estar no banco e elegível."
    j["estado"] = "jogando"
    state["slots_abertos"][equipe] -= 1
    return True, f"Jogador #{numero_entrante} entrou. Slot fechado."

# =============== AUXILIAR ===============
def _get_jogador(state, equipe, numero):
    numero = int(numero)
    for j in state["equipes"][equipe]:
        if int(j["numero"]) == numero:
            j.setdefault("estado", "banco")
            j.setdefault("elegivel", True)
            j.setdefault("expulso", False)
            j.setdefault("exclusoes", 0)
            return j
    return None
