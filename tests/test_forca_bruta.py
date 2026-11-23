"""Testes da Força Bruta."""

import itertools
import os
import random
import sys
import unittest

# Permite executar os testes a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.forca_bruta import forca_bruta  # noqa: E402
from src.modelo import Arquivo, Instancia  # noqa: E402


def melhor_valor_por_combinacoes(instancia):
    """Referência independente: usa itertools.combinations."""
    melhor = 0
    for k in range(instancia.n + 1):
        for comb in itertools.combinations(instancia.arquivos, k):
            if sum(a.tamanho for a in comb) <= instancia.capacidade:
                melhor = max(melhor, sum(a.importancia for a in comb))
    return melhor


class TestForcaBruta(unittest.TestCase):
    def test_exemplo_da_secao_3_6(self):
        # Capacidade 10 MB; o ótimo é {2, 3}, com importância 90.
        inst = Instancia(
            [Arquivo("1", 6, 60), Arquivo("2", 5, 45), Arquivo("3", 5, 45)], 10
        )
        r = forca_bruta(inst)
        self.assertEqual(r.importancia_total, 90)
        self.assertEqual([a.nome for a in r.selecionados], ["2", "3"])
        self.assertEqual(r.espaco_usado, 10)
        self.assertEqual(r.espaco_restante, 0)

    def test_todos_cabem(self):
        inst = Instancia([Arquivo("a", 2, 10), Arquivo("b", 3, 20)], 100)
        r = forca_bruta(inst)
        self.assertEqual(r.importancia_total, 30)
        self.assertEqual(len(r.selecionados), 2)

    def test_nenhum_cabe(self):
        inst = Instancia([Arquivo("a", 50, 10), Arquivo("b", 60, 20)], 10)
        r = forca_bruta(inst)
        self.assertEqual(r.importancia_total, 0)
        self.assertEqual(r.selecionados, ())
        self.assertEqual(r.espaco_restante, 10)

    def test_tamanho_igual_a_capacidade(self):
        # A restrição é "<=": usar exatamente C é permitido.
        inst = Instancia([Arquivo("a", 10, 7)], 10)
        r = forca_bruta(inst)
        self.assertEqual(r.importancia_total, 7)

    def test_empate_prefere_menor_espaco(self):
        inst = Instancia([Arquivo("grande", 8, 30), Arquivo("pequeno", 3, 30)], 8)
        r = forca_bruta(inst)
        self.assertEqual(r.importancia_total, 30)
        self.assertEqual([a.nome for a in r.selecionados], ["pequeno"])

    def test_resultado_registra_tempo_e_algoritmo(self):
        inst = Instancia([Arquivo("a", 1, 1)], 1)
        r = forca_bruta(inst)
        self.assertGreaterEqual(r.tempo, 0.0)
        self.assertEqual(r.algoritmo, "Força Bruta")

    def test_contra_referencia_em_instancias_aleatorias(self):
        rng = random.Random(42)
        for _ in range(200):
            n = rng.randint(1, 10)
            arquivos = [
                Arquivo(str(i), rng.randint(1, 20), rng.randint(1, 100))
                for i in range(n)
            ]
            capacidade = rng.randint(1, 80)
            inst = Instancia(arquivos, capacidade)
            r = forca_bruta(inst)
            self.assertEqual(r.importancia_total, melhor_valor_por_combinacoes(inst))
            self.assertLessEqual(r.espaco_usado, capacidade)


if __name__ == "__main__":
    unittest.main()