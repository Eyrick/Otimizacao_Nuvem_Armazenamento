"""Testes do script que gera CSVs e pastas de exemplo."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Permite executar os testes a partir da raiz do projeto.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

from gerar_exemplos import PERFIS, gerar, principal  # noqa: E402
from src.leitura import ler_arquivos_csv, varrer_pasta  # noqa: E402
from src.modelo import IMPORTANCIA_MAX, IMPORTANCIA_MIN  # noqa: E402


def executar(*argumentos):
    """Roda o script sem poluir a saída dos testes; devolve (código, texto)."""
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        codigo = principal(list(argumentos))
    return codigo, saida.getvalue()


class TestPerfis(unittest.TestCase):
    def test_quantidade_nomes_unicos_e_limites(self):
        for perfil in PERFIS:
            arqs = gerar(perfil, 300, 1)
            self.assertEqual(len(arqs), 300, perfil)
            self.assertEqual(len({a.nome for a in arqs}), 300, perfil)
            for a in arqs:
                self.assertGreaterEqual(a.tamanho, 1)
                self.assertTrue(IMPORTANCIA_MIN <= a.importancia <= IMPORTANCIA_MAX)

    def test_reproduzivel_e_depende_da_semente(self):
        for perfil in PERFIS:
            self.assertEqual(gerar(perfil, 50, 7), gerar(perfil, 50, 7))
            self.assertNotEqual(gerar(perfil, 50, 7), gerar(perfil, 50, 8))

    def test_realista_tem_tipos_e_tamanhos_grandes(self):
        arqs = gerar("realista", 2000, 1)
        pastas = {a.nome.split("/")[0] for a in arqs}
        self.assertEqual(pastas, {"documentos", "fotos", "videos", "backups", "logs"})
        self.assertGreater(max(a.tamanho for a in arqs), 1000)
        # Respeita os intervalos de cada tipo.
        for a in arqs:
            if a.nome.startswith("videos/"):
                self.assertTrue(50 <= a.tamanho <= 1500 and 20 <= a.importancia <= 90)
            if a.nome.startswith("logs/"):
                self.assertTrue(a.tamanho <= 15 and a.importancia <= 25)

    def test_correlacionado_importancia_perto_do_tamanho(self):
        for a in gerar("correlacionado", 500, 1):
            self.assertLessEqual(a.tamanho, 100)
            self.assertLessEqual(abs(a.importancia - a.tamanho), 5)

    def test_perfil_desconhecido(self):
        with self.assertRaises(ValueError):
            gerar("outro", 10, 1)


class TestScript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.saida = Path(self._tmp.name) / "gerados"

    def test_csvs_sao_lidos_de_volta(self):
        codigo, texto = executar("--saida", str(self.saida), "--ns", "20", "200",
                                 "--pastas", "--perfis", "uniforme", "realista")
        self.assertEqual(codigo, 0)
        self.assertEqual(sorted(p.name for p in self.saida.iterdir()),
                         ["realista_20.csv", "realista_200.csv",
                          "uniforme_20.csv", "uniforme_200.csv"])
        self.assertEqual(ler_arquivos_csv(self.saida / "realista_200.csv"),
                         gerar("realista", 200, 2026))

    def test_pasta_tem_os_tamanhos_do_csv(self):
        executar("--saida", str(self.saida), "--ns", "--pastas", "30",
                 "--perfis", "realista", "uniforme", "--esparso")
        for perfil in ("realista", "uniforme"):
            esperado = {a.nome: a.tamanho for a in ler_arquivos_csv(self.saida / f"pasta_{perfil}_30.csv")}
            real = {a.nome: a.tamanho for a in varrer_pasta(self.saida / f"pasta_{perfil}_30", recursivo=True)}
            self.assertEqual(len(real), 30)
            self.assertEqual(real, esperado)

    def test_pasta_existente_nao_e_sobrescrita(self):
        argumentos = ("--saida", str(self.saida), "--ns", "--pastas", "10",
                      "--perfis", "uniforme", "--esparso")
        self.assertEqual(executar(*argumentos)[0], 0)
        marca = self.saida / "pasta_uniforme_10" / "minha_anotacao.txt"
        marca.write_text("não apagar")
        codigo, texto = executar(*argumentos)
        self.assertEqual(codigo, 1)
        self.assertIn("PULOU", texto)
        self.assertTrue(marca.exists())

    @unittest.skipUnless(os.name == "nt", "só vale no Windows")
    def test_limite_de_espaco_no_windows(self):
        codigo, texto = executar("--saida", str(self.saida), "--ns", "--pastas", "100",
                                 "--perfis", "realista", "--limite-gb", "0.001")
        self.assertEqual(codigo, 1)
        self.assertIn("PULOU", texto)

    def test_opcao_esparso_cria_as_mesmas_pastas(self):
        # Fora do Windows a opção não muda nada; no Windows (NTFS) ativa o modo esparso.
        codigo, _ = executar("--saida", str(self.saida), "--ns", "--pastas", "20",
                             "--perfis", "realista", "--esparso")
        self.assertEqual(codigo, 0)
        esperado = {a.nome: a.tamanho for a in gerar("realista", 20, 2026)}
        real = {a.nome: a.tamanho for a in varrer_pasta(self.saida / "pasta_realista_20", recursivo=True)}
        self.assertEqual(real, esperado)

    def test_quantidade_invalida(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            executar("--saida", str(self.saida), "--ns", "0")


if __name__ == "__main__":
    unittest.main()