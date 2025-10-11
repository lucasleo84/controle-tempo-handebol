# utils/jogador.py
import time

# -------------------------------
# Formatação de tempo
# -------------------------------
def formato_mmss(segundos):
    segundos = int(segundos)
    m, s = divmod(segundos, 60)
    return f"{m:02d}:{s:02d}"

# -------------------------------
# Inicialização
# -------------------------------
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

# -------------------------------
# Definir e corrigir titulares
# -------------------------------
def definir_titulares(state, equipe, numeros_titulares):
    """
    Marca como 'jogando' os jogadores cujos números foram selecionados,
    e 'banco' para os demais.
    Garante atualização do state para refletir imediatamente na UI.
    """
    nova_lista = []
    for j in state["equipes"][equipe]:
        numero = int(j["numero"])
        novo = j.copy()
        novo["elegivel"] = True
        novo["expulso"] = False
        novo["exclusoes"] = int(j.get("exclusoes", 0))
        novo["estado"] = "jogando" if numero in numeros_titulares else "banco"
        nova_lista.append(novo)

    # Substitui a lista inteira, forçando refresh correto
    state["equipes"][equipe] = nova_lista
    state["titulares_definidos"][equipe] = True
    return True

# -------------------------------
# Atualização de tempos (opcional)
# -------------------------------
def atualizar_tempos(state):
    """
    Mantida por compatibilidade — no modelo atual (v9+),
    o cronômetro lógico é calculado no app no momento do uso.
    Se quiser acumular por estado, você pode estender aqui.
    """
    pass

# -------------------------------
# Substituição
# -------------------------------
def efetuar_substituicao(state, equipe, selecionados):
    if len(selecionados) != 2 or None in selecionados:
        return False, "Selecione quem sai e quem entra."
    """
    selecionados = [sai, entra] (strings ou ints)
    Regras:
      - 'sai' deve estar jogando e elegível
      - 'entra' deve estar no banco e elegível
      - Troca estados: sai->banco, entra->jogando
    """
    if len(selecionados) != 2:
        return False, "Selecione quem sai e quem entra."

    sai, entra = str(selecionados[0]), str(selecionados[1])

    jog_sai = _get_jogador(state, equipe, sai)
    jog_entra = _get_jogador(state, equipe, entra)

    if not jog_sai or not jog_entra:
        return False, "Jogador inválido."

    if not (jog_sai["estado"] == "jogando" and jog_sai.get("elegivel", True)):
        return False, "Jogador selecionado para sair não está jogando."
    if not (jog_entra["estado"] == "banco" and jog_entra.get("elegivel", True)):
        return False, "Jogador selecionado para entrar não está no banco."

    # Efetiva
    jog_sai["estado"] = "banco"
    jog_entra["estado"] = "jogando"
    return True, "Substituição registrada."

# -------------------------------
# 2 minutos (exclusão)
# -------------------------------
def aplicar_exclusao_2min(state, equipe, numero):
    """
    Regras:
      - só para quem está JOGANDO e elegível
      - vai para 'penalizado'
      - abre um slot para reposição (5x6)
      - cronômetro 120s
      - ao atingir 3 exclusões => expulso (inelegível)
    """
    j = _get_jogador(state, equipe, numero)
    if not j:
        return False, "Jogador inválido.", False

    if not (j["estado"] == "jogando" and j.get("elegivel", True)):
        return False, "Jogador não pode receber 2 minutos (verifique estado).", False

    # Aplica penalidade
    j["estado"] = "penalizado"
    j["exclusoes"] = int(j.get("exclusoes", 0)) + 1

    state["penalidades"].append({
        "tipo": "2min",
        "equipe": equipe,
        "jogador": str(numero),
        "restante": 120,
        "ultimo_tick": time.time(),
        "ativo": True
    })

    # Abre um slot
    state["slots_abertos"][equipe] = int(state["slots_abertos"].get(equipe, 0)) + 1

    terminou3 = False
    if j["exclusoes"] >= 3:
        # Inelegível para o restante do jogo
        j["elegivel"] = False
        j["expulso"] = True
        j["estado"] = "expulso"
        terminou3 = True

    return True, f"Exclusão de 2 minutos aplicada ao #{numero}.", terminou3

# -------------------------------
# Expulsão
# -------------------------------
def aplicar_expulsao(state, equipe, numero):
    """
    Regras:
      - só faz sentido para quem está JOGANDO
      - vira 'expulso' (inelegível)
      - abre um slot
      - adiciona um '2min' de equipe (após 120s alguém pode entrar)
    """
    j = _get_jogador(state, equipe, numero)
    if not j:
        return False, "Jogador inválido."

    if not (j["estado"] == "jogando" and j.get("elegivel", True)):
        return False, "Jogador não pode ser expulso (verifique estado)."

    j["estado"] = "expulso"
    j["elegivel"] = False
    j["expulso"] = True

    state["penalidades"].append({
        "tipo": "2min",             # 2' da equipe antes de repor
        "equipe": equipe,
        "jogador": str(numero),
        "restante": 120,
        "ultimo_tick": time.time(),
        "ativo": True
    })
    state["slots_abertos"][equipe] = int(state["slots_abertos"].get(equipe, 0)) + 1

    return True, f"Jogador #{numero} expulso. Equipe cumpre 2 minutos."

# -------------------------------
# Completar (após 2 min / expulsão)
# -------------------------------
def completar_substituicao(state, equipe, numero_entrante):
    """
    Entra um jogador do BANCO quando há slot aberto (após 2')
    Regras:
      - precisa haver state['slots_abertos'][equipe] > 0
      - 'numero_entrante' deve estar no 'banco' e elegível
      - fecha 1 slot
    """
    if int(state["slots_abertos"].get(equipe, 0)) <= 0:
        return False, "Sem slot aberto ou jogador não elegível para entrar."

    j = _get_jogador(state, equipe, numero_entrante)
    if not j:
        return False, "Jogador inválido."

    if not (j["estado"] == "banco" and j.get("elegivel", True)):
        return False, "Jogador precisa estar no banco e elegível."

    j["estado"] = "jogando"
    state["slots_abertos"][equipe] = int(state["slots_abertos"].get(equipe, 0)) - 1
    return True, f"Jogador #{numero_entrante} entrou. Slot fechado."

# -------------------------------
# Helpers
# -------------------------------
def _get_jogador(state, equipe, numero):
    numero = int(numero)
    for j in state["equipes"][equipe]:
        if int(j["numero"]) == numero:
            # garante chaves básicas
            j.setdefault("estado", "banco")
            j.setdefault("elegivel", True)
            j.setdefault("expulso", False)
            j.setdefault("exclusoes", 0)
            return j
    return None

