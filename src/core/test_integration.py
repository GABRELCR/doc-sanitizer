# src/core/test_integration.py

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
        list[dict]: Lista unificada e não sobreposta de achados, pronta para o anonimizador.

    Algoritmo de Resolução de Conflitos:
    1. Unificação & Ordenação Primária: O(K log K), onde K = total de achados.
       Ordena as janelas de texto pelo índice inicial (`start`) e, em caso de empate, pelo término (`end`).
    2. Algoritmo Guloso de Fusão de Intervalos (Greedy Interval Merging): O(K).
       Percorre os intervalos sequencialmente mantendo um estado no array `merged`.
    3. Regra de Cobertura Máxima (Longest Match Rule):
       Havendo interseção (`current['start'] < last['end']`), o algoritmo prioriza o achado com 
       maior amplitude de caracteres (`end - start`), substituindo o intervalo menor.
    """
    # Combina as duas coleções de achados
    all_findings = regex_findings + nlp_findings
    
    # Ordena primariamente pelo índice de início e secundariamente pelo índice final
    all_findings.sort(key=lambda x: (x['start'], x['end']))
    
    merged = []
    for current in all_findings:
        if not merged:
            merged.append(current)
        else:
            last = merged[-1]
            # Condição de sobreposição: o elemento atual começa antes do término do anterior
            if current['start'] < last['end']:
                # Critério de desempate: mantemos a entidade que possui a maior área de cobertura textual
                if (current['end'] - current['start']) > (last['end'] - last['start']):
                    merged[-1] = current
            else:
                # Intervalos adjacentes ou disjuntos são aceitos diretamente
                merged.append(current)
                
    return merged


def run_pipeline():
    """
    Orquestra a pipeline híbrida avançada de auditoria, unificando inspeção determinística (RegEx) 
    e Inteligência Artificial (NLP/NER) para higienização e persistência de dados sensíveis.

    Arquitetura da Pipeline (Hybrid ETL / AI-Driven Masking):
    1. Ingestão (Extract): Leitura da estrutura da planilha e extração de células textuais.
    2. Detecção RegEx (Fast Path): Busca rápida por padrões estruturados (CPF, CNPJ, E-mail, CEP, Telefone).
    3. Detecção NLP (Slow Path): Inferência por redes neurais/spaCy para entidades não estruturadas (PERSON, LOCATION).
    4. Resolução de Conflitos (Merge): Fusão de janelas de texto sobrepostas via `merge_findings`.
    5. Mutação em Memória (Transform): Substituição por dados sintéticos (`Faker`) e atualização da DOM.
    6. Persistência (Load): Exportação para novo arquivo seguro.
    """
    # Definição dos caminhos para a fonte de dados e o arquivo final sanitizado com IA
    caminho_arquivo = "data/teste.xlsx"
    caminho_saida = "data/teste_sanitizado_com_ia.xlsx" 
    
    print(f"🔍 Iniciando higienização com IA em: {caminho_arquivo}")
    print("⏳ Carregando modelos de IA (isso pode levar alguns segundos)...")
    
    # ------------------------------------------------------------------------------
    # Inicialização do Ecossistema de Módulos (Híbrido: RegEx + NLP + Strategy)
    # ------------------------------------------------------------------------------
    leitor = ExcelReader(caminho_arquivo)
    regex_detector = RegexDetector()
    nlp_detector = NLPDetector()
    anonimizador = Anonymizer(strategy="faker")

    # Ingestão de dados: Extração de todas as células textuais da planilha
    celulas = leitor.read_all_cells()
    total_alteracoes = 0
    
    # ------------------------------------------------------------------------------
    # Processamento e Inspeção Híbrida Célula a Célula
    # ------------------------------------------------------------------------------
    for i, celula in enumerate(celulas):
        texto_original = celula['text']
        
        # Otimização de Performance (Short-Circuit Guard Clause):
        # Descarta células vazias ou textos irrelevantes (< 3 caracteres) para evitar chamadas de IA desnecessárias
        if not texto_original or len(texto_original) < 3:
            continue

        # 1. Execução do Fast Path: Análise determinística por Expressões Regulares (Baixo overhead de CPU)
        achados_regex = regex_detector.detect(texto_original)
        
        # 2. Execução do Slow Path: Processamento de IA / NLP (Alto overhead de GPU/CPU)
        # Otimização Domain-Specific: Ignora a linha 1 (cabeçalhos/headers) para otimizar tempo de execução
        if celula['row'] > 1: 
            achados_nlp = nlp_detector.detect(texto_original)
        else:
            achados_nlp = []

        # 3. Consolidação e Resolução de Conflitos entre RegEx e NLP
        achados_finais = merge_findings(achados_regex, achados_nlp)
        
        # 4. Mutação e Atualização de Célula
        if achados_finais:
            # Substitui os dados identificados pela estratégia Faker
            texto_limpo = anonimizador.anonymize_text(texto_original, achados_finais)
            
            # Atualiza a árvore DOM do openpyxl em memória
            leitor.update_cell(
                sheet_name=celula['sheet'], 
                coordinate=celula['coordinate'], 
                new_value=texto_limpo
            )
            total_alteracoes += 1
            
            # Amostragem defensiva: limita a exibição visual às 5 primeiras células modificadas
            if total_alteracoes <= 5:
                print(f"\n📍 Célula {celula['coordinate']}:")
                print(f"   Original: {texto_original}")
                print(f"   Sanitizado: {texto_limpo}")

    # ------------------------------------------------------------------------------
    # Gravando no Disco o Resultado Sanitizado
    # ------------------------------------------------------------------------------
    leitor.save(caminho_saida)
    
    print(f"\n✅ PROCESSO CONCLUÍDO COM IA!")
    print(f"Total de células higienizadas: {total_alteracoes}")
    print(f"Arquivo seguro gerado em: {caminho_saida}")


# Ponto de entrada padrão para execução do script via CLI (Command Line Interface)
if __name__ == "__main__":
    run_pipeline()