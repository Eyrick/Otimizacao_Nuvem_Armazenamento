"""Leitura de instâncias reais: arquivos CSV e pastas do sistema.

Fluxo de trabalho previsto na metodologia:

    1. `varrer_pasta` lê os tamanhos reais dos arquivos de uma pasta e
       atribui uma importância padrão a todos;
    2. `salvar_csv` grava o resultado em um CSV;
    3. o grupo edita a coluna de importância (1 a 100) no CSV;
    4. `carregar_instancia` lê o CSV e monta a instância, definindo a
       capacidade em MB ou como fração do tamanho total.

Formato do CSV (com cabeçalho, codificação UTF-8):

    nome,tamanho_mb,importancia
    relatorio.pdf,12,95

Tamanhos em MB inteiros: a conversão de bytes arredonda para cima, para que
a solução continue viável com o tamanho real (um arquivo de 1 byte conta
como 1 MB, e nunca como 0).
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from src.modelo import Arquivo, Instancia, ModeloError

CABECALHO = ("nome", "tamanho_mb", "importancia")
IMPORTANCIA_PADRAO = 50
BYTES_POR_MB = 1024 * 1024


class LeituraError(ValueError):
    """Erro ao ler um CSV ou uma pasta."""


def bytes_para_mb(tamanho_bytes: int) -> int:
    """Converte bytes em MB inteiros, arredondando para cima (mínimo 1)."""
    if tamanho_bytes < 0:
        raise LeituraError(f"Tamanho em bytes inválido: {tamanho_bytes}.")
    # Divisão inteira com teto, sem passar por ponto flutuante.
    mb = -(-tamanho_bytes // BYTES_POR_MB)
    return max(1, mb)


def _inteiro(texto: str, campo: str, linha: int) -> int:
    try:
        return int(texto.strip())
    except ValueError:
        raise LeituraError(
            f"Linha {linha}: '{campo}' deve ser um número inteiro, mas veio {texto!r}."
        ) from None


def ler_arquivos_csv(caminho: str | os.PathLike, delimitador: str = ",") -> list[Arquivo]:
    """Lê os arquivos de um CSV (cabeçalho: nome,tamanho_mb,importancia).

    Linhas em branco são ignoradas. Qualquer problema (cabeçalho errado,
    número de colunas, valor não inteiro, valor fora do intervalo ou nome
    repetido) levanta `LeituraError` indicando a linha.
    """
    arquivos: list[Arquivo] = []
    nomes: set[str] = set()
    cabecalho_lido = False

    # utf-8-sig aceita CSV exportado pelo Excel (que costuma incluir BOM).
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        for numero, linha in enumerate(csv.reader(f, delimiter=delimitador), start=1):
            if not any(celula.strip() for celula in linha):
                continue  # linha em branco

            if not cabecalho_lido:
                colunas = tuple(c.strip().lower() for c in linha)
                if colunas != CABECALHO:
                    raise LeituraError(
                        f"Linha {numero}: cabeçalho esperado "
                        f"'{','.join(CABECALHO)}', mas veio '{','.join(linha)}'."
                    )
                cabecalho_lido = True
                continue

            if len(linha) != len(CABECALHO):
                raise LeituraError(
                    f"Linha {numero}: esperadas {len(CABECALHO)} colunas, "
                    f"mas vieram {len(linha)}."
                )
            nome = linha[0].strip()
            tamanho = _inteiro(linha[1], "tamanho_mb", numero)
            importancia = _inteiro(linha[2], "importancia", numero)
            try:
                arquivo = Arquivo(nome, tamanho, importancia)
            except ModeloError as erro:
                raise LeituraError(f"Linha {numero}: {erro}") from None
            if nome in nomes:
                raise LeituraError(f"Linha {numero}: nome repetido '{nome}'.")
            nomes.add(nome)
            arquivos.append(arquivo)

    if not arquivos:
        raise LeituraError("O CSV não contém nenhum arquivo.")
    return arquivos


def salvar_csv(
    arquivos: list[Arquivo] | tuple[Arquivo, ...],
    caminho: str | os.PathLike,
    delimitador: str = ",",
) -> None:
    """Grava os arquivos em um CSV no formato lido por `ler_arquivos_csv`."""
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=delimitador)
        escritor.writerow(CABECALHO)
        for a in arquivos:
            escritor.writerow((a.nome, a.tamanho, a.importancia))


def varrer_pasta(
    pasta: str | os.PathLike,
    recursivo: bool = False,
    importancia: int = IMPORTANCIA_PADRAO,
) -> list[Arquivo]:
    """Lista os arquivos de uma pasta com o tamanho real (em MB, para cima).

    Todos recebem a mesma `importancia` (padrão 50): ela deve ser editada
    depois, no CSV gerado por `salvar_csv`. O nome é o caminho relativo à
    pasta, com '/' como separador, e o resultado sai em ordem alfabética,
    para ser reproduzível. Links simbólicos e arquivos ilegíveis são
    ignorados.
    """
    raiz = Path(pasta)
    if not raiz.is_dir():
        raise LeituraError(f"'{pasta}' não é uma pasta.")

    encontrados: list[Arquivo] = []
    for diretorio, subpastas, nomes in os.walk(raiz, followlinks=False):
        if not recursivo:
            subpastas.clear()  # não desce nas subpastas
        for nome in nomes:
            caminho = Path(diretorio) / nome
            try:
                if caminho.is_symlink() or not caminho.is_file():
                    continue
                tamanho = bytes_para_mb(caminho.stat().st_size)
            except OSError:
                continue  # sem permissão ou removido durante a varredura
            relativo = caminho.relative_to(raiz).as_posix()
            encontrados.append(Arquivo(relativo, tamanho, importancia))

    if not encontrados:
        raise LeituraError(f"Nenhum arquivo encontrado em '{pasta}'.")
    return sorted(encontrados, key=lambda a: a.nome)


def capacidade_por_fracao(arquivos: list[Arquivo] | tuple[Arquivo, ...], fracao: float) -> int:
    """Capacidade como fração do tamanho total (parte inteira, mínimo 1 MB).

    Ex.: arquivos somando 100 MB e fracao=0.3 resultam em C = 30 MB.
    """
    if not 0 < fracao <= 1:
        raise LeituraError(f"A fração deve estar em (0, 1], mas veio {fracao!r}.")
    total = sum(a.tamanho for a in arquivos)
    return max(1, int(total * fracao))


def montar_instancia(
    arquivos: list[Arquivo] | tuple[Arquivo, ...],
    capacidade: int | None = None,
    fracao: float | None = None,
) -> Instancia:
    """Cria a instância com a capacidade em MB ou como fração do total."""
    if (capacidade is None) == (fracao is None):
        raise LeituraError("Informe a capacidade OU a fração, mas não os dois.")
    if capacidade is None:
        capacidade = capacidade_por_fracao(arquivos, fracao)
    try:
        return Instancia(arquivos, capacidade)
    except ModeloError as erro:
        raise LeituraError(str(erro)) from None


def carregar_instancia(
    caminho: str | os.PathLike,
    capacidade: int | None = None,
    fracao: float | None = None,
    delimitador: str = ",",
) -> Instancia:
    """Lê um CSV e devolve a instância pronta para os algoritmos."""
    arquivos = ler_arquivos_csv(caminho, delimitador)
    return montar_instancia(arquivos, capacidade, fracao)