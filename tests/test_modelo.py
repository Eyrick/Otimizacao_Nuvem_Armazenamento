"""Testes das validações do modelo de dados."""

import os
import sys
import unittest

# Permite executar os testes a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.modelo import Arquivo, Instancia, ModeloError  # noqa: E402


class TestArquivo(unittest.TestCase):
    def test_arquivo_valido(self):
        a = Arquivo("foto.jpg", 5, 45)
        self.assertEqual((a.nome, a.tamanho, a.importancia), ("foto.jpg", 5, 45))
        self.assertAlmostEqual(a.razao, 9.0)

    def test_limites_de_importancia(self):
        Arquivo("a", 1, 1)
        Arquivo("b", 1, 100)
        for valor in (0, 101, -3):
            with self.assertRaises(ModeloError):
                Arquivo("x", 1, valor)

    def test_tamanho_invalido(self):
        for valor in (0, -1, 2.5, "3", True, None):
            with self.assertRaises(ModeloError):
                Arquivo("x", valor, 10)

    def test_importancia_nao_inteira(self):
        for valor in (10.5, "10", True, None):
            with self.assertRaises(ModeloError):
                Arquivo("x", 1, valor)

    def test_nome_vazio(self):
        for nome in ("", "   ", None):
            with self.assertRaises(ModeloError):
                Arquivo(nome, 1, 10)


class TestInstancia(unittest.TestCase):
    def setUp(self):
        self.arquivos = [Arquivo("1", 6, 60), Arquivo("2", 5, 45), Arquivo("3", 5, 45)]

    def test_instancia_valida(self):
        inst = Instancia(self.arquivos, 10)
        self.assertEqual(inst.n, 3)
        self.assertEqual(inst.capacidade, 10)
        self.assertEqual(inst.tamanho_total, 16)
        self.assertEqual(inst.importancia_total, 150)

    def test_arquivos_viram_tupla(self):
        inst = Instancia(self.arquivos, 10)
        self.assertIsInstance(inst.arquivos, tuple)

    def test_capacidade_invalida(self):
        for valor in (0, -5, 10.0, "10", True):
            with self.assertRaises(ModeloError):
                Instancia(self.arquivos, valor)

    def test_sem_arquivos(self):
        with self.assertRaises(ModeloError):
            Instancia([], 10)

    def test_itens_que_nao_sao_arquivo(self):
        with self.assertRaises(ModeloError):
            Instancia([("a", 1, 1)], 10)


if __name__ == "__main__":
    unittest.main()
