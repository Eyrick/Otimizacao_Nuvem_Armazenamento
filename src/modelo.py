"""Modelo de dados do problema de armazenamento em nuvem (Mochila 0/1).

Cada arquivo tem um tamanho w_i (MB, inteiro positivo) e uma importância
v_i (inteiro de 1 a 100). Uma instância reúne os n arquivos e a
capacidade C de armazenamento (MB, inteiro positivo).

As validações ficam aqui, no momento da criação dos objetos, para que os
algoritmos possam assumir entradas corretas (em especial, tamanhos e
capacidade inteiros, exigência da programação dinâmica).
"""

from __future__ import annotations

from dataclasses import dataclass

IMPORTANCIA_MIN = 1
IMPORTANCIA_MAX = 100


class ModeloError(ValueError):
    """Erro de validação dos dados de entrada."""


def _eh_inteiro(valor: object) -> bool:
    # bool é subclasse de int em Python, mas não é um valor válido aqui.
    return isinstance(valor, int) and not isinstance(valor, bool)


@dataclass(frozen=True)
class Arquivo:
    """Um arquivo candidato ao armazenamento.

    Atributos:
        nome: identificação do arquivo (não vazia).
        tamanho: w_i, em MB (inteiro positivo).
        importancia: v_i (inteiro entre 1 e 100).
    """

    nome: str
    tamanho: int
    importancia: int

    def __post_init__(self) -> None:
        if not isinstance(self.nome, str) or not self.nome.strip():
            raise ModeloError("O nome do arquivo não pode ser vazio.")
        if not _eh_inteiro(self.tamanho) or self.tamanho <= 0:
            raise ModeloError(
                f"Tamanho inválido para '{self.nome}': {self.tamanho!r} "
                "(esperado inteiro positivo, em MB)."
            )
        if (
            not _eh_inteiro(self.importancia)
            or not IMPORTANCIA_MIN <= self.importancia <= IMPORTANCIA_MAX
        ):
            raise ModeloError(
                f"Importância inválida para '{self.nome}': {self.importancia!r} "
                f"(esperado inteiro de {IMPORTANCIA_MIN} a {IMPORTANCIA_MAX})."
            )

    @property
    def razao(self) -> float:
        """Razão importância/tamanho (v_i / w_i), usada pelo guloso."""
        return self.importancia / self.tamanho


@dataclass(frozen=True)
class Instancia:
    """Uma instância do problema: arquivos disponíveis e capacidade C.

    Atributos:
        arquivos: os n arquivos disponíveis (ao menos um).
        capacidade: C, em MB (inteiro positivo).
    """

    arquivos: tuple[Arquivo, ...]
    capacidade: int

    def __post_init__(self) -> None:
        # Aceita qualquer sequência e guarda como tupla imutável.
        object.__setattr__(self, "arquivos", tuple(self.arquivos))

        if not self.arquivos:
            raise ModeloError("A instância precisa de pelo menos um arquivo.")
        if not all(isinstance(a, Arquivo) for a in self.arquivos):
            raise ModeloError("Todos os itens de 'arquivos' devem ser Arquivo.")
        if not _eh_inteiro(self.capacidade) or self.capacidade <= 0:
            raise ModeloError(
                f"Capacidade inválida: {self.capacidade!r} "
                "(esperado inteiro positivo, em MB)."
            )

    @property
    def n(self) -> int:
        """Quantidade de arquivos."""
        return len(self.arquivos)

    @property
    def tamanho_total(self) -> int:
        """Soma dos tamanhos de todos os arquivos, em MB."""
        return sum(a.tamanho for a in self.arquivos)

    @property
    def importancia_total(self) -> int:
        """Soma das importâncias de todos os arquivos."""
        return sum(a.importancia for a in self.arquivos)
