# src/security/vault.py

import os
import json
import base64
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class SecurityVault:
    """
    Cofre criptografado de alta segurança responsável por armazenar o mapeamento reverso 
    (Token -> Dado Original) de forma segura em disco.

    Decisão de Arquitetura e Criptografia (Defense-in-Depth):
    - Utiliza **Argon2id** (vencedor do Password Hashing Competition) como Função de Derivação de Chave (KDF), 
      sendo resistente a ataques de força bruta baseados em GPU/ASIC devido ao seu custo de memória.
    - Utiliza **AES-GCM** (Galois/Counter Mode), uma cifra simétrica autenticada (AEAD - Authenticated Encryption 
      with Associated Data) que garante tanto o sigilo quanto a integridade dos dados, prevenindo ataques de adulteração.
    """
    
    def __init__(self):
        """
        Inicializa a instância do cofre criptográfico.
        """
        pass

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Deriva uma chave criptográfica segura de 256 bits a partir de uma senha de texto plano 
        utilizando a função de derivação baseada em memória Argon2id.

        Args:
            password (str): Senha mestra fornecida pelo operador.
            salt (bytes): Vetor de salt aleatório criptograficamente seguro para mitigar ataques de tabela arco-íris.

        Returns:
            bytes: Chave simétrica derivada de 32 bytes (256 bits).

        Detalhes dos Parâmetros de Ajuste (Tuning):
        - `memory_cost=65536`: Aloca 64 MB de RAM por computação, dificultando ataques em massa por hardware dedicado.
        - `iterations=3`: Número de passes sequenciais na memória.
        - `lanes=4`: Grau de paralelismo.
        """
        kdf = Argon2id(
            salt=salt,
            length=32,          # Chave de 256 bits para o AES-256
            iterations=3,       # Passes de computação
            lanes=4,            # Graus de paralelismo
            memory_cost=65536,  # Custo de memória configurado para 64MB
        )
        return kdf.derive(password.encode())

    def save_vault(self, mapping: dict, password: str, filepath: str):
        """
        Criptografa o dicionário de mapeamento sensível e o persiste em um arquivo seguro no disco.

        Args:
            mapping (dict): Dicionário contendo o mapeamento reverso de tokens.
            password (str): Senha mestra para encriptação do cofre.
            filepath (str): Caminho do arquivo de saída onde o cofre será armazenado.

        Fluxo de Criptografia (Encryption Pipeline):
        1. Geração de Salt aleatório de 16 bytes via `os.urandom`.
        2. Derivação da chave simétrica via Argon2id.
        3. Inicialização do AES-GCM e geração de um Nonce (Number Used Once) exclusivo de 12 bytes.
        4. Serialização do dicionário para JSON (bytes) e cifragem autenticada.
        5. Codificação dos artefatos criptográficos em Base64 e persistência em formato JSON.
        """
        # 1. Gera um salt aleatório criptograficamente seguro para proteger contra Rainbow Tables
        salt = os.urandom(16)
        
        # 2. Deriva a chave simétrica de 256 bits usando a senha mestra e o salt
        key = self._derive_key(password, salt)
        
        # 3. Configura a cifra AES-GCM e gera um Nonce exclusivo (essencial para evitar reuso de vetor de inicialização)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        
        # Serializa o dicionário de mapeamento para string JSON e depois para codificação UTF-8 (bytes)
        data_to_encrypt = json.dumps(mapping).encode('utf-8')
        
        # Executa a encriptação autenticada (retorna o texto cifrado acrescido da tag de autenticação)
        ciphertext = aesgcm.encrypt(nonce, data_to_encrypt, None)
        
        # 4. Empacota os metadados criptográficos (salt, nonce, ciphertext) codificados em Base64 para armazenamento textual seguro
        vault_data = {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }
        
        # Escreve o cofre estruturado em disco
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(vault_data, f, indent=4)
            
    def load_vault(self, password: str, filepath: str) -> dict:
        """
        Lê o arquivo cifrado do disco, valida a integridade, descriptografa com a senha mestra 
        e reconstrói o dicionário de mapeamento original.

        Args:
            password (str): Senha mestra para decriptografia.
            filepath (str): Caminho do arquivo de cofre armazenado no disco.

        Returns:
            dict: O dicionário de mapeamento original restaurado.

        Raises:
            ValueError: Se a senha estiver incorreta ou se o arquivo do cofre tiver sido corrompido/adulterado.
        """
        # Abre e carrega o pacote JSON do cofre
        with open(filepath, 'r', encoding='utf-8') as f:
            vault_data = json.load(f)
            
        # Decodifica os componentes criptográficos de Base64 para bytes brutos
        salt = base64.b64decode(vault_data["salt"])
        nonce = base64.b64decode(vault_data["nonce"])
        ciphertext = base64.b64decode(vault_data["ciphertext"])
        
        # Deriva a mesma chave utilizando o salt recuperado e a senha fornecida
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        
        # Bloco de Tratamento de Exceções Criptográficas (Tamper Detection)
        try:
            # Tenta descriptografar e validar a tag de autenticação do AES-GCM
            decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
            # Reconverte os bytes decodificados de volta para um dicionário Python
            return json.loads(decrypted_data.decode('utf-8'))
        except InvalidTag:
            # Captura falha de integridade/autenticação (senha errada ou arquivo adulterado)
            raise ValueError("❌ Senha incorreta ou arquivo de cofre corrompido!")