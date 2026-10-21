# src/core/test_integration.py

import os
from src.readers.excel_reader import ExcelReader
from src.detectors.regex_detector import RegexDetector
from src.anonymizers.anonymizer import Anonymizer


def run_pipeline():
    """
    Orquestra o pipeline completo de Leitura, Detecção, Sanitização e Persistência de Dados Sensíveis (PII).

    Arquitetura da Pipeline (ETL / Masking & Persistence):
    1. Ingestão (Extract): Leitura e mapeamento de células via `ExcelReader`.
    2. Inspeção (Detect): Varredura das células por expressões regulares via `RegexDetector`.
    3. Transformação (Transform): Substituição de dados sensíveis via `Anonymizer`.
    4. Atualização em Memória (Update): Modificação da árvore de dados (DOM do openpyxl) via `update_cell`.
    5. Persistência (Load / Export): Salvamento em um novo arquivo físico via `save`.
    """
    # Definição dos caminhos para arquivos de entrada e saída
    caminho_arquivo = "data/teste.xlsx"
    # Definição de um novo caminho para garantir a imutabilidade da fonte de dados original
    caminho_saida = "data/teste_sanitizado.xlsx" 
    
    print(f"🔍 Iniciando higienização de: {caminho_arquivo}")
    
    # ------------------------------------------------------------------------------
    # Inicialização dos Módulos e Componentes do Sistema
    # ------------------------------------------------------------------------------
    leitor = ExcelReader(caminho_arquivo)
    detector = RegexDetector()
    # Injeção da estratégia "faker" para substituição por dados sintéticos realistas
    anonimizador = Anonymizer(strategy="faker")

    # Ingestão de dados: Extrai a lista de células com dados textuais
    celulas = leitor.read_all_cells()
    # Acumulador para métricas do relatório de auditoria
    total_alteracoes = 0
    
    # ------------------------------------------------------------------------------
    # Ciclo de Inspeção e Mutação em Memória
    #
    # Complexidade de Tempo: O(C * R + C * A)
    # Onde C = número de células, R = regras de regex, A = tempo de anonimização por célula.
    # ------------------------------------------------------------------------------
    for celula in celulas:
        texto_original = celula['text']
        # Identifica ocorrências de PII no texto da célula atual
        achados = detector.detect(texto_original)
        
        # Se houver dados sensíveis identificados
        if achados:
            # Gera o novo texto sanitizado aplicando os dados falsos/máscaras
            texto_limpo = anonimizador.anonymize_text(texto_original, achados)
            
            # Atualiza o valor diretamente na estrutura em memória do workbook (openpyxl)
            leitor.update_cell(
                sheet_name=celula['sheet'], 
                coordinate=celula['coordinate'], 
                new_value=texto_limpo
            )
            total_alteracoes += 1

    # ------------------------------------------------------------------------------
    # Persistência do Novo Arquivo (Disk Write Step)
    # ------------------------------------------------------------------------------
    # Salva a árvore DOM modificada em um novo arquivo sem alterar a planilha original
    leitor.save(caminho_saida)
    
    print(f"\n✅ PROCESSO CONCLUÍDO!")
    print(f"Total de células higienizadas: {total_alteracoes}")
    print(f"Arquivo seguro gerado em: {caminho_saida}")


# Ponto de entrada padrão para execução do script via CLI (Command Line Interface)
if __name__ == "__main__":
    run_pipeline()