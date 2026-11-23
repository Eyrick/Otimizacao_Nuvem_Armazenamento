"""Algoritmo de Força Bruta para a Mochila 0/1.

Enumera todos os 2^n subconjuntos de arquivos por recursão, decidindo para
cada arquivo se ele entra ou não na solução. Ao chegar ao final (folha),
o subconjunto é aceito se couber na capacidade, e o de maior importância
é guardado.

Complexidade:
    Tempo:  T(n) = 2 T(n-1) + O(1)  =>  O(2^n)
            (o peso e a importância são acumulados durante a descida, então
            cada subconjunto custa O(1) amortizado; se fossem recalculados do
            zero em cada folha, o custo seria O(n * 2^n)).
    Espaço: O(n), correspondente à pilha de recursão.

Não há poda: todas as 2^n folhas são visitadas. Isso mantém o algoritmo como
referência de correção e deixa o crescimento exponencial evidente nos
experimentos.
"""

from __future__ import annotations

import time

from src.modelo import Instancia
from src.resultado import Resultado, montar_resultado

NOME = "Força Bruta"


def forca_bruta(instancia: Instancia) -> Resultado:
    """Devolve a solução ótima da instância, testando todas as combinações."""
    arquivos = instancia.arquivos
    n = instancia.n
    capacidade = instancia.capacidade

    # Melhor solução encontrada até o momento. A seleção é guardada como uma
    # máscara de bits: o bit i vale 1 se o arquivo i foi escolhido.
    melhor_valor = -1
    melhor_peso = 0
    melhor_mascara = 0

    def explorar(i: int, peso: int, valor: int, mascara: int) -> None:
        nonlocal melhor_valor, melhor_peso, melhor_mascara

        if i == n:
            # Folha: um subconjunto completo foi definido. Só é aceito se
            # respeitar a restrição de capacidade. Em caso de empate no
            # valor, prefere-se o que usa menos espaço.
            if peso <= capacidade and (
                valor > melhor_valor
                or (valor == melhor_valor and peso < melhor_peso)
            ):
                melhor_valor = valor
                melhor_peso = peso
                melhor_mascara = mascara
            return

        arquivo = arquivos[i]
        # Ramo 1: o arquivo i entra na solução.
        explorar(
            i + 1,
            peso + arquivo.tamanho,
            valor + arquivo.importancia,
            mascara | (1 << i),
        )
        # Ramo 2: o arquivo i fica de fora.
        explorar(i + 1, peso, valor, mascara)

    inicio = time.perf_counter()
    explorar(0, 0, 0, 0)
    tempo = time.perf_counter() - inicio

    selecionados = [a for i, a in enumerate(arquivos) if melhor_mascara >> i & 1]
    return montar_resultado(NOME, instancia, selecionados, tempo)