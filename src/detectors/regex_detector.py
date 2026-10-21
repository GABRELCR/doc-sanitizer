# src/detectors/regex_detector.py

import re


class RegexDetector:
    """
    Motor de detecção de Dados Pessoais / Dados Sensíveis (PII) baseado em Expressões Regulares (RegEx).

    Decisão de Arquitetura:
    - Atua como um componente isolado de processamento de texto (Engine / Service), desacoplando 
      a lógica de reconhecimento de padrões das camadas de infraestrutura e orquestração.
    """
    
    def __init__(self):
        """
        Inicializa o detector compilando previamente as expressões regulares para otimização de desempenho.

        Detalhes de Desempenho e Arquitetura:
        - `re.compile()`: Pré-compila os padrões RegEx em bytecode no momento da instanciação da classe.
          Isso evita a re-compilação dinâmica a cada chamada do método de detecção, reduzindo drasticamente 
          o overhead de CPU em varreduras massivas de texto.
        - Estrutura de Dados `self.patterns`: Um dicionário mapeando o rótulo da entidade sensível 
          (chave `str`) para seu respectivo objeto de expressão regular compilado (`re.Pattern`).
        """
        self.patterns = {
            "CPF": re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'),
            "CNPJ": re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'),
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "TELEFONE": re.compile(r'(?<!\d)(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}-?\d{4})(?!\d)'),
            "CEP": re.compile(r'\b\d{5}-?\d{3}\b')
        }

    def detect(self, text: str) -> list:
        """
        Varre o texto fornecido em busca de todas as ocorrências de PII configuradas.

        Args:
            text (str): Texto bruto da célula ou documento a ser auditado.

        Returns:
            list[dict]: Uma lista de dicionários contendo os metadados de cada ocorrência encontrada,
                        ordenados sequencialmente pela posição de aparição no texto.

        Algoritmo e Estrutura de Dados:
        - Varredura por Iterador (`finditer`): Utiliza iteradores de avaliação preguiçosa (`lazy evaluation`) 
          para varrer o texto sem carregar todas as correspondências simultaneamente na memória.
        - Ordenação Pós-Processamento: Como múltiplos padrões são testados independentemente, 
          as ocorrências de tipos diferentes podem vir fora de ordem cronológica. O método aplica 
          `findings.sort(key=lambda x: x["start"])` para reorganizá-las com base no índice inicial (`start`).
        """
        findings = []
        
        # Itera sobre cada tipo de entidade e seu respectivo padrão compilado
        for entity_type, pattern in self.patterns.items():
            # `finditer` retorna um iterador de objetos Match, otimizando o consumo de memória em textos longos
            for match in pattern.finditer(text):
                # Constrói o dicionário de representação da ocorrência (DTO implícito)
                findings.append({
                    "entity_type": entity_type,    # Categoria do dado sensível (ex: CPF, EMAIL)
                    "text": match.group(),         # Valor textual exato capturado pela expressão regular
                    "start": match.start(),        # Índice do caractere inicial da correspondência no texto
                    "end": match.end()             # Índice do caractere final da correspondência no texto
                })
                
        # Ordenação estável da lista combinada de achados pelo índice de início no texto original
        findings.sort(key=lambda x: x["start"])
        
        return findings