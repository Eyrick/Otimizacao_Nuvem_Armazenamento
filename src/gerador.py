"""Gerador de instâncias sintéticas, reproduzível por semente.

As instâncias reais (pastas dos integrantes) são pequenas demais para os
experimentos com muitos arquivos. Este módulo gera arquivos fictícios com
tamanho e importância sorteados de forma uniforme, em intervalos
configuráveis. A mesma semente sempre produz a mesma instância (com a mesma
versão do Python), o que torna os experimentos reproduzíveis.

Para os experimentos, `gerar_cenarios` combina quantidades de arquivos (n),
capacidades (fração do tamanho total) e repetições. Para um mesmo n e uma
mesma repetição, o conjunto de arquivos é o mesmo em todas as capacidades:
só o espaço disponível muda, o que isola o efeito de C.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.leitura import LeituraError, montar_instancia
from src.modelo import IMPORTANCIA_MAX, IMPORTANCIA_MIN, Arquivo, Instancia

TAMANHO_MIN_PADRAO = 1
TAMANHO_MAX_PADRAO = 100  # MB
SEMENTE_PADRAO = 2026
LIMITE_REPETICOES = 10_000  # evita que sementes de n diferentes se sobreponham


@dataclass(frozen=True)
class Cenario:
    """Uma instância gerada, com os parâmetros que a definem.

    Atributos:
        n: quantidade de arquivos.
        fracao: capacidade como fração do tamanho total.
        repeticao: índice da repetição (0, 1, ...).
        semente: semente usada para sortear os arquivos.
        instancia: a instância pronta para os algoritmos.
    """

    n: int
    fracao: float
    repeticao: int
    semente: int
    instancia: Instancia

    @property
    def descricao(self) -> str:
        return (
            f"n={self.n}, C={self.fracao:.0%} do total "
            f"({self.instancia.capacidade} MB), semente={self.semente}"
        )


def gerar_arquivos(
    n: int,
    semente: int = SEMENTE_PADRAO,
    tamanho_min: int = TAMANHO_MIN_PADRAO,
    tamanho_max: int = TAMANHO_MAX_PADRAO,
    importancia_min: int = IMPORTANCIA_MIN,
    importancia_max: int = IMPORTANCIA_MAX,
) -> list[Arquivo]:
    """Gera n arquivos fictícios (arquivo_001, arquivo_002, ...).

    Tamanhos (MB) e importâncias são inteiros sorteados uniformemente nos
    intervalos fechados informados.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise LeituraError(f"n deve ser um inteiro positivo, mas veio {n!r}.")
    if not 1 <= tamanho_min <= tamanho_max:
        raise LeituraError(
            f"Intervalo de tamanho inválido: [{tamanho_min}, {tamanho_max}] MB."
        )
    if not IMPORTANCIA_MIN <= importancia_min <= importancia_max <= IMPORTANCIA_MAX:
        raise LeituraError(
            f"Intervalo de importância inválido: [{importancia_min}, {importancia_max}] "
            f"(deve estar dentro de [{IMPORTANCIA_MIN}, {IMPORTANCIA_MAX}])."
        )

    rng = random.Random(semente)
    largura = max(3, len(str(n)))  # zeros à esquerda: ordem alfabética = ordem numérica
    arquivos = []
    for i in range(1, n + 1):
        arquivos.append(
            Arquivo(
                f"arquivo_{i:0{largura}d}",
                rng.randint(tamanho_min, tamanho_max),
                rng.randint(importancia_min, importancia_max),
            )
        )
    return arquivos


def gerar_instancia(
    n: int,
    fracao: float,
    semente: int = SEMENTE_PADRAO,
    **intervalos: int,
) -> Instancia:
    """Gera n arquivos e define a capacidade como fração do tamanho total.

    `intervalos` aceita tamanho_min, tamanho_max, importancia_min e
    importancia_max (ver `gerar_arquivos`).
    """
    arquivos = gerar_arquivos(n, semente, **intervalos)
    return montar_instancia(arquivos, fracao=fracao)


def gerar_cenarios(
    ns: list[int] | tuple[int, ...],
    fracoes: list[float] | tuple[float, ...],
    repeticoes: int = 1,
    semente_base: int = SEMENTE_PADRAO,
    **intervalos: int,
) -> list[Cenario]:
    """Gera todas as combinações (n, repetição, fração) para os experimentos.

    A semente de cada conjunto de arquivos é
    `semente_base + 10000 * n + repeticao`: depende de n e da repetição, mas
    não da fração. Assim, as frações usam os mesmos arquivos, e conjuntos de
    n diferentes são independentes entre si.
    """
    if isinstance(repeticoes, bool) or not isinstance(repeticoes, int) or not (
        1 <= repeticoes <= LIMITE_REPETICOES
    ):
        raise LeituraError(
            f"repeticoes deve estar entre 1 e {LIMITE_REPETICOES}, mas veio {repeticoes!r}."
        )

    cenarios = []
    for n in ns:
        for repeticao in range(repeticoes):
            semente = semente_base + 10_000 * n + repeticao
            arquivos = gerar_arquivos(n, semente, **intervalos)
            for fracao in fracoes:
                instancia = montar_instancia(arquivos, fracao=fracao)
                cenarios.append(Cenario(n, fracao, repeticao, semente, instancia))
    return cenarios