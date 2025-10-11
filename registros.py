import pandas as pd
import os

def salvar_csv(state):
    registros = []
    for equipe in ["A", "B"]:
        for jogador in state["equipes"][equipe]:
            registros.append({
                "Equipe": equipe,
                "Jogador": jogador["numero"],
                "Tempo jogado (min)": round(jogador["tempo_jogado"] / 60, 2),
                "Tempo no banco (min)": round(jogador["tempo_banco"] / 60, 2),
                "Tempo 2min (min)": round(jogador["tempo_penalidade"] / 60, 2)
            })
    df = pd.DataFrame(registros)
    os.makedirs("dados", exist_ok=True)
    df.to_csv("dados/saida_jogo.csv", index=False, encoding="utf-8")
