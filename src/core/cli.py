# src/core/cli.py

import argparse
import os
import sys

# Importações dos módulos do ecossistema do DocSanitizer
from src.readers.excel_reader import ExcelReader
from src.detectors.regex_detector import RegexDetector
from src.detectors.nlp_detector import NLPDetector
from src.anonymizers.anonymizer import Anonymizer


def merge_findings(regex_findings: list, nlp_findings: list) -> list:
    """
    Consolida as detecções determinísticas (RegEx) e estocásticas (IA/NLP), resolvendo conflitos 
    de sobreposição de intervalos (Interval Overlap / Boundary Collision Resolution).

    Args:
        regex_findings (list[dict]): Lista de ocorrências capturadas pelo RegexDetector.
        nlp_findings (list[dict]): Lista de ocorrências capturadas pelo NLPDetector.

    Returns:
        list[dict]: Lista unificada e não sobreposta de achados.

    Algoritmo de Resolução de Conflitos:
    - Ordenação Primária: $O(K \log K)$, onde $K$ é o total de achados. Ordena os intervalos por início (`start`) e fim (`end`).
    - Algoritmo Guloso de Fusão (Greedy Interval Merging): Percorre a lista mantendo a maior cobertura textual 
      (`end - start`) ao identificar intersecções (`current['start'] < last['end']`).
    """
    all_findings = regex_findings + nlp_findings
    all_findings.sort(key=lambda x: (x['start'], x['end']))
    
    merged = []
    for current in all_findings:
        if not merged:
            merged.append(current)
        else:
            last = merged[-1]
            # Detecta intersecção entre o intervalo atual e o último adicionado
            if current['start'] < last['end']:
                # Regra de Cobertura Máxima (Longest Match Rule)
                if (current['end'] - current['start']) > (last['end'] - last['start']):
                    merged[-1] = current
            else:
                merged.append(current)
    return merged


def processar_arquivo(input_path: str, output_path: str, strategy: str):
    """
    Orquestrador principal responsável por executar o pipeline de higienização LGPD sobre um arquivo.

    Args:
        input_path (str): Caminho para o arquivo Excel de entrada (.xlsx).
        output_path (str): Caminho de destino para salvar a planilha sanitizada.
        strategy (str): Estratégia de substituição ("mask" para asteriscos ou "faker" para dados sintéticos).

    Arquitetura de Processamento e Resiliência:
    - Encapsula a execução em um bloco `try-except` para tratamento gracioso de exceções de I/O e execução.
    - Aplica o Fast Path (RegEx) em todas as células e o Slow Path (NLP/NER) apenas nas células de dados (`row > 1`).
    - Atualiza a árvore DOM em memória e persiste em um novo arquivo físico, preservando a fonte de dados original.
    """
    print(f"\n🚀 Iniciando DocSanitizer...")
    print(f"📂 Arquivo de Entrada: {input_path}")
    print(f"💾 Arquivo de Saída:   {output_path}")
    print(f"🛡️  Estratégia:         {strategy}")
    print("⏳ Processando... (Por favor, aguarde)\n")

    try:
        # Inicialização dos componentes de infraestrutura, detecção e transformação
        leitor = ExcelReader(input_path)
        regex_detector = RegexDetector()
        nlp_detector = NLPDetector()
        anonimizador = Anonymizer(strategy=strategy)

        # Ingestão do conteúdo das células
        celulas = leitor.read_all_cells()
        total_alteracoes = 0
        
        for celula in celulas:
            texto_original = celula['text']
            
            # Guard Clause: Otimização para ignorar células nulas, vazias ou irrelevantes (< 3 caracteres)
            if not texto_original or len(texto_original) < 3:
                continue

            # 1. Inspeção por Expressões Regulares (Rápida)
            achados_regex = regex_detector.detect(texto_original)
            
            # 2. Inspeção por IA / NLP (Pula o cabeçalho na linha 1)
            if celula['row'] > 1: 
                achados_nlp = nlp_detector.detect(texto_original)
            else:
                achados_nlp = []

            # 3. Consolidação e Resolução de Conflitos
            achados_finais = merge_findings(achados_regex, achados_nlp)
            
            # 4. Sanitização e Atualização em Memória
            if achados_finais:
                texto_limpo = anonimizador.anonymize_text(texto_original, achados_finais)
                leitor.update_cell(celula['sheet'], celula['coordinate'], texto_limpo)
                total_alteracoes += 1

        # Persistência da planilha sanitizada em disco
        leitor.save(output_path)
        print(f"✅ SUCESSO! {total_alteracoes} células foram higienizadas.")
        print(f"📁 O arquivo seguro está em: {output_path}\n")

    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo '{input_path}' não foi encontrado.")
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")


def modo_interativo():
    """
    Interface de Usuário em Modo Wizard / Interativo via Terminal (REPL-like).

    Decisão de Design / Usabilidade:
    - Provê um fluxo passo a passo amigável orientado a prompts para usuários sem conhecimento 
      de linha de comando (CLI flags), aplicando valores padrão defensivos (*defaults*) para facilitar o uso.
    """
    print("\n" + "="*50)
    print("🛡️  BEM-VINDO AO DOCSANITIZER 🛡️")
    print("="*50)
    
    # Solicita o arquivo de entrada
    input_path = input("1. Digite o caminho do arquivo Excel (ex: data/teste.xlsx): ").strip()
    
    # Define e sugere um nome de saída padrão dinâmico baseado no arquivo de origem
    nome_padrao = f"sanitizado_{os.path.basename(input_path)}"
    output_path = input(f"2. Digite o nome do arquivo de saída (ou aperte Enter para '{nome_padrao}'): ").strip()
    if not output_path:
        output_path = nome_padrao

    # Seleção de estratégia de anonimização
    print("3. Escolha a estratégia de anonimização:")
    print("   [1] Máscara (Asteriscos: ***.***)")
    print("   [2] Faker (Dados falsos: Carlos, Joana, etc.)")
    opcao = input("   Digite 1 ou 2 (Enter para 2): ").strip()
    
    strategy = "mask" if opcao == "1" else "faker"
    
    # Invocação do orquestrador
    processar_arquivo(input_path, output_path, strategy)


# Ponto de entrada CLI (Command Line Interface Entry Point)
if __name__ == "__main__":
    """
    Gerenciamento de Argumentos de Linha de Comando (`argparse`).

    Decisão de Arquitetura (Dual Execution Mode):
    - Permite chamada não interativa para integração em pipelines e automações (ex: CI/CD, Scripts Bash) 
      ao fornecer a flag `--input`.
    - Ativa automaticamente o `modo_interativo()` se executado sem parâmetros, oferecendo uma interface amigável.
    """
    parser = argparse.ArgumentParser(description="DocSanitizer - Anonimizador LGPD Offline")
    parser.add_argument("--input", help="Caminho do arquivo de entrada (.xlsx)")
    parser.add_argument("--output", help="Caminho do arquivo de saída (.xlsx)")
    parser.add_argument("--strategy", choices=["mask", "faker"], default="faker", help="Estratégia de anonimização")
    
    args = parser.parse_args()

    # Modo Automatizado / Modifiers via flags de linha de comando
    if args.input:
        output_final = args.output if args.output else f"sanitizado_{os.path.basename(args.input)}"
        processar_arquivo(args.input, output_final, args.strategy)
    
    # Modo Interativo / Wizard para execução direta sem argumentos
    else:
        modo_interativo()