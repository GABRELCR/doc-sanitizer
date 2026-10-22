# src/detectors/nlp_detector.py

import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider


class NLPDetector:
    """
    Motor avançado de detecção de Dados Pessoais / Dados Sensíveis (PII) baseado em Inteligência Artificial,
    combinando o framework de Processamento de Linguagem Natural (NLP) do spaCy com o Microsoft Presidio Analyzer.

    Decisão de Arquitetura (Design Pattern):
    - Atua como um componente especializado em Named Entity Recognition (NER) para dados **não estruturados** 
      (como nomes próprios e localizações), complementando os detectores baseados em regras rígidas (RegEx).
    """
    
    def __init__(self):
        """
        Inicializa e configura o motor de NLP e o ecossistema do Microsoft Presidio para o idioma português.

        Detalhes de Configuração e Desempenho:
        - `configuration`: Dicionário de diretrizes que instrui o Presidio a utilizar o `spacy` como motor de NLP 
          subjacente e o modelo de grande porte em português (`pt_core_news_lg`), oferecendo maior acurácia 
          na identificação de entidades complexas.
        - `NlpEngineProvider`: Padrão de projeto Factory / Provider que desacopla a criação do motor de NLP 
          da inicialização lógica do analisador principal.
        - `AnalyzerEngine`: Núcleo analítico do Presidio responsável por aplicar os reconhecedores de entidades 
          nomeadas (NER) restritos ao idioma português (`supported_languages=["pt"]`).
        """
        # 1. Configura o Presidio para usar o modelo de grande porte do spaCy em português
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}],
        }
        
        # Cria o provedor de NLP através do dicionário de configuração
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        # 2. Inicializa o motor do Presidio com o motor NLP configurado e suporte ao português
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["pt"]
        )

    def detect(self, text: str) -> list:
        """
        Analisa o texto fornecido utilizando Machine Learning / NER para extrair entidades do tipo 
        Nomes de Pessoas (PERSON) e Localizações (LOCATION).

        Args:
            text (str): Texto bruto ou trecho de célula a ser analisado pela IA.

        Returns:
            list[dict]: Uma lista de dicionários estruturados contendo os metadados dos achados, 
                        incluindo tipo de entidade, texto capturado, posições e escore de confiança.

        Algoritmo e Estrutura de Dados:
        - Executa inferência via modelo estatístico do spaCy encapsulado pelo Presidio.
        - Mapeia objetos nativos de resultado (`RecognizerResult`) em uma estrutura customizada de DTO (`dict`) 
          pronta para integração com os demais componentes do pipeline.
        """
        findings = []
        
        # O Presidio executa a análise léxica e estatística, retornando uma lista de ocorrências com escores
        results = self.analyzer.analyze(
            text=text,
            language="pt",
            entities=["PERSON", "LOCATION"]  # Escopo restrito a nomes de pessoas e endereços/localizações
        )
        
        # Converte os resultados brutos do motor de IA em dicionários normalizados para o pipeline
        for res in results:
            findings.append({
                "entity_type": res.entity_type,          # Categoria da entidade (ex: "PERSON" ou "LOCATION")
                "text": text[res.start:res.end],         # Extração direta do trecho textual com base nos índices
                "start": res.start,                      # Índice do caractere inicial no texto original
                "end": res.end,                          # Índice do caractere final no texto original
                "score": res.score                       # Grau de confiança estatística da predição da IA (0.0 a 1.0)
            })
            
        return findings


# --- Bloco de teste rápido (Ponto de Execução Standalone / Smoke Test) ---
if __name__ == "__main__":
    """
    Bloco de execução direta para validação do modelo de IA e testes locais de NER.
    Nota: O carregamento inicial do modelo `pt_core_news_lg` na memória RAM pode levar alguns segundos.
    """
    print("Carregando modelo de IA... (pode demorar alguns segundos)")
    detector = NLPDetector()
    
    # Frase de teste sintética contendo nome e localização
    texto_teste = "O paciente Carlos Oliveira mora na Avenida Paulista em São Paulo e precisa de atendimento."
    
    print("\n--- Texto Original ---")
    print(texto_teste)
    print("\n--- Entidades Encontradas pela IA ---")
    
    # Executa a detecção por NLP no texto de teste
    resultados = detector.detect(texto_teste)
    
    for res in resultados:
        # Filtro de Limiar de Confiança (Threshold Filtering):
        # Desconsidera predições com escore de confiança inferior a 50% (`> 0.5`) para mitigar falsos positivos.
        if res["score"] > 0.5:
            print(f"[{res['entity_type']}] Encontrado: '{res['text']}' (Confiança: {res['score']:.2f})")