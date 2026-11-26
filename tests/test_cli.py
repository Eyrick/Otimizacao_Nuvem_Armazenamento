"""Testes da interface de linha de comando (com entrada simulada)."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

# Permite executar os testes a partir da raiz do projeto.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.cli import LIMITE_FORCA_BRUTA, main  # noqa: E402

# Exemplo da seção 3.6 digitado no menu de cadastro manual (capacidade 10 MB).
EXEMPLO_3_6 = ["1", "3", "1", "6", "60", "2", "5", "45", "3", "5", "45", "10"]


def executar(entradas):
    """Roda o programa com as entradas dadas; devolve (código, texto da saída)."""
    fila = list(entradas)
    saida = []

    def entrada(prompt):
        saida.append(prompt)  # o prompt também aparece na tela
        if not fila:
            raise EOFError
        digitado = fila.pop(0)
        saida.append(digitado + "\n")
        return digitado

    codigo = main(entrada=entrada, saida=lambda texto="": saida.append(texto + "\n"))
    return codigo, "".join(saida)


class TestMenuBasico(unittest.TestCase):
    def test_sair_direto(self):
        codigo, texto = executar(["0"])
        self.assertEqual(codigo, 0)
        self.assertIn("Otimização de Armazenamento em Nuvem", texto)
        self.assertIn("Até logo.", texto)

    def test_opcao_invalida_pergunta_de_novo(self):
        codigo, texto = executar(["9", "abc", "0"])
        self.assertEqual(codigo, 0)
        self.assertEqual(texto.count("Opção inválida."), 2)

    def test_fim_da_entrada_encerra_sem_erro(self):
        codigo, texto = executar([])
        self.assertEqual(codigo, 0)
        self.assertIn("Entrada encerrada.", texto)


class TestCadastroManual(unittest.TestCase):
    def test_programacao_dinamica_no_exemplo(self):
        codigo, texto = executar(EXEMPLO_3_6 + ["2", "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("--- Programação Dinâmica ---", texto)
        self.assertIn("Importância total: 90", texto)
        self.assertIn("Espaço usado: 10 MB de 10 MB (restante: 0 MB)", texto)
        self.assertIn("Arquivos selecionados (2):", texto)

    def test_forca_bruta_e_guloso_no_exemplo(self):
        _, texto = executar(EXEMPLO_3_6 + ["1", "3", "0"])
        self.assertIn("--- Força Bruta ---", texto)
        self.assertIn("Importância total: 90", texto)  # Força Bruta
        self.assertIn("--- Guloso ---", texto)
        self.assertIn("Importância total: 60", texto)  # Guloso erra o exemplo

    def test_comparacao_mostra_perda_do_guloso(self):
        _, texto = executar(EXEMPLO_3_6 + ["4", "0"])
        for nome in ("Força Bruta", "Programação Dinâmica", "Guloso"):
            self.assertRegex(texto, rf"(?m)^{nome}\s")
        linha_guloso = next(l for l in texto.splitlines() if l.startswith("Guloso"))
        self.assertIn("33,33%", linha_guloso)
        linha_pd = next(l for l in texto.splitlines() if l.startswith("Programação"))
        self.assertIn("0,00%", linha_pd)

    def test_entradas_invalidas_sao_reperguntadas(self):
        entradas = [
            "1", "0", "abc", "1",          # quantidade: 0 e "abc" inválidos
            "", "a.txt",                    # nome vazio
            "0", "x", "4",                  # tamanho inválido
            "0", "101", "70",               # importância fora da faixa
            "0", "abc", "150%", "5%",       # capacidade inválida; 5% de 4 MB vira 1 MB
            "0",
        ]
        codigo, texto = executar(entradas)
        self.assertEqual(codigo, 0)
        self.assertIn("O nome não pode ser vazio.", texto)
        self.assertIn("Capacidade inválida", texto)
        self.assertIn("capacidade de 1 MB", texto)

    def test_nome_repetido_e_recusado(self):
        _, texto = executar(["1", "2", "a", "1", "10", "a", "b", "1", "10", "100%", "0"])
        self.assertIn("Já existe um arquivo com esse nome.", texto)
        self.assertIn("2 arquivos", texto)

    def test_porcentagem_com_virgula(self):
        _, texto = executar(["1", "1", "a", "10", "50", "50,5%", "0"])
        # 50,5% de 10 MB = 5,05 -> parte inteira 5
        self.assertIn("capacidade de 5 MB", texto)

    def test_capacidade_maior_que_o_total_e_aceita(self):
        _, texto = executar(["1", "1", "a", "10", "50", "100", "2", "0"])
        self.assertIn("Importância total: 50", texto)
        self.assertIn("restante: 90 MB", texto)


class TestCsv(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_csv_do_repositorio_e_comparacao(self):
        caminho = RAIZ / "data" / "exemplo.csv"
        codigo, texto = executar(["2", str(caminho), "30%", "4", "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("8 arquivos lidos.", texto)
        self.assertIn("capacidade de 976 MB (30,0% do total)", texto)
        # Os três chegam ao mesmo valor nesta instância.
        self.assertEqual(len(re.findall(r"(?m)^(?:Força Bruta|Programação Dinâmica|Guloso)\s+430\s", texto)), 3)

    def test_caminho_com_aspas(self):
        caminho = RAIZ / "data" / "exemplo.csv"
        _, texto = executar(["2", f'"{caminho}"', "30%", "0"])
        self.assertIn("8 arquivos lidos.", texto)

    def test_csv_com_ponto_e_virgula(self):
        p = self.dir / "br.csv"
        p.write_text("nome;tamanho_mb;importancia\nx;4;40\ny;6;60\n", encoding="utf-8")
        _, texto = executar(["2", str(p), "10", "2", "0"])
        self.assertIn("2 arquivos lidos.", texto)
        self.assertIn("Importância total: 100", texto)

    def test_csv_inexistente_volta_ao_menu(self):
        codigo, texto = executar(["2", str(self.dir / "nao_existe.csv"), "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("Não foi possível ler o CSV", texto)
        self.assertEqual(texto.count("Como deseja obter os arquivos?"), 2)

    def test_csv_com_erro_informa_a_linha(self):
        p = self.dir / "ruim.csv"
        p.write_text("nome,tamanho_mb,importancia\nx,1,500\n", encoding="utf-8")
        _, texto = executar(["2", str(p), "0"])
        self.assertIn("Linha 2", texto)


class TestPasta(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        (self.dir / "a.bin").write_bytes(b"x" * (2 * 1024 * 1024))
        (self.dir / "b.bin").write_bytes(b"x")
        (self.dir / "sub").mkdir()
        (self.dir / "sub" / "c.bin").write_bytes(b"x")

    def test_varre_sem_subpastas_e_continua(self):
        codigo, texto = executar(["3", str(self.dir), "n", "", "100%", "2", "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("2 arquivos encontrados", texto)
        self.assertIn("importância 50", texto)
        self.assertIn("Importância total: 100", texto)

    def test_varre_com_subpastas(self):
        _, texto = executar(["3", str(self.dir), "s", "", "100%", "0"])
        self.assertIn("3 arquivos encontrados", texto)
        self.assertIn("sub/c.bin", texto)

    def test_salva_csv_para_editar_e_volta_ao_menu(self):
        destino = self.dir.parent / (self.dir.name + "_editar.csv")
        self.addCleanup(lambda: destino.unlink(missing_ok=True))
        codigo, texto = executar(["3", str(self.dir), "n", str(destino), "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("CSV salvo em", texto)
        self.assertTrue(destino.exists())
        self.assertTrue(destino.read_text(encoding="utf-8").startswith("nome,tamanho_mb,importancia"))

    def test_pasta_inexistente(self):
        _, texto = executar(["3", str(self.dir / "nao_existe"), "n", "0"])
        self.assertIn("Não foi possível ler a pasta", texto)


class TestSintetica(unittest.TestCase):
    def resumo(self, texto):
        return next(l for l in texto.splitlines() if l.startswith("Instância:"))

    def test_gera_e_compara(self):
        codigo, texto = executar(["4", "10", "", "50%", "4", "0"])
        self.assertEqual(codigo, 0)
        self.assertIn("Instância: 10 arquivos", texto)
        self.assertIn("arquivo_001", texto)
        self.assertEqual(len(re.findall(r"(?m)^(?:Força Bruta|Programação Dinâmica|Guloso)\s", texto)), 3)

    def test_mesma_semente_mesma_instancia(self):
        _, t1 = executar(["4", "12", "7", "50%", "0"])
        _, t2 = executar(["4", "12", "7", "50%", "0"])
        _, t3 = executar(["4", "12", "8", "50%", "0"])
        self.assertEqual(self.resumo(t1), self.resumo(t2))
        self.assertNotEqual(self.resumo(t1), self.resumo(t3))

    def test_semente_invalida_e_reperguntada(self):
        _, texto = executar(["4", "5", "abc", "3", "50%", "0"])
        self.assertIn("A semente deve ser um número inteiro.", texto)

    def test_listagem_omitida_para_instancia_grande(self):
        _, texto = executar(["4", "30", "", "50%", "0"])
        self.assertNotIn("arquivo_001", texto)
        self.assertIn("Instância: 30 arquivos", texto)

    def test_opcao_mostrar_arquivos_lista_todos(self):
        _, texto = executar(["4", "30", "", "50%", "5", "0"])
        self.assertIn("arquivo_030", texto)


class TestConfirmacoes(unittest.TestCase):
    def test_forca_bruta_acima_do_limite_pede_confirmacao_e_pode_cancelar(self):
        n = LIMITE_FORCA_BRUTA + 1
        _, texto = executar(["4", str(n), "", "50%", "1", "n", "0"])
        self.assertIn(f"2^{n} combinações", texto)
        self.assertIn("Força Bruta não foi executada.", texto)
        self.assertNotIn("--- Força Bruta ---", texto)

    def test_comparacao_sem_forca_bruta_quando_cancelada(self):
        n = LIMITE_FORCA_BRUTA + 1
        _, texto = executar(["4", str(n), "", "50%", "4", "n", "0"])
        self.assertIn("Força Bruta não foi executada.", texto)
        linhas = [l for l in texto.splitlines() if l.startswith(("Programação", "Guloso"))]
        self.assertEqual(len(linhas), 2)
        # Nenhuma linha da tabela é da Força Bruta (só a mensagem de cancelamento).
        self.assertNotRegex(texto, r"(?m)^Força Bruta\s+\d")

    def test_pd_com_tabela_gigante_pede_confirmacao(self):
        _, texto = executar(["1", "1", "a", "10", "50", "100000000", "2", "n", "0"])
        # n = 1 e C = 100.000.000: a tabela teria (1 + 1) * (C + 1) posições.
        self.assertIn("200.000.002 posições", texto)
        self.assertIn("Programação Dinâmica não foi executada.", texto)

    def test_responder_invalido_na_confirmacao_pergunta_de_novo(self):
        n = LIMITE_FORCA_BRUTA + 1
        _, texto = executar(["4", str(n), "", "50%", "1", "talvez", "n", "0"])
        self.assertIn("Responda com s ou n.", texto)


class TestFluxoCompleto(unittest.TestCase):
    def test_carregar_outra_instancia(self):
        entradas = EXEMPLO_3_6 + ["2", "6"] + ["4", "5", "", "100%", "3", "0"]
        codigo, texto = executar(entradas)
        self.assertEqual(codigo, 0)
        # O menu de algoritmos aparece a cada ação: 2 por instância.
        self.assertEqual(texto.count("O que deseja executar?"), 4)
        # As duas instâncias foram apresentadas, na ordem em que foram carregadas.
        self.assertLess(texto.index("Instância: 3 arquivos"), texto.index("Instância: 5 arquivos"))


if __name__ == "__main__":
    unittest.main()