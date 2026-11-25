"""Testes da leitura de instâncias (CSV e pasta)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Permite executar os testes a partir da raiz do projeto.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.forca_bruta import forca_bruta  # noqa: E402
from src.leitura import (  # noqa: E402
    BYTES_POR_MB,
    LeituraError,
    bytes_para_mb,
    capacidade_por_fracao,
    carregar_instancia,
    ler_arquivos_csv,
    montar_instancia,
    salvar_csv,
    varrer_pasta,
)
from src.modelo import Arquivo  # noqa: E402
from src.programacao_dinamica import programacao_dinamica  # noqa: E402


class TesteComPastaTemporaria(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def escrever(self, nome, conteudo, binario=False):
        caminho = self.dir / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if binario:
            caminho.write_bytes(conteudo)
        else:
            caminho.write_text(conteudo, encoding="utf-8")
        return caminho


class TestBytesParaMb(unittest.TestCase):
    def test_arredonda_para_cima_com_minimo_de_1(self):
        self.assertEqual(bytes_para_mb(0), 1)
        self.assertEqual(bytes_para_mb(1), 1)
        self.assertEqual(bytes_para_mb(BYTES_POR_MB), 1)
        self.assertEqual(bytes_para_mb(BYTES_POR_MB + 1), 2)
        self.assertEqual(bytes_para_mb(5 * BYTES_POR_MB), 5)

    def test_negativo(self):
        with self.assertRaises(LeituraError):
            bytes_para_mb(-1)


class TestLerCsv(TesteComPastaTemporaria):
    def test_csv_valido(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nfoto.jpg,5,45\ndoc.pdf,3,90\n")
        arqs = ler_arquivos_csv(p)
        self.assertEqual([(a.nome, a.tamanho, a.importancia) for a in arqs],
                         [("foto.jpg", 5, 45), ("doc.pdf", 3, 90)])

    def test_bom_cabecalho_em_maiusculas_e_linhas_em_branco(self):
        p = self.escrever("a.csv", "\ufeffNome,Tamanho_MB,Importancia\n\nx,1,10\n\n,,\ny,2,20\n")
        self.assertEqual([a.nome for a in ler_arquivos_csv(p)], ["x", "y"])

    def test_outro_delimitador(self):
        p = self.escrever("a.csv", "nome;tamanho_mb;importancia\nx;1;10\n")
        self.assertEqual(ler_arquivos_csv(p, delimitador=";")[0].nome, "x")

    def test_cabecalho_errado(self):
        p = self.escrever("a.csv", "arquivo,mb,valor\nx,1,10\n")
        with self.assertRaisesRegex(LeituraError, "Linha 1: cabeçalho"):
            ler_arquivos_csv(p)

    def test_numero_de_colunas(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nx,1\n")
        with self.assertRaisesRegex(LeituraError, "Linha 2: esperadas 3 colunas"):
            ler_arquivos_csv(p)

    def test_valor_nao_inteiro(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nx,5.5,10\n")
        with self.assertRaisesRegex(LeituraError, "Linha 2: 'tamanho_mb' deve ser"):
            ler_arquivos_csv(p)

    def test_valor_fora_do_intervalo_informa_a_linha(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nx,1,10\ny,2,101\n")
        with self.assertRaisesRegex(LeituraError, "Linha 3: Importância inválida"):
            ler_arquivos_csv(p)

    def test_tamanho_zero(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nx,0,10\n")
        with self.assertRaisesRegex(LeituraError, "Linha 2: Tamanho inválido"):
            ler_arquivos_csv(p)

    def test_nome_repetido(self):
        p = self.escrever("a.csv", "nome,tamanho_mb,importancia\nx,1,10\nx,2,20\n")
        with self.assertRaisesRegex(LeituraError, "Linha 3: nome repetido"):
            ler_arquivos_csv(p)

    def test_sem_arquivos(self):
        for conteudo in ("", "nome,tamanho_mb,importancia\n"):
            p = self.escrever("a.csv", conteudo)
            with self.assertRaises(LeituraError):
                ler_arquivos_csv(p)

    def test_ida_e_volta_com_virgula_e_acento_no_nome(self):
        arqs = [Arquivo("relatório, final.pdf", 4, 80), Arquivo("café.txt", 1, 5)]
        p = self.dir / "saida.csv"
        salvar_csv(arqs, p)
        self.assertEqual(ler_arquivos_csv(p), arqs)


class TestCapacidade(unittest.TestCase):
    def setUp(self):
        self.arqs = [Arquivo("a", 60, 10), Arquivo("b", 40, 20)]  # total 100 MB

    def test_fracao(self):
        self.assertEqual(capacidade_por_fracao(self.arqs, 0.3), 30)
        self.assertEqual(capacidade_por_fracao(self.arqs, 0.5), 50)
        self.assertEqual(capacidade_por_fracao(self.arqs, 1), 100)

    def test_minimo_de_1_mb(self):
        self.assertEqual(capacidade_por_fracao([Arquivo("a", 1, 1)], 0.1), 1)

    def test_fracao_invalida(self):
        for f in (0, -0.5, 1.5):
            with self.assertRaises(LeituraError):
                capacidade_por_fracao(self.arqs, f)

    def test_montar_instancia_exige_um_dos_dois(self):
        self.assertEqual(montar_instancia(self.arqs, capacidade=70).capacidade, 70)
        self.assertEqual(montar_instancia(self.arqs, fracao=0.5).capacidade, 50)
        with self.assertRaises(LeituraError):
            montar_instancia(self.arqs)
        with self.assertRaises(LeituraError):
            montar_instancia(self.arqs, capacidade=70, fracao=0.5)

    def test_capacidade_invalida_vira_erro_de_leitura(self):
        with self.assertRaises(LeituraError):
            montar_instancia(self.arqs, capacidade=0)


class TestVarrerPasta(TesteComPastaTemporaria):
    def test_tamanhos_reais_arredondados_para_cima(self):
        self.escrever("pequeno.txt", b"x", binario=True)
        self.escrever("medio.bin", b"x" * (BYTES_POR_MB + 1), binario=True)
        self.escrever("vazio.txt", b"", binario=True)
        arqs = {a.nome: a for a in varrer_pasta(self.dir)}
        self.assertEqual(arqs["pequeno.txt"].tamanho, 1)
        self.assertEqual(arqs["medio.bin"].tamanho, 2)
        self.assertEqual(arqs["vazio.txt"].tamanho, 1)

    def test_importancia_padrao_e_personalizada(self):
        self.escrever("a.txt", b"x", binario=True)
        self.assertEqual(varrer_pasta(self.dir)[0].importancia, 50)
        self.assertEqual(varrer_pasta(self.dir, importancia=70)[0].importancia, 70)

    def test_recursivo_ou_nao(self):
        self.escrever("raiz.txt", b"x", binario=True)
        self.escrever("sub/fundo.txt", b"x", binario=True)
        self.assertEqual([a.nome for a in varrer_pasta(self.dir)], ["raiz.txt"])
        self.assertEqual(
            [a.nome for a in varrer_pasta(self.dir, recursivo=True)],
            ["raiz.txt", "sub/fundo.txt"],
        )

    def test_ordem_alfabetica(self):
        for nome in ("c.txt", "a.txt", "b.txt"):
            self.escrever(nome, b"x", binario=True)
        self.assertEqual([a.nome for a in varrer_pasta(self.dir)], ["a.txt", "b.txt", "c.txt"])

    @unittest.skipUnless(hasattr(os, "symlink"), "sem suporte a links simbólicos")
    def test_ignora_links_simbolicos(self):
        alvo = self.escrever("real.txt", b"x", binario=True)
        try:
            os.symlink(alvo, self.dir / "link.txt")
        except OSError:
            self.skipTest("não foi possível criar link simbólico")
        self.assertEqual([a.nome for a in varrer_pasta(self.dir)], ["real.txt"])

    def test_pasta_inexistente_ou_vazia(self):
        with self.assertRaises(LeituraError):
            varrer_pasta(self.dir / "nao_existe")
        with self.assertRaises(LeituraError):
            varrer_pasta(self.dir)  # vazia

    def test_fluxo_pasta_csv_instancia(self):
        # pasta -> CSV -> (edição da importância) -> instância
        self.escrever("a.txt", b"x" * BYTES_POR_MB, binario=True)
        self.escrever("b.txt", b"x" * (3 * BYTES_POR_MB), binario=True)
        csv_path = self.dir.parent / (self.dir.name + "_saida.csv")
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))
        salvar_csv(varrer_pasta(self.dir), csv_path)
        inst = carregar_instancia(csv_path, capacidade=2)
        self.assertEqual([(a.nome, a.tamanho) for a in inst.arquivos], [("a.txt", 1), ("b.txt", 3)])
        self.assertEqual(inst.capacidade, 2)


class TestExemploDoRepositorio(unittest.TestCase):
    def test_exemplo_csv_resolve_igual_na_forca_bruta_e_na_pd(self):
        inst = carregar_instancia(RAIZ / "data" / "exemplo.csv", fracao=0.3)
        self.assertEqual(inst.n, 8)
        self.assertEqual(inst.tamanho_total, 3255)
        self.assertEqual(inst.capacidade, 976)
        fb = forca_bruta(inst)
        pd = programacao_dinamica(inst)
        self.assertEqual(fb.importancia_total, pd.importancia_total)
        self.assertLessEqual(pd.espaco_usado, 976)


if __name__ == "__main__":
    unittest.main()