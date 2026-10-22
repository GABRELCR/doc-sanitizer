# src/core/cli.py

import argparse
import os
import sys
import json
import re  # Módulo para manipulação de expressões regulares no fluxo de reversão
from getpass import getpass

# Importações dos módulos da arquitetura do DocSanitizer
from src.readers.excel_reader import ExcelReader
from src.detectors.regex_detector import RegexDetector
from src.detectors.nlp_detector import NLPDetector
from src.anonymizers.anonymizer import Anonymizer
from src.security.vault import SecurityVault


def merge_findings(regex_findings: list, nlp_findings: list) -> list:
    r"""
    Consolida as detecções determinísticas (RegEx) e estocásticas (IA/NLP), resolvendo conflitos
    de sobreposição de intervalos (Interval Overlap / Boundary Collision Resolution).

    Args:
        regex_findings (list[dict]): Lista de ocorrências capturadas pelo RegexDetector.
        nlp_findings (list[dict]): Lista de ocorrências capturadas pelo NLPDetector.

    Returns:
        list[dict]: Lista unificada e não sobreposta de achados.

    Algoritmo e Estrutura de Dados:
    - Algoritmo Guloso de Fusão de Intervalos (Greedy Interval Merging) com complexidade $O(K \log K)$,
      onde $K$ é a quantidade total de entidades identificadas.
    - Aplica a Regra de Cobertura Máxima (Longest Match Rule): ao identificar sobreposição 
      (`current['start'] < last['end']`), preserva a entidade com maior extensão de caracteres (`end - start`).
    """
    all_findings = regex_findings + nlp_findings
    # Ordena os intervalos prioritariamente pelo índice de início e secundariamente pelo fim
    all_findings.sort(key=lambda x: (x['start'], x['end']))
    
    merged = []
    for current in all_findings:
        if not merged:
            merged.append(current)
        else:
            last = merged[-1]
            # Verifica intersecção de intervalos entre o elemento atual e o último adicionado
            if current['start'] < last['end']:
                # Substitui pelo intervalo com maior área de cobertura
                if (current['end'] - current['start']) > (last['end'] - last['start']):
                    merged[-1] = current
            else:
                merged.append(current)
    return merged


def processar_arquivo(input_path: str, output_path: str, strategy: str, password: str = None):
    """
    Orquestra a pipeline completa de higienização de planilhas (ETL + Tokenização + Criptografia).

    Args:
        input_path (str): Caminho do arquivo Excel de entrada (.xlsx).
        output_path (str): Caminho de destino da planilha sanitizada.
        strategy (str): Estratégia de substituição ("mask", "faker" ou "tokenize").
        password (str, optional): Senha mestra para criptografia do cofre no modo "tokenize".

    Decisões de Arquitetura e Fluxo de Dados:
    - Processamento Híbrido: Executa o filtro de RegEx em toda a planilha e ativa o modelo de IA (NLP)
      apenas nas linhas de dados (`row > 1`), preservando a linha de cabeçalho.
    - Gestão do Cofre: Se a estratégia for "tokenize", o mapa de tokens (`full_mapping`) é persistido.
      Quando uma senha é fornecida, utiliza o `SecurityVault` para gerar um cofre criptografado AES-GCM (`.enc`).
      Na ausência de senha, aplica fallback registrando o dicionário em JSON puro (`.json`) com aviso de segurança.
    """
    print(f"\n🚀 Iniciando Sanitização...")
    print(f"🛡️  Estratégia: {strategy}\n")
    
    try:
        # Instanciação dos módulos do ecossistema
        leitor = ExcelReader(input_path)
        regex_detector = RegexDetector()
        nlp_detector = NLPDetector()
        anonimizador = Anonymizer(strategy=strategy)
        cofre = SecurityVault()

        # Ingestão de dados da planilha
        celulas = leitor.read_all_cells()
        total_alteracoes = 0
        full_mapping = {}  # Dicionário acumulador global para os tokens do arquivo

        for celula in celulas:
            texto_original = celula['text']
            # Cláusula de Guarda: descarta células vazias, nulas ou irrelevantes (< 3 caracteres)
            if not texto_original or len(texto_original) < 3:
                continue

            # Invocação dos detectores determinístico e preditivo
            achados_regex = regex_detector.detect(texto_original)
            achados_nlp = nlp_detector.detect(texto_original) if celula['row'] > 1 else []
            achados_finais = merge_findings(achados_regex, achados_nlp)
            
            # Sanitização e atualização do modelo em memória se houver PIIs
            if achados_finais:
                texto_limpo, tokens_gerados = anonimizador.anonymize_text(texto_original, achados_finais)
                
                # Mutação direta da célula na estrutura DOM do openpyxl
                leitor.update_cell(celula['sheet'], celula['coordinate'], texto_limpo)
                total_alteracoes += 1
                full_mapping.update(tokens_gerados)  # Agrega os pares token->dado no acumulador

        # Persistência do arquivo higienizado no disco
        leitor.save(output_path)
        
        # Fluxo de Exportação do Cofre de Segurança (apenas para estratégia "tokenize")
        if strategy == "tokenize":
            if not password:
                # Fallback Inseguro: persiste em JSON puro sem encriptação
                print("⚠️ AVISO: Nenhuma senha fornecida. Salvando cofre em JSON puro (inseguro).")
                cofre_path_json = output_path.replace('.xlsx', '_cofre.json')
                with open(cofre_path_json, 'w', encoding='utf-8') as f:
                    json.dump(full_mapping, f, indent=4)
                print(f"📁 Cofre (inseguro) gerado em: {cofre_path_json}")
            else:
                # Modo Criptográfico Seguro: encripta o dicionário com AES-256-GCM + Argon2id
                cofre_path_enc = output_path.replace('.xlsx', '_cofre.enc')
                cofre.save_vault(full_mapping, password, cofre_path_enc)
                print(f"🔒 Cofre criptografado (AES-GCM) gerado em: {cofre_path_enc}")

        print(f"✅ SUCESSO! {total_alteracoes} células higienizadas.")
        print(f"📁 Arquivo seguro: {output_path}\n")

    except Exception as e:
        print(f"❌ ERRO: {e}")


def reverter_arquivo(input_path: str, cofre_path: str, output_path: str, password: str):
    """
    Restaura os dados originais em um arquivo previamente tokenizado utilizando o cofre criptografado.

    Args:
        input_path (str): Caminho do arquivo Excel tokenizado (.xlsx).
        cofre_path (str): Caminho do arquivo do cofre criptografado (.enc).
        output_path (str): Caminho de destino para a planilha original recuperada.
        password (str): Senha mestra para descriptografia do cofre.

    Algoritmo de Reversão de Dados:
    1. Descriptografa o cofre de segurança via `SecurityVault.load_vault`.
    2. Lê a planilha tokenizada e realiza busca via Expressão Regular para encontrar múltiplos 
       tokens no mesmo texto (ex: endereços que contêm rua e cidade tokenizados).
    3. Substitui os tokens encontrados pelos seus valores originais armazenados no dicionário $O(1)$.
    4. Persiste a planilha restaurada em um novo arquivo físico.
    """
    print(f"\n🔓 Iniciando REVERSÃO do arquivo...")
    
    try:
        cofre = SecurityVault()
        try:
            # Descriptografa o cofre e recupera o dicionário de mapeamento
            mapping = cofre.load_vault(password, cofre_path)
            print("✅ Cofre descriptografado com sucesso.")
        except ValueError as e:
            # Falha de autenticação (senha incorreta ou arquivo adulterado)
            print(f"❌ ERRO DE SEGURANÇA: {e}")
            return

        # Leitura da planilha tokenizada
        leitor = ExcelReader(input_path)
        celulas = leitor.read_all_cells()
        total_revertido = 0
        
        # Regex para encontrar qualquer token no meio de um texto maior (ex: TOKEN_1234abcd)
        token_pattern = re.compile(r'TOKEN_[a-f0-9]{8}')
        
        for celula in celulas:
            texto = celula['text']
            
            if "TOKEN_" in texto:
                # Função interna que decide o que substituir
                def substituir_token(match):
                    token_encontrado = match.group(0)
                    # Retorna o dado original se o token existir no cofre, senão mantém o token
                    return mapping.get(token_encontrado, token_encontrado)
                
                # Substitui todos os tokens na célula usando a função de callback
                texto_revertido = token_pattern.sub(substituir_token, texto)
                
                if texto_revertido != texto:  # Se houve mudança real
                    leitor.update_cell(celula['sheet'], celula['coordinate'], texto_revertido)
                    total_revertido += 1

        # Salva o arquivo com os dados restaurados
        leitor.save(output_path)
        print(f"✅ REVERSÃO CONCLUÍDA! {total_revertido} células restauradas.")
        print(f"📁 Arquivo original recuperado em: {output_path}\n")

    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")


# --- MODOS INTERATIVOS (WIZARD GUI VIA CLI) ---

def interativo_sanitizar():
    """
    Assistente interativo passo a passo para o fluxo de sanitização (ocultação de dados).
    """
    print("\n" + "="*50)
    print("🛡️  SANITIZAR ARQUIVO (OCULTAR DADOS)")
    print("="*50)
    
    input_path = input("1. Caminho do arquivo Excel (ex: data/teste.xlsx): ").strip()
    nome_padrao = f"sanitizado_{os.path.basename(input_path)}"
    output_path = input(f"2. Nome do arquivo de saída (Enter para '{nome_padrao}'): ").strip() or nome_padrao

    print("3. Escolha a estratégia:")
    print("   [1] Máscara (Asteriscos)")
    print("   [2] Faker (Dados Falsos)")
    print("   [3] Tokenize (Cofre Reversível)")
    opcao = input("   Digite 1, 2 ou 3 (Enter para 2): ").strip()
    
    strategy = "mask" if opcao == "1" else "faker"
    password = None

    if opcao == "3":
        strategy = "tokenize"
        # Oculta a digitação da senha no terminal via getpass
        password = getpass("   🔑 Digite uma senha forte para o cofre (Enter para salvar sem senha): ").strip()

    processar_arquivo(input_path, output_path, strategy, password)


def interativo_reverter():
    """
    Assistente interativo passo a passo para o fluxo de reversão (restauração de dados).
    """
    print("\n" + "="*50)
    print("🔓 REVERTER ARQUIVO (RESTAURAR DADOS)")
    print("="*50)
    
    input_path = input("1. Caminho do arquivo tokenizado (.xlsx): ").strip()
    cofre_path = input("2. Caminho do arquivo do cofre (.enc): ").strip()
    nome_padrao = f"revertido_{os.path.basename(input_path)}"
    output_path = input(f"3. Nome do arquivo de saída (Enter para '{nome_padrao}'): ").strip() or nome_padrao
    
    # Leitura oculta da senha do cofre
    password = getpass("🔑 Digite a senha do cofre: ").strip()
    
    reverter_arquivo(input_path, cofre_path, output_path, password)


def menu_principal():
    """
    Menu principal de navegação do modo interativo (Wizard).
    """
    print("\n" + "="*50)
    print("🛡️  BEM-VINDO AO DOCSANITIZER 🛡️")
    print("="*50)
    print("[1] Sanitizar um arquivo (Ocultar dados para LGPD)")
    print("[2] Reverter um arquivo (Restaurar dados via Cofre)")
    
    escolha = input("\nEscolha uma opção (1 ou 2): ").strip()
    
    if escolha == "1":
        interativo_sanitizar()
    elif escolha == "2":
        interativo_reverter()
    else:
        print("Opção inválida. Encerrando o programa.")


# --- PONTO DE ENTRADA (MAIN) ---

if __name__ == "__main__":
    """
    Ponto de entrada do script e configuração do manipulador de argumentos (`argparse`).

    Suporta três formas de invocação:
    1. Modo Reversão CLI: `python -m src.core.cli --reverter --input <file> --cofre <enc> --password <pass>`
    2. Modo Sanitização CLI: `python -m src.core.cli --input <file> --strategy <strategy> [--password <pass>]`
    3. Modo Interativo: `python -m src.core.cli` (executa sem argumentos)
    """
    parser = argparse.ArgumentParser(description="DocSanitizer - Anonimizador LGPD Offline")
    
    # Modos de Operação
    parser.add_argument("--reverter", action="store_true", help="Ativa o modo de reversão")
    
    # Caminhos
    parser.add_argument("--input", help="Caminho do arquivo de entrada (.xlsx)")
    parser.add_argument("--output", help="Caminho do arquivo de saída (.xlsx)")
    parser.add_argument("--cofre", help="Caminho do cofre (.enc) - usado apenas na reversão")
    
    # Parâmetros de Sanitização
    parser.add_argument("--strategy", choices=["mask", "faker", "tokenize"], default="faker", help="Estratégia de anonimização")
    parser.add_argument("--password", help="Senha do cofre criptografado")
    
    args = parser.parse_args()

    # 1. Execução do Modo Reversão via linha de comando
    if args.reverter:
        if not args.input or not args.cofre or not args.password:
            print("❌ Para reverter, informe --input, --cofre e --password.")
            sys.exit(1)
        out = args.output or f"revertido_{os.path.basename(args.input)}"
        reverter_arquivo(args.input, args.cofre, out, args.password)
        
    # 2. Execução do Modo Sanitização via linha de comando
    elif args.input:
        out = args.output or f"sanitizado_{os.path.basename(args.input)}"
        processar_arquivo(args.input, out, args.strategy, args.password)
        
    # 3. Execução do Modo Interativo (Wizard via Terminal)
    else:
        menu_principal()