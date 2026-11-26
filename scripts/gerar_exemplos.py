"""Gera exemplos grandes (CSVs e pastas) para testar e medir os algoritmos.

Uso, a partir da raiz do projeto:

    python scripts/gerar_exemplos.py
    python scripts/gerar_exemplos.py --ns 1000 100000 --perfis realista
    python scripts/gerar_exemplos.py --pastas 100 1000 --saida data/gerados

Perfis de instância:
    uniforme       tamanho (1 a 100 MB) e importância (1 a 100) sorteados de
                   forma uniforme e independente (o mesmo de src/gerador.py).
    realista       tipos de arquivo (documentos, fotos, vídeos, backups, logs)
                   com tamanhos em escala logarítmica e importância própria de
                   cada tipo. Os tamanhos chegam a milhares de MB.
    correlacionado importância próxima do tamanho (1 a 100 MB). É o caso
                   clássico em que o Guloso não ajuda: todos os arquivos têm
                   razão importância/tamanho parecida.

Saída (por padrão em data/gerados/):
    <perfil>_<n>.csv         lista de arquivos, no formato lido pelo programa
    pasta_<perfil>_<n>/      arquivos de verdade, com o tamanho do CSV
    pasta_<perfil>_<n>.csv   importâncias da pasta (a varredura usa 50 para todos)

Os arquivos das pastas são esparsos: têm o tamanho certo, mas quase não
ocupam disco em Linux e macOS. No Windows eles ocupam o espaço inteiro, a
menos que se use --esparso (só funciona em discos NTFS); sem essa opção, o
script recusa pastas com mais de --limite-gb (padrão 1) nesse sistema.
A mesma semente gera sempre os mesmos exemplos.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
from pathlib import Path

# Permite executar o script a partir da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gerador import SEMENTE_PADRAO, gerar_arquivos  # noqa: E402
from src.leitura import BYTES_POR_MB, salvar_csv  # noqa: E402
from src.modelo import IMPORTANCIA_MAX, IMPORTANCIA_MIN, Arquivo  # noqa: E402

PERFIS = ("uniforme", "realista", "correlacionado")
NS_PADRAO = (50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000)
PASTAS_PADRAO = (100, 1_000)
LIMITE_GB_PADRAO = 1.0

# Tipos do perfil "realista":
# (pasta, extensões, peso, tamanho mín e máx em MB, importância mín e máx)
TIPOS = (
    ("documentos", (".pdf", ".docx", ".xlsx", ".pptx"), 30, 1, 40, 55, 100),
    ("fotos", (".jpg", ".png", ".heic"), 35, 1, 25, 30, 85),
    ("videos", (".mp4", ".mov", ".mkv"), 10, 50, 1_500, 20, 90),
    ("backups", (".zip", ".tar.gz", ".bak"), 5, 100, 3_000, 5, 60),
    ("logs", (".log", ".txt"), 20, 1, 15, 1, 25),
)


def _log_uniforme(rng: random.Random, minimo: int, maximo: int) -> int:
    """Inteiro entre minimo e maximo com densidade uniforme em escala log."""
    if minimo == maximo:
        return minimo
    valor = math.exp(rng.uniform(math.log(minimo), math.log(maximo + 1)))
    return max(minimo, min(maximo, int(valor)))


def gerar_realista(n: int, semente: int) -> list[Arquivo]:
    """Arquivos de tipos variados, nomeados como pasta/tipo_NNN.ext."""
    rng = random.Random(semente)
    largura = max(3, len(str(n)))
    pesos = [t[2] for t in TIPOS]
    arquivos = []
    for i in range(1, n + 1):
        pasta, extensoes, _, t_min, t_max, i_min, i_max = rng.choices(TIPOS, pesos)[0]
        nome = f"{pasta}/{pasta[:-1]}_{i:0{largura}d}{rng.choice(extensoes)}"
        arquivos.append(
            Arquivo(nome, _log_uniforme(rng, t_min, t_max), rng.randint(i_min, i_max))
        )
    return arquivos


def gerar_correlacionado(n: int, semente: int) -> list[Arquivo]:
    """Importância = tamanho com ruído de até 5 pontos (limitada a 1..100)."""
    rng = random.Random(semente)
    largura = max(3, len(str(n)))
    arquivos = []
    for i in range(1, n + 1):
        tamanho = rng.randint(1, 100)
        importancia = tamanho + rng.randint(-5, 5)
        importancia = max(IMPORTANCIA_MIN, min(IMPORTANCIA_MAX, importancia))
        arquivos.append(Arquivo(f"arquivo_{i:0{largura}d}", tamanho, importancia))
    return arquivos


def gerar(perfil: str, n: int, semente: int) -> list[Arquivo]:
    """Gera n arquivos do perfil pedido. A semente depende de n."""
    semente = semente + 10_000 * n  # n diferentes não repetem sorteios
    if perfil == "uniforme":
        return gerar_arquivos(n, semente)
    if perfil == "realista":
        return gerar_realista(n, semente)
    if perfil == "correlacionado":
        return gerar_correlacionado(n, semente)
    raise ValueError(f"Perfil desconhecido: {perfil!r} (use {', '.join(PERFIS)}).")


def _marcar_esparso(f) -> None:
    """No Windows (NTFS), marca o arquivo como esparso antes de aumentá-lo.

    Sem isso o Windows reserva em disco o tamanho inteiro. Em outros sistemas
    os arquivos já são esparsos e esta função não faz nada.
    """
    if os.name != "nt":
        return
    import ctypes
    import msvcrt
    from ctypes import wintypes

    FSCTL_SET_SPARSE = 0x000900C4
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.DeviceIoControl.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    kernel32.DeviceIoControl.restype = wintypes.BOOL
    retornados = wintypes.DWORD(0)
    ok = kernel32.DeviceIoControl(
        msvcrt.get_osfhandle(f.fileno()), FSCTL_SET_SPARSE,
        None, 0, None, 0, ctypes.byref(retornados), None,
    )
    if not ok:
        raise OSError("este disco não aceita arquivos esparsos (use NTFS).")


def criar_pasta(arquivos: list[Arquivo], destino: Path, esparso: bool = False) -> None:
    """Cria os arquivos de verdade, com o tamanho em MB de cada um (esparsos)."""
    for a in arquivos:
        caminho = destino / a.nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "wb") as f:
            if esparso:
                _marcar_esparso(f)
            f.truncate(a.tamanho * BYTES_POR_MB)


def _gb(arquivos: list[Arquivo]) -> float:
    return sum(a.tamanho for a in arquivos) / 1024


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Gera CSVs e pastas de exemplo com muitos arquivos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--saida", default="data/gerados", help="pasta onde tudo é gravado")
    p.add_argument("--ns", type=int, nargs="*", default=list(NS_PADRAO),
                   help="quantidades de arquivos dos CSVs (vazio: nenhum CSV)")
    p.add_argument("--pastas", type=int, nargs="*", default=list(PASTAS_PADRAO),
                   help="quantidades de arquivos das pastas (vazio: nenhuma pasta)")
    p.add_argument("--perfis", nargs="+", choices=PERFIS, default=list(PERFIS))
    p.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    p.add_argument("--limite-gb", type=float, default=LIMITE_GB_PADRAO,
                   help="no Windows, tamanho máximo (GB) de cada pasta criada")
    p.add_argument("--esparso", action="store_true",
                   help="no Windows, marca os arquivos como esparsos (NTFS) e "
                        "dispensa o limite de tamanho")
    args = p.parse_args(argv)

    if any(n < 1 for n in (*args.ns, *args.pastas)):
        p.error("as quantidades devem ser inteiros positivos.")

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    avisos = 0

    for perfil in args.perfis:
        for n in args.ns:
            arquivos = gerar(perfil, n, args.semente)
            caminho = saida / f"{perfil}_{n}.csv"
            salvar_csv(arquivos, caminho)
            print(f"CSV   {caminho}  ({n} arquivos, {_gb(arquivos):,.1f} GB no total)")

        for n in args.pastas:
            arquivos = gerar(perfil, n, args.semente)
            pasta = saida / f"pasta_{perfil}_{n}"
            if pasta.exists() and any(pasta.iterdir()):
                print(f"PULOU {pasta}: já existe e não está vazia (apague-a para gerar de novo).")
                avisos += 1
                continue
            if os.name == "nt" and not args.esparso and _gb(arquivos) > args.limite_gb:
                print(
                    f"PULOU {pasta}: ocuparia {_gb(arquivos):,.1f} GB no Windows "
                    f"(limite {args.limite_gb:g} GB). Use o perfil 'uniforme' ou "
                    "'correlacionado', use --esparso ou aumente --limite-gb."
                )
                avisos += 1
                continue
            try:
                criar_pasta(arquivos, pasta, args.esparso)
            except OSError as erro:
                print(f"ERRO  {pasta}: {erro} Apague a pasta antes de tentar de novo.")
                return 1
            salvar_csv(arquivos, saida / f"pasta_{perfil}_{n}.csv")
            print(f"PASTA {pasta}  ({n} arquivos, {_gb(arquivos):,.1f} GB aparentes)")

    return 1 if avisos else 0


if __name__ == "__main__":
    sys.exit(principal())