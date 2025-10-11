import time

def inicializar_equipes(nome, qtd):
    return [{
        "numero": i + 1,
        "estado": "banco",
        "tempo_jogado": 0,
        "tempo_banco": 0,
        "tempo_penalidade": 0
    } for i in range(qtd)]

def atualizar_tempos(state):
    for equipe in ["A", "B"]:
        for jogador in state["equipes"][equipe]:
            if jogador["estado"] == "jogando":
                jogador["tempo_jogado"] += 1
            elif jogador["estado"] == "banco":
                jogador["tempo_banco"] += 1
            elif jogador["estado"] == "penalidade":
                jogador["tempo_penalidade"] += 1

def aplicar_penalidade(state, equipe, numero, tipo):
    for jogador in state["equipes"][equipe]:
        if jogador["numero"] == numero:
            jogador["estado"] = "penalidade" if tipo == "2min" else "expulso"
            state["penalidades"].append({
                "equipe": equipe,
                "jogador": numero,
                "tipo": tipo,
                "inicio": time.strftime("%H:%M:%S"),
                "restante": 120
            })
            break

def atualizar_penalidades(state):
    for p in state["penalidades"]:
        if p["restante"] > 0:
            p["restante"] -= 1
        if p["restante"] == 0:
            for j in state["equipes"][p["equipe"]]:
                if j["numero"] == p["jogador"] and j["estado"] == "penalidade":
                    j["estado"] = "banco"
    state["penalidades"] = [p for p in state["penalidades"] if p["restante"] > 0]

def substituir_jogadores(state, equipe, numero):
    for jogador in state["equipes"][equipe]:
        if jogador["numero"] == numero:
            jogador["estado"] = "banco" if jogador["estado"] == "jogando" else "jogando"
