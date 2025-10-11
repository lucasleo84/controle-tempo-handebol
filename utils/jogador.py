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
