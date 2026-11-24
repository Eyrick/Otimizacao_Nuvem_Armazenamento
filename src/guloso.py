"""Algoritmo Guloso para a Mochila 0/1.

Ordena os arquivos pela razão importância/tamanho (v_i / w_i) em ordem
decrescente e os percorre nessa ordem, incluindo cada arquivo que ainda
couber no espaço restante.

A escolha é local (o arquivo com melhor razão naquele momento) e nunca é
desfeita, por isso o método é rápido, mas NÃO garante a solução ótima.
Exemplo: com C = 10 e arquivos (w, v) = (6, 60), (5, 45), (5, 45), o guloso
escolhe o primeiro (razão 10,0), sobram 4 MB e nada mais cabe: importância
60, contra 90 do ótimo ({2, 3}).

Complexidade:
    Tempo:  O(n log n), dominado pela ordenação; a varredura é O(n).
    Espaço: O(n) para a lista ordenada.

Não depende do valor de C, ao contrário da programação dinâmica.
"""

from __future__ import annotations

import time

from src.modelo import Instancia
from src.resultado import Resultado, montar_resultado

NOME = "Guloso"


def guloso(instancia: Instancia) -> Resultado:
    """Devolve uma solução viável (não necessariamente ótima) da instância."""
    inicio = time.perf_counter()

    # Ordena os índices por razão decrescente. Em caso de empate na razão,
    # prefere o arquivo de maior importância e, depois, o de menor índice,
    # para que o resultado seja sempre o mesmo (determinístico).
    ordem = sorted(
        range(instancia.n),
        key=lambda i: (
            -instancia.arquivos[i].razao,
            -instancia.arquivos[i].importancia,
            i,
        ),
    )

    restante = instancia.capacidade
    escolhidos_idx = []
    for i in ordem:
        arquivo = instancia.arquivos[i]
        # Escolha gulosa: inclui o arquivo se ainda couber. Não volta atrás.
        if arquivo.tamanho <= restante:
            escolhidos_idx.append(i)
            restante -= arquivo.tamanho

    # Devolve os arquivos escolhidos na ordem original da instância.
    escolhidos = [instancia.arquivos[i] for i in sorted(escolhidos_idx)]

    tempo = time.perf_counter() - inicio
    return montar_resultado(NOME, instancia, escolhidos, tempo)