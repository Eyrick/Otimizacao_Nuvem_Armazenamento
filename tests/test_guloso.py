"""Testes do algoritmo Guloso."""

import os
import random
import sys
import unittest

# Permite executar os testes a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.guloso import guloso  # noqa: E402
from src.modelo import Arquivo, Instancia  # noqa: E402
from src.programacao_dinamica import programacao_dinamica  # noqa: E402


class TestGuloso(unittest.TestCase):
    def test_falha_no_exemplo_da_secao_3_6(self):
        # O guloso escolhe o arquivo 1 (razão 10,0) e obtém 60; o ótimo é 90.
        inst = Instancia(
            [Arquivo("1", 6, 60), Arquivo("2", 5, 45), Arquivo("3", 5, 45)], 10
        )
        r = guloso(inst)
        self.assertEqual(r.importancia_total, 60)
        self.assertEqual([a.nome for a in r.selecionados], ["1"])
        self.assertEqual(r.espaco_usado, 6)
        self.assertEqual(r.espaco_restante, 4)
        # Confirma que o ótimo é de fato maior (gap de 1/3).
        self.assertEqual(programacao_dinamica(inst).importancia_total, 90)

    def test_acerta_quando_o_criterio_basta(self):
        # Todos cabem: o guloso e o ótimo coincidem.
        inst = Instancia([Arquivo("a", 2, 10), Arquivo("b", 3, 20)], 100)
        r = guloso(inst)
        self.assertEqual(r.importancia_total, 30)
        self.assertEqual(len(r.selecionados), 2)

    def test_nenhum_cabe(self):
        inst = Instancia([Arquivo("a", 50, 10), Arquivo("b", 60, 20)], 10)
        r = guloso(inst)
        self.assertEqual(r.importancia_total, 0)
        self.assertEqual(r.selecionados, ())

    def test_continua_depois_de_um_arquivo_que_nao_cabe(self):
        # O arquivo de maior razão não cabe; o guloso deve seguir adiante
        # e ainda aproveitar os seguintes.
        inst = Instancia(
            [Arquivo("grande", 20, 100), Arquivo("p1", 3, 6), Arquivo("p2", 4, 8)],
            8,
        )
        r = guloso(inst)
        self.assertEqual([a.nome for a in r.selecionados], ["p1", "p2"])
        self.assertEqual(r.importancia_total, 14)

    def test_selecionados_mantem_ordem_original(self):
        # Razões crescentes: o guloso visita c, b, a, mas a saída segue a
        # ordem da instância.
        inst = Instancia(
            [Arquivo("a", 1, 10), Arquivo("b", 1, 20), Arquivo("c", 1, 30)], 3
        )
        r = guloso(inst)
        self.assertEqual([a.nome for a in r.selecionados], ["a", "b", "c"])

    def test_resultado_deterministico_em_empate_de_razao(self):
        # Razões iguais (10): prefere a maior importância, depois o menor índice.
        inst = Instancia(
            [Arquivo("x", 1, 10), Arquivo("y", 2, 20), Arquivo("z", 1, 10)], 2
        )
        primeiro = guloso(inst)
        segundo = guloso(inst)
        self.assertEqual(
            [a.nome for a in primeiro.selecionados],
            [a.nome for a in segundo.selecionados],
        )
        self.assertEqual([a.nome for a in primeiro.selecionados], ["y"])

    def test_resultado_registra_tempo_e_algoritmo(self):
        inst = Instancia([Arquivo("a", 1, 1)], 1)
        r = guloso(inst)
        self.assertGreaterEqual(r.tempo, 0.0)
        self.assertEqual(r.algoritmo, "Guloso")


class TestGulosoContraOtimo(unittest.TestCase):
    """O guloso é sempre viável e nunca supera o ótimo da PD."""

    def test_nunca_supera_o_otimo_e_respeita_a_capacidade(self):
        rng = random.Random(11)
        piores = 0
        for _ in range(500):
            n = rng.randint(1, 15)
            arquivos = [
                Arquivo(str(i), rng.randint(1, 30), rng.randint(1, 100))
                for i in range(n)
            ]
            inst = Instancia(arquivos, rng.randint(1, 150))
            g = guloso(inst)
            otimo = programacao_dinamica(inst).importancia_total
            self.assertLessEqual(g.importancia_total, otimo, msg=repr(inst))
            self.assertLessEqual(g.espaco_usado, inst.capacidade)
            if g.importancia_total < otimo:
                piores += 1
        # Em instâncias aleatórias o guloso erra algumas vezes: se nunca
        # errasse, a comparação de qualidade dos experimentos não faria sentido.
        self.assertGreater(piores, 0)


if __name__ == "__main__":
    unittest.main()