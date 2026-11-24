"""Algoritmo de Programação Dinâmica para a Mochila 0/1.

Seja m[i][c] a maior importância que se obtém usando apenas os i primeiros
arquivos com capacidade c. A recorrência é:

    m[0][c] = 0                                          (sem arquivos)
    m[i][c] = m[i-1][c]                                  se w_i > c
    m[i][c] = max(m[i-1][c], m[i-1][c - w_i] + v_i)      se w_i <= c

O valor ótimo está em m[n][C]. Os arquivos escolhidos são recuperados
percorrendo a tabela de trás para frente: se m[i][c] difere de m[i-1][c],
o arquivo i foi escolhido e passa-se a c - w_i.

Complexidade (n arquivos, capacidade C inteira):
    Tempo:  O(n * C), pois a tabela tem (n + 1) * (C + 1) posições e cada
            uma é calculada em tempo constante. A reconstrução custa O(n).
    Espaço: O(n * C) com a tabela completa, necessária para reconstruir a
            solução. A função `valor_otimo_pd` guarda só um vetor de tamanho
            C + 1 e usa O(C) de espaço, mas devolve apenas o valor.

A complexidade é pseudo-polinomial: depende do valor numérico de C, e não
apenas do tamanho da entrada.
"""

from __future__ import annotations

import time

from src.modelo import Instancia
from src.resultado import Resultado, montar_resultado

NOME = "Programação Dinâmica"


def programacao_dinamica(instancia: Instancia) -> Resultado:
    """Devolve a solução ótima da instância, com os arquivos escolhidos."""
    arquivos = instancia.arquivos
    n = instancia.n
    capacidade = instancia.capacidade

    inicio = time.perf_counter()

    # m[i][c]: melhor importância com os i primeiros arquivos e capacidade c.
    # A linha 0 (nenhum arquivo) e a coluna 0 (capacidade nula) valem 0.
    m = [[0] * (capacidade + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        peso = arquivos[i - 1].tamanho
        valor = arquivos[i - 1].importancia
        anterior = m[i - 1]
        atual = m[i]
        for c in range(capacidade + 1):
            if peso > c:
                # O arquivo i não cabe nesta capacidade: fica de fora.
                atual[c] = anterior[c]
            else:
                # Melhor entre deixar o arquivo de fora ou incluí-lo.
                atual[c] = max(anterior[c], anterior[c - peso] + valor)

    # Reconstrução: do último arquivo para o primeiro. Se o valor mudou ao
    # considerar o arquivo i, ele faz parte da solução.
    escolhidos = []
    c = capacidade
    for i in range(n, 0, -1):
        if m[i][c] != m[i - 1][c]:
            escolhidos.append(arquivos[i - 1])
            c -= arquivos[i - 1].tamanho
    escolhidos.reverse()  # volta à ordem original da instância

    tempo = time.perf_counter() - inicio
    return montar_resultado(NOME, instancia, escolhidos, tempo)


def valor_otimo_pd(instancia: Instancia) -> int:
    """Devolve só o valor ótimo, usando um vetor de tamanho C + 1.

    Mesma recorrência, mas como a linha i só depende da linha i-1, basta um
    vetor. As capacidades são percorridas de C até 0 para que m[c - peso]
    ainda guarde o valor da linha anterior (cada arquivo é usado no máximo
    uma vez). Espaço O(C); não permite reconstruir os arquivos escolhidos.
    """
    capacidade = instancia.capacidade
    m = [0] * (capacidade + 1)

    for arquivo in instancia.arquivos:
        peso = arquivo.tamanho
        valor = arquivo.importancia
        for c in range(capacidade, peso - 1, -1):
            m[c] = max(m[c], m[c - peso] + valor)

    return m[capacidade]