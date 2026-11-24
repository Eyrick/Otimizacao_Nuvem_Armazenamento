"""Testes da Programação Dinâmica e comparação cruzada com a Força Bruta."""

import os
import random
import sys
import unittest

# Permite executar os testes a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.forca_bruta import forca_bruta  # noqa: E402
from src.modelo import Arquivo, Instancia  # noqa: E402
from src.programacao_dinamica import (  # noqa: E402
    programacao_dinamica,
    valor_otimo_pd,
)


def instancia_aleatoria(rng, n_max=12, tamanho_max=25, capacidade_max=100):
    n = rng.randint(1, n_max)
    arquivos = [
        Arquivo(str(i), rng.randint(1, tamanho_max), rng.randint(1, 100))
        for i in range(n)
    ]
    return Instancia(arquivos, rng.randint(1, capacidade_max))


class TestProgramacaoDinamica(unittest.TestCase):
    def test_exemplo_da_secao_3_6(self):
        # Capacidade 10 MB; o ótimo é {2, 3}, com importância 90.
        inst = Instancia(
            [Arquivo("1", 6, 60), Arquivo("2", 5, 45), Arquivo("3", 5, 45)], 10
        )
        r = programacao_dinamica(inst)
        self.assertEqual(r.importancia_total, 90)
        self.assertEqual([a.nome for a in r.selecionados], ["2", "3"])
        self.assertEqual(r.espaco_usado, 10)
        self.assertEqual(r.espaco_restante, 0)
        self.assertEqual(valor_otimo_pd(inst), 90)

    def test_todos_cabem(self):
        inst = Instancia([Arquivo("a", 2, 10), Arquivo("b", 3, 20)], 100)
        r = programacao_dinamica(inst)
        self.assertEqual(r.importancia_total, 30)
        self.assertEqual(len(r.selecionados), 2)
        self.assertEqual(valor_otimo_pd(inst), 30)

    def test_nenhum_cabe(self):
        inst = Instancia([Arquivo("a", 50, 10), Arquivo("b", 60, 20)], 10)
        r = programacao_dinamica(inst)
        self.assertEqual(r.importancia_total, 0)
        self.assertEqual(r.selecionados, ())
        self.assertEqual(valor_otimo_pd(inst), 0)

    def test_tamanho_igual_a_capacidade(self):
        # A restrição é "<=": usar exatamente C é permitido.
        inst = Instancia([Arquivo("a", 10, 7)], 10)
        self.assertEqual(programacao_dinamica(inst).importancia_total, 7)
        self.assertEqual(valor_otimo_pd(inst), 7)

    def test_arquivo_nao_e_usado_duas_vezes(self):
        # Um único arquivo de 3 MB e capacidade 9: a versão com vetor não
        # pode contá-lo mais de uma vez (isso seria a mochila ilimitada).
        inst = Instancia([Arquivo("a", 3, 10)], 9)
        self.assertEqual(valor_otimo_pd(inst), 10)
        self.assertEqual(programacao_dinamica(inst).importancia_total, 10)

    def test_resultado_registra_tempo_e_algoritmo(self):
        inst = Instancia([Arquivo("a", 1, 1)], 1)
        r = programacao_dinamica(inst)
        self.assertGreaterEqual(r.tempo, 0.0)
        self.assertEqual(r.algoritmo, "Programação Dinâmica")

    def test_selecionados_mantem_ordem_original(self):
        inst = Instancia(
            [Arquivo("a", 1, 10), Arquivo("b", 1, 20), Arquivo("c", 1, 30)], 3
        )
        r = programacao_dinamica(inst)
        self.assertEqual([a.nome for a in r.selecionados], ["a", "b", "c"])


class TestComparacaoCruzada(unittest.TestCase):
    """A PD deve igualar a Força Bruta, que é correta por construção."""

    def test_valor_igual_a_forca_bruta(self):
        rng = random.Random(2026)
        for _ in range(500):
            inst = instancia_aleatoria(rng)
            fb = forca_bruta(inst)
            pd = programacao_dinamica(inst)
            self.assertEqual(
                pd.importancia_total, fb.importancia_total, msg=repr(inst)
            )
            self.assertEqual(valor_otimo_pd(inst), fb.importancia_total, msg=repr(inst))

    def test_solucao_da_pd_e_consistente(self):
        # Os arquivos devolvidos precisam somar exatamente o valor informado
        # e respeitar a capacidade, sem repetir nenhum arquivo.
        rng = random.Random(99)
        for _ in range(300):
            inst = instancia_aleatoria(rng, n_max=15, tamanho_max=30, capacidade_max=150)
            r = programacao_dinamica(inst)
            self.assertEqual(
                r.importancia_total, sum(a.importancia for a in r.selecionados)
            )
            self.assertEqual(r.espaco_usado, sum(a.tamanho for a in r.selecionados))
            self.assertLessEqual(r.espaco_usado, inst.capacidade)
            nomes = [a.nome for a in r.selecionados]
            self.assertEqual(len(nomes), len(set(nomes)))

    def test_capacidades_variadas_na_mesma_instancia(self):
        # Mesmo conjunto de arquivos, várias capacidades: 30%, 50% e 70%
        # do tamanho total, como previsto na metodologia.
        rng = random.Random(5)
        arquivos = [Arquivo(str(i), rng.randint(1, 30), rng.randint(1, 100)) for i in range(12)]
        total = sum(a.tamanho for a in arquivos)
        for fracao in (0.3, 0.5, 0.7):
            inst = Instancia(arquivos, max(1, int(total * fracao)))
            self.assertEqual(
                programacao_dinamica(inst).importancia_total,
                forca_bruta(inst).importancia_total,
            )


if __name__ == "__main__":
    unittest.main()