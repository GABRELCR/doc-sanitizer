# src/anonymizers/anonymizer.py

from faker import Faker


class Anonymizer:
    """
    Motor responsável pelas estratégias de anonimização, mascaramento e substituição de Dados Sensíveis (PII).

    Decisão de Arquitetura (Design Pattern):
    - Implementa uma variação do Strategy Pattern, permitindo alternar dinamicamente entre diferentes 
      métodos de sanitização de dados (ex.: mascaramento com asteriscos ou geração de dados sintéticos).
    """
    
    def __init__(self, strategy: str = "mask"):
        """
        Inicializa o motor de anonimização configurando a estratégia padrão e o gerador de dados falsos.

        Args:
            strategy (str): Estratégia de anonimização a ser aplicada ("mask" ou "faker"). 
                            O padrão é "mask".

        Detalhes de Implementação:
        - `self.fake`: Instancia a biblioteca `Faker` configurada explicitamente para o locale brasileiro (`pt_BR`), 
          garantindo que CPFs, CNPJs, CEPs e e-mails gerados estejam em conformidade com o padrão nacional.
        """
        self.strategy = strategy
        self.fake = Faker('pt_BR')  # Inicializa o Faker em português (locale pt_BR)

    def _generate_mask(self, text: str) -> str:
        """
        Gera uma máscara textual substituindo cada caractere por asteriscos.

        Args:
            text (str): O texto original da entidade sensível.

        Returns:
            str: Uma string de asteriscos (`*`) com exatamente o mesmo comprimento do texto original,
                 preservando a volumetria visual do dado mascarado.
        """
        return "*" * len(text)

    def _generate_fake(self, entity_type: str) -> str:
        """
        Gera dados sintéticos e realistas baseados na categoria da entidade sensível.

        Args:
            entity_type (str): O tipo da entidade (ex: 'CPF', 'EMAIL', 'TELEFONE').

        Returns:
            str: Um dado sintético gerado pela biblioteca Faker ou uma tag de fallback.
        """
        if entity_type == "CPF":
            return self.fake.cpf()
        elif entity_type == "CNPJ":
            return self.fake.cnpj()
        elif entity_type == "EMAIL":
            return self.fake.email()
        elif entity_type == "TELEFONE":
            # Tratamento customizado: garante a padronização visual consistente para telefones brasileiros
            return f"({self.fake.random_int(min=11, max=99)}) 9{self.fake.random_int(min=1000, max=9999)}-{self.fake.random_int(min=1000, max=9999)}"
        elif entity_type == "CEP":
            return self.fake.postcode()
        
        # Padrão de Guard Clause / Fallback para tipos de entidades não mapeados
        return "[DADO_OCULTADO]"

    def anonymize_text(self, text: str, findings: list) -> str:
        """
        Substitui de forma segura os dados sensíveis encontrados em um texto.

        Args:
            text (str): O texto original completo onde os achados foram identificados.
            findings (list[dict]): Lista contendo os metadados dos achados (incluindo 'start', 'end' e 'entity_type').

        Returns:
            str: O texto processado com os dados sensíveis devidamente anonimizados.

        Algoritmo Crítico e Manipulação de Estruturas de Dados:
        1. Ordenação Reversa (Reverse Sorting): Os achados são ordenados do final para o início 
           (`reverse=True` baseado no índice `start`). Isso é um requisito arquitetural obrigatório para evitar
           o *deslocamento de índices* (offset shift); se substituíssemos do começo para o fim, a alteração no tamanho 
           da string invalidaria as posições `start`/`end` dos achados subsequentes.
        2. Mutabilidade de Strings em Python: Como strings são imutáveis no Python, o texto é convertido 
           temporariamente em uma lista de caracteres (`list(text)`), permitindo substituições diretas por fatiamento 
           (slice assignment) em tempo O(K), e posteriormente convertido de volta para string via `"".join()`.
        """
        # Ordena os achados da maior posição para a menor (fim para o início do texto)
        sorted_findings = sorted(findings, key=lambda x: x["start"], reverse=True)
        
        # Converte a string imutável em uma lista mutável de caracteres
        text_list = list(text)

        # Itera sobre os achados de trás para frente para preservar a integridade dos índices
        for finding in sorted_findings:
            start = finding["start"]
            end = finding["end"]
            entity_type = finding["entity_type"]

            # Seleciona o método de substituição com base na estratégia configurada
            if self.strategy == "mask":
                replacement = self._generate_mask(finding["text"])
            elif self.strategy == "faker":
                replacement = self._generate_fake(entity_type)
            else:
                replacement = "[DADO_OCULTADO]"

            # Substitui o trecho na lista de caracteres de forma eficiente via slice assignment
            text_list[start:end] = list(replacement)

        # Reconstrói e retorna a string final a partir da lista modificada
        return "".join(text_list)