"""Testes do gerador de instâncias sintéticas."""

import os
import sys
import unittest

# Permite executar os testes a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.forca_bruta import forca_bruta  # noqa: E402
from src.gerador import (  # noqa: E402
    gerar_arquivos,
    gerar_cenarios,
    gerar_instancia,
)
from src.guloso import guloso  # noqa: E402
from src.leitura import LeituraError, capacidade_por_fracao  # noqa: E402
from src.programacao_dinamica import programacao_dinamica  # noqa: E402


class TestGerarArquivos(unittest.TestCase):
    def test_quantidade_e_nomes(self):
        arqs = gerar_arquivos(12, semente=1)
        self.assertEqual(len(arqs), 12)
        self.assertEqual(arqs[0].nome, "arquivo_001")
        self.assertEqual(arqs[-1].nome, "arquivo_012")
        self.assertEqual(len({a.nome for a in arqs}), 12)

    def test_nomes_com_largura_maior_para_n_grande(self):
        arqs = gerar_arquivos(10_000, semente=1)
        self.assertEqual(arqs[0].nome, "arquivo_00001")
        self.assertEqual(arqs[-1].nome, "arquivo_10000")
        self.assertEqual(sorted(a.nome for a in arqs), [a.nome for a in arqs])

    def test_mesma_semente_mesmo_resultado(self):
        self.assertEqual(gerar_arquivos(30, semente=7), gerar_arquivos(30, semente=7))

    def test_sementes_diferentes_resultados_diferentes(self):
        self.assertNotEqual(gerar_arquivos(30, semente=7), gerar_arquivos(30, semente=8))

    def test_valores_dentro_dos_intervalos(self):
        arqs = gerar_arquivos(
            500, semente=3, tamanho_min=5, tamanho_max=20,
            importancia_min=30, importancia_max=60,
        )
        self.assertTrue(all(5 <= a.tamanho <= 20 for a in arqs))
        self.assertTrue(all(30 <= a.importancia <= 60 for a in arqs))
        # Com 500 sorteios, os extremos do intervalo devem aparecer.
        self.assertEqual({a.tamanho for a in arqs} & {5, 20}, {5, 20})

    def test_intervalo_de_um_unico_valor(self):
        arqs = gerar_arquivos(5, tamanho_min=7, tamanho_max=7)
        self.assertTrue(all(a.tamanho == 7 for a in arqs))

    def test_parametros_invalidos(self):
        for n in (0, -1, 2.5, "3", True):
            with self.assertRaises(LeituraError):
                gerar_arquivos(n)
        with self.assertRaises(LeituraError):
            gerar_arquivos(5, tamanho_min=0)
        with self.assertRaises(LeituraError):
            gerar_arquivos(5, tamanho_min=10, tamanho_max=5)
        with self.assertRaises(LeituraError):
            gerar_arquivos(5, importancia_max=101)
        with self.assertRaises(LeituraError):
            gerar_arquivos(5, importancia_min=0)
        with self.assertRaises(LeituraError):
            gerar_arquivos(5, importancia_min=60, importancia_max=30)


class TestGerarInstancia(unittest.TestCase):
    def test_capacidade_e_fracao_do_total(self):
        inst = gerar_instancia(20, 0.5, semente=4)
        self.assertEqual(inst.n, 20)
        self.assertEqual(inst.capacidade, capacidade_por_fracao(inst.arquivos, 0.5))
        self.assertLessEqual(inst.capacidade, inst.tamanho_total)

    def test_reproduzivel(self):
        self.assertEqual(gerar_instancia(15, 0.3, semente=9), gerar_instancia(15, 0.3, semente=9))

    def test_repassa_intervalos(self):
        inst = gerar_instancia(50, 0.5, semente=2, tamanho_max=10)
        self.assertTrue(all(a.tamanho <= 10 for a in inst.arquivos))


class TestGerarCenarios(unittest.TestCase):
    NS = (5, 10, 15)
    FRACOES = (0.3, 0.5, 0.7)

    def setUp(self):
        self.cenarios = gerar_cenarios(self.NS, self.FRACOES, repeticoes=2)

    def test_quantidade_e_ordem(self):
        self.assertEqual(len(self.cenarios), 3 * 3 * 2)
        primeiro = self.cenarios[0]
        self.assertEqual((primeiro.n, primeiro.repeticao, primeiro.fracao), (5, 0, 0.3))

    def test_mesmos_arquivos_em_todas_as_fracoes(self):
        # Mesmo n e mesma repetição: o conjunto de arquivos é idêntico.
        por_chave = {}
        for c in self.cenarios:
            por_chave.setdefault((c.n, c.repeticao), []).append(c)
        for grupo in por_chave.values():
            self.assertEqual(len(grupo), 3)
            self.assertEqual(len({c.instancia.arquivos for c in grupo}), 1)
            self.assertEqual(len({c.instancia.capacidade for c in grupo}), 3)

    def test_repeticoes_diferentes_arquivos_diferentes(self):
        r0 = next(c for c in self.cenarios if (c.n, c.repeticao, c.fracao) == (10, 0, 0.5))
        r1 = next(c for c in self.cenarios if (c.n, c.repeticao, c.fracao) == (10, 1, 0.5))
        self.assertNotEqual(r0.instancia.arquivos, r1.instancia.arquivos)

    def test_capacidade_cresce_com_a_fracao(self):
        for n in self.NS:
            caps = [c.instancia.capacidade for c in self.cenarios if c.n == n and c.repeticao == 0]
            self.assertEqual(caps, sorted(caps))

    def test_sementes_unicas_por_conjunto(self):
        sementes = {(c.n, c.repeticao): c.semente for c in self.cenarios}
        self.assertEqual(len(set(sementes.values())), len(sementes))

    def test_reproduzivel_entre_chamadas(self):
        self.assertEqual(self.cenarios, gerar_cenarios(self.NS, self.FRACOES, repeticoes=2))

    def test_semente_base_muda_o_resultado(self):
        outros = gerar_cenarios(self.NS, self.FRACOES, repeticoes=2, semente_base=1)
        self.assertNotEqual(self.cenarios[0].instancia, outros[0].instancia)

    def test_descricao(self):
        c = self.cenarios[0]
        self.assertIn("n=5", c.descricao)
        self.assertIn("30%", c.descricao)
        self.assertIn(f"{c.instancia.capacidade} MB", c.descricao)

    def test_repeticoes_invalidas(self):
        for r in (0, -1, 10_001, 1.5, True):
            with self.assertRaises(LeituraError):
                gerar_cenarios((5,), (0.5,), repeticoes=r)

    def test_fracao_invalida(self):
        with self.assertRaises(LeituraError):
            gerar_cenarios((5,), (0,), repeticoes=1)


class TestAlgoritmosNosCenarios(unittest.TestCase):
    """Os algoritmos devem se comportar nas instâncias dos experimentos."""

    def test_pd_igual_a_forca_bruta_e_guloso_nunca_supera(self):
        cenarios = gerar_cenarios((5, 8, 10, 12), (0.3, 0.5, 0.7), repeticoes=5)
        for c in cenarios:
            fb = forca_bruta(c.instancia)
            pd = programacao_dinamica(c.instancia)
            g = guloso(c.instancia)
            self.assertEqual(fb.importancia_total, pd.importancia_total, msg=c.descricao)
            self.assertLessEqual(g.importancia_total, pd.importancia_total, msg=c.descricao)
            self.assertLessEqual(pd.espaco_usado, c.instancia.capacidade, msg=c.descricao)


if __name__ == "__main__":
    unittest.main()