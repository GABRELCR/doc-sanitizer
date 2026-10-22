# src/anonymizers/anonymizer.py

import uuid
from faker import Faker


class Anonymizer:
    r"""
    Motor responsável pelas estratégias de anonimização, mascaramento, geração sintética 
    e tokenização (pseudonimização reversível) de Dados Sensíveis (PII), dando suporte tanto a 
    entidades estruturadas (RegEx) quanto a entidades não estruturadas de IA/NLP (NER).

    Decisão de Arquitetura (Design Pattern):
    - Implementa uma variação do Strategy Pattern, permitindo alternar dinamicamente entre diferentes 
      métodos de sanitização de dados (ex.: mascaramento com asteriscos, dados sintéticos ou tokenização).
    """
    
    def __init__(self, strategy: str = "mask"):
        """
        Inicializa o motor de anonimização configurando a estratégia padrão e o gerador de dados falsos.

        Args:
            strategy (str): Estratégia de anonimização a ser aplicada ("mask", "faker" ou "tokenize"). 
                            O padrão é "mask".

        Detalhes de Implementação:
        - `self.fake`: Instancia a biblioteca `Faker` configurada para o locale brasileiro (`pt_BR`), 
          garantindo que dados sintéticos gerados obedeçam ao contexto regional.
        """
        self.strategy = strategy
        self.fake = Faker('pt_BR')  # Inicializa o Faker em português (locale pt_BR)

    def _generate_mask(self, text: str) -> str:
        """
        Gera uma máscara textual substituindo cada caractere por asteriscos.

        Args:
            text (str): O texto original da entidade sensível.

        Returns:
            str: String de asteriscos (`*`) com exatamente o mesmo comprimento do texto original, 
                 preservando a volumetria visual e a estrutura tabular do documento.
        """
        return "*" * len(text)

    def _generate_fake(self, entity_type: str) -> str:
        """
        Gera dados sintéticos e realistas baseados na categoria da entidade sensível.

        Args:
            entity_type (str): O tipo da entidade (ex: 'CPF', 'EMAIL', 'PERSON', 'LOCATION').

        Returns:
            str: O dado sintético gerado ou uma tag de fallback estruturada.
        """
        if entity_type == "CPF":
            return self.fake.cpf()
        elif entity_type == "CNPJ":
            return self.fake.cnpj()
        elif entity_type == "EMAIL":
            return self.fake.email()
        elif entity_type == "TELEFONE":
            # Formatação controlada para garantir consistência visual de telefones brasileiros
            return f"({self.fake.random_int(min=11, max=99)}) 9{self.fake.random_int(min=1000, max=9999)}-{self.fake.random_int(min=1000, max=9999)}"
        elif entity_type == "CEP":
            return self.fake.postcode()
        elif entity_type == "PERSON":
            # Gera um nome completo fictício baseado no locale pt_BR
            return self.fake.name()
        elif entity_type == "LOCATION":
            # Tratamento de Sanitização Secundária: Remove quebras de linha e barras para adequação em linha única
            return self.fake.address().replace('\n', ', ').replace('/', '')
            
        # Padrão de Guard Clause / Fallback para tipos de entidades não mapeados
        return "[DADO_OCULTADO]"

    def _generate_token(self) -> str:
        """
        Gera um identificador textual único para pseudonimização reversível.

        Returns:
            str: Um token no formato `TOKEN_XXXXXXXX`.

        Detalhes de Implementação:
        - Utiliza `uuid.uuid4()` para garantir aleatoriedade estatística quase absoluta.
        - Trunca o UUID para 8 caracteres para manter o token curto, legível e prático para planilhas.
        """
        return f"TOKEN_{str(uuid.uuid4())[:8]}"

    def anonymize_text(self, text: str, findings: list) -> tuple:
        r"""
        Substitui de forma segura os dados sensíveis encontrados em um texto de acordo com a estratégia ativa,
        retornando o texto modificado e o dicionário de mapeamento reverso (para o cofre criptográfico).

        Args:
            text (str): O texto original completo onde os achados foram identificados.
            findings (list[dict]): Lista contendo os metadados dos achados ('start', 'end', 'entity_type', 'text').

        Returns:
            tuple[str, dict]: Uma tupla contendo o texto processado e o dicionário de mapeamento (`token -> texto_original`).

        Algoritmo Crítico e Manipulação de Estruturas de Dados:
        1. Ordenação Reversa (Reverse Sorting): Os achados são ordenados do final para o início 
           (`reverse=True` baseado no índice `start`). Isso evita o deslocamento de índices (*offset shift*) 
           durante as substituições sucessivas; caso contrário, alterar o tamanho do texto no início invalidaria 
           as posições dos achados subsequentes.
        2. Mutabilidade de Strings em Python: Como strings são imutáveis no Python, o texto é convertido 
           temporariamente em uma lista de caracteres (`list(text)`), permitindo substituições rápidas 
           por fatiamento (*slice assignment*) em tempo eficiente $O(K)$, e posteriormente reconvertido para string via `"".join()`.
        """
        # Ordena os achados da maior posição para a menor (fim para o início do texto)
        sorted_findings = sorted(findings, key=lambda x: x["start"], reverse=True)
        
        # Converte a string imutável em uma lista mutável de caracteres
        text_list = list(text)
        
        # Dicionário acumulador para registrar o de-para (Token -> Texto Original)
        token_mapping = {}

        # Itera sobre os achados de trás para frente para preservar a integridade dos índices
        for finding in sorted_findings:
            start = finding["start"]
            end = finding["end"]
            entity_type = finding["entity_type"]
            texto_original = finding["text"]

            # Seleciona o método de substituição com base na estratégia configurada
            if self.strategy == "mask":
                replacement = self._generate_mask(texto_original)
            elif self.strategy == "faker":
                replacement = self._generate_fake(entity_type)
            elif self.strategy == "tokenize":
                # Gera o token exclusivo e registra o par no mapeamento reverso
                token = self._generate_token()
                replacement = token
                token_mapping[token] = texto_original
            else:
                replacement = "[DADO_OCULTADO]"

            # Substitui o trecho na lista de caracteres de forma eficiente via slice assignment
            text_list[start:end] = list(replacement)

        # Reconstrói a string final a partir da lista modificada e retorna junto com o dicionário de mapeamento
        return "".join(text_list), token_mapping