# src/readers/excel_reader.py

import openpyxl
from openpyxl import load_workbook


class ExcelReader:
    """
    Classe utilitária e de infraestrutura responsável por encapsular a leitura, parsing
    e modificação de planilhas no formato Microsoft Excel (.xlsx) através da biblioteca `openpyxl`.

    Decisão de Arquitetura (Design Pattern):
    - Atua no padrão Data Access Object (DAO) / Service / Reader para isolar a dependência 
      externa da biblioteca de terceiros (`openpyxl`) do restante das regras de negócio.
    """

    def __init__(self, filepath: str):
        """
        Inicializa o leitor e carrega a estrutura da planilha em memória.

        Args:
            filepath (str): Caminho absoluto ou relativo para o arquivo `.xlsx`.

        Detalhes de Implementação e Desempenho:
        - `self.filepath`: Armazena a referência textual do caminho do arquivo para rastreamento.
        - `load_workbook(..., data_only=True)`: Parâmetro crucial de arquitetura. Força a leitura 
          apenas dos **valores calculados** gerados pelo Excel em vez das fórmulas puras 
          (ex.: retorna "10" em vez de "=SOMA(A1:A9)"). 
        - Nota de Memória: Por padrão, carrega a árvore de dados completa da planilha (DOM em memória).
        """
        self.filepath = filepath
        
        # Carregamento síncrono do arquivo Excel para o modelo de objetos openpyxl.Workbook
        self.workbook = load_workbook(filename=self.filepath, data_only=True)

    def read_all_cells(self) -> list:
        """
        Executa a varredura e extração de metadados e conteúdo textual de todas as células das abas.

        Returns:
            list[dict]: Uma lista de dicionários, onde cada elemento representa uma célula 
                        com conteúdo textual válido contendo os metadados de localização e valor.

        Algoritmo e Estrutura de Dados:
        - Algoritmo de Varredura Sequencial (Nested Loop Traversal): O(N * M * K), onde:
            N = número de abas (sheets)
            M = número de linhas (rows)
            K = número de colunas (columns)
        - Estrutura de dados de saída: `list[dict]`, proporcionando formato flexível e leve,
          pronto para serialização em formato JSON ou conversão para DataFrames do `pandas`.
        """
        extracted_data = []

        # Itera sobre os nomes das planilhas (Worksheets) disponíveis no objeto Workbook
        for sheet_name in self.workbook.sheetnames:
            # Acesso direto à aba via chave/indexador da classe Workbook
            sheet = self.workbook[sheet_name]

            # `iter_rows()` é um gerador da openpyxl que itera por linha até a última célula com dados (`max_row`).
            # Utilizar iteradores reduz o footprint de memória ao acessar blocos de células.
            for row in sheet.iter_rows():
                for cell in row:
                    # Regra de Filtragem e Validação de Tipos (Guard Clause):
                    # 1. `cell.value is not None`: Garante o descarte imediato de células vazias/nulas.
                    # 2. `isinstance(cell.value, str)`: Restringe a extração apenas para dados do tipo string.
                    #    Atenção: Valores numéricos puros (int, float) ou datas (datetime) serão ignorados por esta condição.
                    if cell.value is not None and isinstance(cell.value, str):
                        # Dicionário de representação do elemento extraído (DTO implícito)
                        extracted_data.append({
                            "sheet": sheet_name,            # Nome da aba/planilha de origem
                            "row": cell.row,                # Índice numérico da linha (base 1)
                            "column": cell.column,          # Índice numérico da coluna (base 1)
                            "coordinate": cell.coordinate, # Coordenada legível no padrão A1 (Ex: 'A1', 'B5')
                            "text": str(cell.value)         # Garantia de coerência do tipo string no payload final
                        })

        return extracted_data

    def update_cell(self, sheet_name: str, coordinate: str, new_value: str):
        """
        Atualiza o valor contido em uma célula específica mantendo os estilos e formatações originais.

        Args:
            sheet_name (str): Nome da aba da planilha onde a célula se encontra.
            coordinate (str): Endereço legível da célula no formato Excel (Ex: 'A1', 'C10').
            new_value (str): Novo valor textual sanitizado a ser atribuído à célula.

        Detalhes de Acesso em Memória:
        - Acesso direto $O(1)$ à aba via indexador `self.workbook[sheet_name]` e à célula via chave `sheet[coordinate]`.
        - Permite escrita mutável diretamente na estrutura DOM em memória do `openpyxl`.
        """
        sheet = self.workbook[sheet_name]
        sheet[coordinate] = new_value

    def save(self, output_filepath: str):
        """
        Persiste a árvore DOM do Workbook modificada em um novo arquivo físico no disco.

        Args:
            output_filepath (str): Caminho de destino para salvar a planilha processada.

        Decisão de Segurança e Imutabilidade (Immutability Pattern):
        - A escrita é direcionada para um novo caminho de arquivo (`output_filepath`) para não 
          sobrescrever o arquivo de origem original (`self.filepath`), garantindo a preservação da fonte da verdade.
        """
        self.workbook.save(output_filepath)


# --- Bloco de teste rápido (Ponto de Entrada para Execução Standalone) ---
if __name__ == "__main__":
    """
    Bloco de execução direta da aplicação/módulo.
    Utilizado para testes de integração local, validações rápidas e prototipagem.
    """
    
    # Definição estática do caminho do arquivo de teste
    caminho_teste = "data/teste.xlsx"

    print(f"Tentando ler o arquivo: {caminho_teste}")

    # Estrutura de Tratamento de Exceções (Error Handling Block)
    # Garante o manuseio gracioso de erros comuns de I/O e execução sem interrupção do processo abruptamente.
    try:
        # Instanciação da classe de leitura
        leitor = ExcelReader(caminho_teste)
        
        # Invocação do processo de extração de dados
        celulas = leitor.read_all_cells()

        print(f"Total de células de texto encontradas: {len(celulas)}\n")

        # Fatiamento da lista (Slicing - `celulas[:5]`): 
        # Prática defensiva de log que evita poluição do stdout ao limitar a amostragem aos 5 primeiros registros.
        for celula in celulas[:5]:
            print(f"Planilha: {celula['sheet']} | Célula: {celula['coordinate']} | Texto: {celula['text']}")

    except FileNotFoundError:
        # Captura específica para falhas na localização do arquivo no caminho relativo/absoluto informado
        print("Erro: Crie um arquivo 'teste.xlsx' dentro da pasta 'data' para testar o leitor.")
    except Exception as e:
        # Captura genérica (Catch-all) para lidar com exceções inesperadas (ex.: arquivo corrompido, erro de permissão ou falta da lib `openpyxl`)
        print(f"Ocorreu um erro: {e}")