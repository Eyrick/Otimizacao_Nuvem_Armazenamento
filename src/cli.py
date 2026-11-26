"""Interface de linha de comando (menu interativo no terminal).

Fluxo:
    1. Escolher como obter a instância: cadastro manual, CSV, pasta do
       sistema ou instância sintética.
    2. Definir a capacidade, em MB ou como porcentagem do tamanho total.
    3. Executar a Força Bruta, a Programação Dinâmica, o Guloso ou comparar
       os três.

Toda a entrada e a saída passam por `Terminal`, que recebe as funções de
leitura e escrita. Isso permite testar o menu sem teclado real.
"""

from __future__ import annotations

import os
from typing import Callable

from src.forca_bruta import forca_bruta
from src.gerador import SEMENTE_PADRAO, gerar_arquivos
from src.guloso import guloso
from src.leitura import (
    IMPORTANCIA_PADRAO,
    LeituraError,
    ler_arquivos_csv,
    montar_instancia,
    salvar_csv,
    varrer_pasta,
)
from src.modelo import IMPORTANCIA_MAX, IMPORTANCIA_MIN, Arquivo, Instancia
from src.programacao_dinamica import programacao_dinamica
from src.resultado import Resultado

TITULO = "Otimização de Armazenamento em Nuvem (Mochila 0/1)"

# Acima destes limites o programa pede confirmação antes de executar.
LIMITE_FORCA_BRUTA = 25  # n: a Força Bruta examina 2^n combinações
LIMITE_CELULAS_PD = 20_000_000  # (n + 1) * (C + 1): tamanho da tabela da PD
LIMITE_LISTAGEM = 15  # até quantos arquivos listar ao carregar a instância

NOME_FB = "Força Bruta"
NOME_PD = "Programação Dinâmica"
NOME_GULOSO = "Guloso"


class Sair(Exception):
    """Pedido do usuário para encerrar o programa."""


class Terminal:
    """Entrada e saída de texto com validação simples."""

    def __init__(
        self,
        entrada: Callable[[str], str] = input,
        saida: Callable[[str], None] = print,
    ) -> None:
        self._entrada = entrada
        self._saida = saida

    def escrever(self, texto: str = "") -> None:
        self._saida(texto)

    def perguntar(self, texto: str) -> str:
        return self._entrada(texto).strip()

    def inteiro(self, texto: str, minimo: int | None = None, maximo: int | None = None) -> int:
        """Pergunta até receber um inteiro dentro da faixa."""
        while True:
            try:
                valor = int(self.perguntar(texto))
            except ValueError:
                valor = None
            if (
                valor is not None
                and (minimo is None or valor >= minimo)
                and (maximo is None or valor <= maximo)
            ):
                return valor
            if minimo is not None and maximo is not None:
                faixa = f" entre {minimo} e {maximo}"
            elif minimo is not None:
                faixa = f" maior ou igual a {minimo}"
            else:
                faixa = ""
            self.escrever(f"  Valor inválido. Digite um número inteiro{faixa}.")

    def sim_nao(self, texto: str, padrao: bool = False) -> bool:
        """Pergunta s/n; Enter escolhe o padrão."""
        while True:
            resposta = self.perguntar(texto).lower()
            if not resposta:
                return padrao
            if resposta in ("s", "sim"):
                return True
            if resposta in ("n", "nao", "não"):
                return False
            self.escrever("  Responda com s ou n.")

    def opcao(self, linhas: list[str], validas: set[str]) -> str:
        """Mostra o menu e pergunta até receber uma opção válida."""
        for linha in linhas:
            self.escrever(linha)
        while True:
            escolha = self.perguntar("Opção: ")
            if escolha in validas:
                return escolha
            self.escrever("  Opção inválida.")


def _num(valor: float, casas: int) -> str:
    """Formata número com vírgula decimal (padrão brasileiro)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Obtenção da instância
# ---------------------------------------------------------------------------

def definir_capacidade(t: Terminal, arquivos: list[Arquivo]) -> Instancia:
    """Pergunta a capacidade (MB ou porcentagem) e monta a instância."""
    total = sum(a.tamanho for a in arquivos)
    t.escrever(f"Tamanho total dos arquivos: {total} MB.")
    while True:
        bruto = t.perguntar("Capacidade em MB (ex.: 500) ou % do total (ex.: 30%): ")
        try:
            if bruto.endswith("%"):
                fracao = float(bruto[:-1].replace(",", ".")) / 100
                return montar_instancia(arquivos, fracao=fracao)
            return montar_instancia(arquivos, capacidade=int(bruto))
        except LeituraError as erro:
            t.escrever(f"  Capacidade inválida: {erro}")
        except ValueError:
            t.escrever("  Digite um inteiro (MB) ou uma porcentagem, como 30%.")


def cadastrar_manual(t: Terminal) -> Instancia:
    n = t.inteiro("Quantos arquivos deseja cadastrar? ", minimo=1)
    arquivos: list[Arquivo] = []
    nomes: set[str] = set()
    for i in range(1, n + 1):
        t.escrever(f"Arquivo {i} de {n}")
        while True:
            nome = t.perguntar("  Nome: ")
            if not nome:
                t.escrever("  O nome não pode ser vazio.")
            elif nome in nomes:
                t.escrever("  Já existe um arquivo com esse nome.")
            else:
                break
        tamanho = t.inteiro("  Tamanho (MB, inteiro): ", minimo=1)
        importancia = t.inteiro(
            f"  Importância ({IMPORTANCIA_MIN} a {IMPORTANCIA_MAX}): ",
            IMPORTANCIA_MIN,
            IMPORTANCIA_MAX,
        )
        nomes.add(nome)
        arquivos.append(Arquivo(nome, tamanho, importancia))
    return definir_capacidade(t, arquivos)


def _detectar_delimitador(caminho: str) -> str:
    """Usa ';' se o cabeçalho do CSV for separado por ponto e vírgula."""
    with open(caminho, encoding="utf-8-sig") as f:
        for linha in f:
            if linha.strip():
                return ";" if linha.count(";") > linha.count(",") else ","
    return ","


def _limpar_caminho(texto: str) -> str:
    # Remove aspas que o terminal costuma incluir ao colar um caminho.
    return texto.strip().strip("\"'")


def carregar_csv(t: Terminal) -> Instancia | None:
    caminho = _limpar_caminho(t.perguntar("Caminho do CSV: "))
    try:
        arquivos = ler_arquivos_csv(caminho, _detectar_delimitador(caminho))
    except (LeituraError, OSError) as erro:
        t.escrever(f"Não foi possível ler o CSV: {erro}")
        return None
    t.escrever(f"{len(arquivos)} arquivos lidos.")
    return definir_capacidade(t, arquivos)


def carregar_pasta(t: Terminal) -> Instancia | None:
    caminho = _limpar_caminho(t.perguntar("Caminho da pasta: "))
    recursivo = t.sim_nao("Incluir subpastas? (s/N): ")
    try:
        arquivos = varrer_pasta(caminho, recursivo=recursivo)
    except LeituraError as erro:
        t.escrever(f"Não foi possível ler a pasta: {erro}")
        return None
    t.escrever(
        f"{len(arquivos)} arquivos encontrados, todos com importância "
        f"{IMPORTANCIA_PADRAO} (a importância é um julgamento seu)."
    )
    destino = _limpar_caminho(
        t.perguntar(
            "Para editar as importâncias, informe onde salvar um CSV "
            "(Enter para continuar sem salvar): "
        )
    )
    if destino:
        try:
            salvar_csv(arquivos, destino)
        except OSError as erro:
            t.escrever(f"Não foi possível salvar o CSV: {erro}")
            return None
        t.escrever(
            f"CSV salvo em {destino}. Edite a coluna 'importancia' e "
            "carregue-o pela opção de CSV."
        )
        return None
    return definir_capacidade(t, arquivos)


def gerar_sintetica(t: Terminal) -> Instancia:
    n = t.inteiro("Quantidade de arquivos: ", minimo=1)
    while True:
        bruto = t.perguntar(f"Semente (Enter para {SEMENTE_PADRAO}): ")
        if not bruto:
            semente = SEMENTE_PADRAO
            break
        try:
            semente = int(bruto)
            break
        except ValueError:
            t.escrever("  A semente deve ser um número inteiro.")
    return definir_capacidade(t, gerar_arquivos(n, semente))


def menu_instancia(t: Terminal) -> Instancia:
    """Repete o menu até obter uma instância; levanta Sair para encerrar."""
    acoes = {
        "1": cadastrar_manual,
        "2": carregar_csv,
        "3": carregar_pasta,
        "4": gerar_sintetica,
    }
    while True:
        t.escrever()
        escolha = t.opcao(
            [
                "Como deseja obter os arquivos?",
                "  1) Cadastrar manualmente",
                "  2) Ler de um CSV",
                "  3) Varrer uma pasta do computador",
                "  4) Gerar uma instância sintética",
                "  0) Sair",
            ],
            {"0", *acoes},
        )
        if escolha == "0":
            raise Sair
        instancia = acoes[escolha](t)
        if instancia is not None:
            return instancia


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------

def mostrar_arquivos(t: Terminal, arquivos: tuple[Arquivo, ...]) -> None:
    largura = max(len(a.nome) for a in arquivos)
    for a in arquivos:
        t.escrever(f"  {a.nome.ljust(largura)}  {a.tamanho:>6} MB   importância {a.importancia:>3}")


def mostrar_instancia(t: Terminal, instancia: Instancia, listar: bool = True) -> None:
    pct = instancia.capacidade / instancia.tamanho_total * 100
    t.escrever()
    t.escrever(
        f"Instância: {instancia.n} arquivos, {instancia.tamanho_total} MB no total; "
        f"capacidade de {instancia.capacidade} MB ({_num(pct, 1)}% do total)."
    )
    if listar:
        mostrar_arquivos(t, instancia.arquivos)


def mostrar_resultado(t: Terminal, r: Resultado) -> None:
    t.escrever()
    t.escrever(f"--- {r.algoritmo} ---")
    if r.selecionados:
        t.escrever(f"Arquivos selecionados ({len(r.selecionados)}):")
        mostrar_arquivos(t, r.selecionados)
    else:
        t.escrever("Nenhum arquivo selecionado.")
    t.escrever(f"Importância total: {r.importancia_total}")
    t.escrever(
        f"Espaço usado: {r.espaco_usado} MB de {r.capacidade} MB "
        f"(restante: {r.espaco_restante} MB)"
    )
    t.escrever(f"Tempo de execução: {_num(r.tempo, 6)} s")


def mostrar_comparacao(t: Terminal, resultados: list[Resultado]) -> None:
    exatos = [r.importancia_total for r in resultados if r.algoritmo in (NOME_FB, NOME_PD)]
    otimo = max(exatos) if exatos else None

    cabecalho = ("Algoritmo", "Importância", "Espaço usado", "Tempo (s)", "Perda vs. ótimo")
    linhas = []
    for r in resultados:
        if otimo is None:
            perda = "-"
        else:
            perda = _num((otimo - r.importancia_total) / otimo * 100 if otimo else 0.0, 2) + "%"
        linhas.append(
            (
                r.algoritmo,
                str(r.importancia_total),
                f"{r.espaco_usado} / {r.capacidade} MB",
                _num(r.tempo, 6),
                perda,
            )
        )
    larguras = [max(len(c[i]) for c in [cabecalho, *linhas]) for i in range(len(cabecalho))]

    def formatar(linha: tuple[str, ...]) -> str:
        celulas = [linha[0].ljust(larguras[0])]
        celulas += [linha[i].rjust(larguras[i]) for i in range(1, len(linha))]
        return "  ".join(celulas)

    t.escrever()
    t.escrever(formatar(cabecalho))
    t.escrever("  ".join("-" * w for w in larguras))
    for linha in linhas:
        t.escrever(formatar(linha))


# ---------------------------------------------------------------------------
# Execução dos algoritmos
# ---------------------------------------------------------------------------

def _confirmar(t: Terminal, instancia: Instancia, nome: str) -> bool:
    """Avisa quando a execução tende a ser muito longa ou pesada."""
    if nome == NOME_FB and instancia.n > LIMITE_FORCA_BRUTA:
        t.escrever(
            f"A Força Bruta examina 2^{instancia.n} combinações e pode levar muito tempo."
        )
    elif nome == NOME_PD:
        celulas = (instancia.n + 1) * (instancia.capacidade + 1)
        if celulas <= LIMITE_CELULAS_PD:
            return True
        t.escrever(
            f"A tabela da Programação Dinâmica terá {_milhar(celulas)} posições "
            "e pode consumir muita memória."
        )
    else:
        return True
    if t.sim_nao("Continuar? (s/N): "):
        return True
    t.escrever(f"{nome} não foi executada.")
    return False


ALGORITMOS = (
    (NOME_FB, forca_bruta),
    (NOME_PD, programacao_dinamica),
    (NOME_GULOSO, guloso),
)


def executar_um(t: Terminal, instancia: Instancia, indice: int) -> None:
    nome, funcao = ALGORITMOS[indice]
    if _confirmar(t, instancia, nome):
        mostrar_resultado(t, funcao(instancia))


def executar_todos(t: Terminal, instancia: Instancia) -> None:
    resultados = [
        funcao(instancia) for nome, funcao in ALGORITMOS if _confirmar(t, instancia, nome)
    ]
    if resultados:
        mostrar_comparacao(t, resultados)


def menu_algoritmos(t: Terminal, instancia: Instancia) -> None:
    """Menu de execução. Retorna ao escolher outra instância; Sair encerra."""
    mostrar_instancia(t, instancia, listar=instancia.n <= LIMITE_LISTAGEM)
    while True:
        t.escrever()
        escolha = t.opcao(
            [
                "O que deseja executar?",
                f"  1) {NOME_FB}",
                f"  2) {NOME_PD}",
                f"  3) {NOME_GULOSO}",
                "  4) Comparar os três",
                "  5) Mostrar os arquivos da instância",
                "  6) Carregar outra instância",
                "  0) Sair",
            ],
            {"0", "1", "2", "3", "4", "5", "6"},
        )
        if escolha == "0":
            raise Sair
        if escolha == "6":
            return
        if escolha == "5":
            mostrar_instancia(t, instancia, listar=True)
        elif escolha == "4":
            executar_todos(t, instancia)
        else:
            executar_um(t, instancia, int(escolha) - 1)


def main(
    entrada: Callable[[str], str] = input,
    saida: Callable[[str], None] = print,
) -> int:
    """Executa o programa. Devolve o código de saída."""
    t = Terminal(entrada, saida)
    t.escrever(TITULO)
    try:
        while True:
            instancia = menu_instancia(t)
            menu_algoritmos(t, instancia)
    except Sair:
        t.escrever("Até logo.")
        return 0
    except EOFError:
        t.escrever("\nEntrada encerrada.")
        return 0
    except KeyboardInterrupt:
        t.escrever("\nInterrompido.")
        return 130