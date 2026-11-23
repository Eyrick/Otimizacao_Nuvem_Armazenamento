"""Tipo de resultado compartilhado pelos algoritmos.

Todos os algoritmos (força bruta, programação dinâmica e guloso) devolvem
um `Resultado`, o que permite compará-los de forma uniforme.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.modelo import Arquivo, Instancia


@dataclass(frozen=True)
class Resultado:
    """Solução encontrada por um algoritmo para uma instância.

    Atributos:
        algoritmo: nome do algoritmo que gerou a solução.
        selecionados: arquivos escolhidos, na ordem original da instância.
        importancia_total: valor da função objetivo Z = soma de v_i x_i.
        espaco_usado: soma dos tamanhos dos arquivos escolhidos, em MB.
        capacidade: capacidade C da instância, em MB.
        tempo: tempo de execução do algoritmo, em segundos.
    """

    algoritmo: str
    selecionados: tuple[Arquivo, ...]
    importancia_total: int
    espaco_usado: int
    capacidade: int
    tempo: float

    @property
    def espaco_restante(self) -> int:
        """Espaço que sobrou na capacidade, em MB."""
        return self.capacidade - self.espaco_usado


def montar_resultado(
    algoritmo: str,
    instancia: Instancia,
    selecionados: tuple[Arquivo, ...] | list[Arquivo],
    tempo: float,
) -> Resultado:
    """Cria um Resultado calculando os totais a partir dos arquivos escolhidos.

    Também confere a restrição do problema (soma dos tamanhos <= C), de modo
    que um algoritmo com defeito não consiga devolver uma solução inviável
    sem que isso seja percebido.
    """
    selecionados = tuple(selecionados)
    espaco = sum(a.tamanho for a in selecionados)
    if espaco > instancia.capacidade:
        raise ValueError(
            f"Solução inviável: {espaco} MB excede a capacidade "
            f"de {instancia.capacidade} MB."
        )
    return Resultado(
        algoritmo=algoritmo,
        selecionados=selecionados,
        importancia_total=sum(a.importancia for a in selecionados),
        espaco_usado=espaco,
        capacidade=instancia.capacidade,
        tempo=tempo,
    )