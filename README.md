
# 🛡️ DocSanitizer

> **Engine 100% Offline de Adequação à LGPD** para higienização e anonimização de Dados Pessoais Sensíveis (PII) em documentos institucionais.

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Air-Gapped](https://img.shields.io/badge/security-air--gapped-success.svg)](https://github.com/SEU_USUARIO/doc-sanitizer)
[![Privacy](https://img.shields.io/badge/LGPD-compliant-orange.svg)](https://www.gov.br/anpd/pt-br)

---

## 🎯 Sobre o Projeto

O **DocSanitizer** é uma ferramenta desktop desenvolvida para clínicas, hospitais, laboratórios e setores administrativos. O sistema automatiza a remoção ou substituição de PII (*Personally Identifiable Information*) em planilhas, relatórios em texto, documentos DOCX e imagens escaneadas. 

Com uma arquitetura **100% offline (*air-gapped*)**, ele garante que nenhum dado sensível trafegue por nuvens públicas, viabilizando o compartilhamento seguro de bases para testes, auditorias ou Business Intelligence em total conformidade com a **LGPD (Lei Geral de Proteção de Dados)**.

---

## ✨ Principais Recursos

* **🔒 Air-Gapped & Seguro:** Execução totalmente local, sem chamadas externas de API ou dependência de internet.
* **📄 Suporte Multiformato:** Processamento de planilhas (`.xlsx`, `.csv`), documentos (`.docx`), textos brutos e imagens (`.png`, `.jpg`, `.pdf` escaneados via OCR).
* **🧠 Detecção Híbrida:** Combinação de Expressões Regulares (Regex) de alta precisão com Processamento de Linguagem Natural (NLP via spaCy e Microsoft Presidio).
* **🔄 Estratégias Flexíveis de Anonimização:**
  * **Máscara:** Ocultação parcial (ex: `***.123.456-**`).
  * **Faker:** Substituição por dados sintéticos realistas e consistentes.
  * **Criptografia Reversível:** Proteção por `AES-GCM` com derivação de chave `Argon2id` (quando autorizado o de-para).
* **⚡ Interface de Linha de Comando (CLI):** Automação simples via terminal para lotes de arquivos.

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.11+ | Base de desenvolvimento |
| **Manipulação de Dados** | Pandas, OpenPyXL, python-docx | Leitura e reescrita de documentos e planilhas |
| **Inteligência Artificial** | spaCy, Microsoft Presidio, Faker | Reconhecimento de Entidades Nomeadas (NER) e geração de dados falsos |
| **Segurança & Criptografia** | Cryptography (AES-GCM), Argon2id | Proteção de dados e segurança de chaves |
| **Visão Computacional** | OpenCV, PyTesseract | Extração de texto em imagens e documentos digitalizados |
| **Empacotamento** | PyInstaller | Geração de executáveis independentes |

---

## 📁 Estrutura do Projeto

```text
doc-sanitizer/
├── src/
│   ├── readers/       # Módulos de leitura e extração de dados por formato
│   ├── detectors/     # Motores de busca e classificação de PII (Regex + NLP)
│   ├── anonymizers/   # Motores de substituição (Máscara, Faker, Criptografia)
│   └── core/          # Orquestrador central do sistema e CLI
├── tests/             # Testes unitários e de integração
├── requirements.txt   # Dependências do projeto
└── README.md

```

---

## 🚀 Como Executar

### Pré-requisitos

* **Python 3.11** ou superior instalado em sua máquina.
* **Tesseract-OCR** instalado no sistema operacional (necessário caso vá processar imagens).

### 1. Clonar o repositório

```bash
git clone https://github.com/GABRELCR/doc-sanitizer
cd doc-sanitizer

```

### 2. Criar e ativar o ambiente virtual

* **Linux / macOS:**
```bash
python -m venv venv
source venv/bin/activate

```


* **Windows (PowerShell / CMD):**
```bash
python -m venv venv
venv\Scripts\activate

```

### 3. Instalar as dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

### 4. Executando o DocSanitizer (Exemplo via CLI)

Para higienizar um arquivo de exemplo apontando o modo de anonimização:

```bash
python -m src.core.cli --input caminho/para/arquivo.xlsx --output caminho/para/saida/ --strategy faker

```

---

## 👨‍💻 Autor

* **Gabriel Corrêa Rebustini**
* **Curso:** Bacharelado em Ciência da Computação — **UNINTER**
* **Atividade:** Projeto de Extensão

---

## 🤝 Como Contribuir

Contribuições são bem-vindas! Sinta-se à vontade para abrir *Issues* ou enviar *Pull Requests* para melhorias de performance, novos detectores de PII ou ampliação de formatos suportados.

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/NovaFeature`)
3. Faça o Commit das alterações (`git commit -m 'Adiciona nova feature'`)
4. Faça o Push para a Branch (`git push origin feature/NovaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE)

```