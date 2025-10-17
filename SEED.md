# Guia de Seed do Banco de Dados

Este documento descreve o processo completo para popular o banco de dados do myMoviesDB com dados do TMDB (The Movie Database).

## Pré-requisitos

- Python 3.10 ou superior
- Conta no TMDB com chave de API
- Banco de dados configurado e migrations aplicadas
- Dependências instaladas conforme `seeder/requirements.txt`

## 1. Obter Chave da API do TMDB

### Criar Conta no TMDB

1. Acesse [https://www.themoviedb.org/](https://www.themoviedb.org/)
2. Clique em **Sign Up** (Cadastrar-se) no canto superior direito
3. Preencha o formulário de cadastro com seus dados
4. Confirme seu e-mail através do link enviado

### Solicitar Chave da API

1. Após fazer login, clique no seu avatar no canto superior direito
2. Selecione **Settings** (Configurações)
3. No menu lateral esquerdo, clique em **API**
4. Clique em **Request an API Key** (Solicitar Chave de API)
5. Selecione **Developer** (Desenvolvedor)
6. Preencha o formulário com as informações do seu projeto:
   - **Application Name**: myMoviesDB (ou nome do seu projeto)
   - **Application URL**: http://localhost:5000 (ou URL do seu projeto)
   - **Application Summary**: Descrição breve do projeto
7. Aceite os termos de uso
8. Copie a **API Key (v3 auth)** que será exibida

### Configurar a Chave da API

Defina a variável de ambiente `TMDB_API_KEY` com sua chave:

**Windows (PowerShell):**
```powershell
$Env:TMDB_API_KEY="sua_chave_aqui"
```

**Windows (CMD):**
```cmd
set TMDB_API_KEY=sua_chave_aqui
```

**Linux/macOS:**
```bash
export TMDB_API_KEY="sua_chave_aqui"
```

**Alternativa (arquivo .env):**

Crie um arquivo `.env` na raiz do projeto com:
```
TMDB_API_KEY=sua_chave_aqui
```

## 2. Preparar Lista de Filmes

Edite o arquivo `seeder/movies_id.txt` e adicione os IDs dos filmes que deseja importar, um por linha.

**Exemplo:**
```
550        # Fight Club
680        # Pulp Fiction
13         # Forrest Gump
278        # The Shawshank Redemption
# Comentários podem ser adicionados após #
```

**Como encontrar IDs de filmes:**
1. Acesse [https://www.themoviedb.org/](https://www.themoviedb.org/)
2. Busque pelo filme desejado
3. O ID estará na URL. Exemplo: `https://www.themoviedb.org/movie/550` → ID = 550

## 3. Instalar Dependências

Navegue até o diretório `seeder` e instale as dependências:

```bash
cd seeder
pip install -r requirements.txt
```

## 4. Processo de Seed (3 Etapas)

### Etapa 1: Buscar Dados do TMDB

Execute o script `fetch_data.py` para baixar os dados dos filmes e pessoas do TMDB:

```bash
python fetch_data.py --fetch-persons --language pt-BR
```

**Opções disponíveis:**
- `--fetch-persons`: Busca também os detalhes das pessoas (elenco e equipe técnica)
- `--max-people N`: Limita o número de pessoas a buscar (0 = sem limite)
- `--language LANG`: Define o idioma dos dados (padrão: pt-BR)
- `--movies-file FILE`: Especifica o arquivo com IDs dos filmes (padrão: movies_id.txt)

**Exemplo com limite de pessoas:**
```bash
python fetch_data.py --fetch-persons --max-people 10 --language pt-BR
```

**Saída esperada:**
- Arquivos JSON em `seeder/movies/` com dados dos filmes e créditos
- Arquivos JSON em `seeder/person/` com dados das pessoas

### Etapa 2: Processar Dados

Execute o script `process_data.py` para processar os dados baixados:

```bash
python process_data.py
```

**Opções disponíveis:**
- `--movies-file FILE`: Especifica o arquivo com IDs dos filmes (padrão: movies_id.txt)

**O que este script faz:**
- Extrai e normaliza informações dos filmes
- Extrai e normaliza informações das pessoas
- Cria listas de gêneros únicos
- Cria listas de funções técnicas únicas
- Processa relacionamentos (elenco e equipe técnica)

**Saída esperada:**
- Arquivos processados em `seeder/output/movies/` (filmes, gêneros, funções)
- Arquivos processados em `seeder/output/person/` (pessoas)
- Arquivos de texto: `generos.txt` e `funcoes_tecnicas.txt`

### Etapa 3: Inserir Dados no Banco

Volte para o diretório raiz do projeto e execute o script `seed_data_into_app.py`:

```bash
cd ..
python -m seeder.seed_data_into_app
```

**O que este script faz:**
- Cria gêneros no banco de dados
- Cria funções técnicas no banco de dados
- Cria registros de pessoas (com fotos, se disponíveis)
- Cria registros de filmes (com pôsteres, se disponíveis)
- Estabelece relacionamentos entre filmes, pessoas e funções

**Saída esperada:**
```
================================================================================
SEED DE DADOS - MYMOVIEDB
================================================================================

📝 Criando gêneros...
  ✓ Action
  ✓ Drama
  ...

📝 Criando funções técnicas...
  ✓ Director
  ✓ Producer
  ...

📝 Criando pessoas...
  ✓ Brad Pitt
  ✓ Morgan Freeman
  ...

📝 Criando filmes...
  ✓ Fight Club, 1999
  ✓ Pulp Fiction, 1994
  ...

================================================================================
✅ SEED CONCLUÍDO COM SUCESSO!
================================================================================

Resumo:
  • X gêneros
  • Y funções técnicas
  • Z pessoas
  • W filmes
```

## 5. Verificar Dados no Banco

Após o seed, você pode verificar se os dados foram inseridos corretamente:

```bash
python -m flask shell
```

```python
from app.models.filme import Filme
from app.models.pessoa import Pessoa

# Listar todos os filmes
filmes = Filme.query.all()
for f in filmes:
    print(f"{f.titulo_original} ({f.ano_lancamento})")

# Listar todas as pessoas
pessoas = Pessoa.query.all()
for p in pessoas:
    print(p.nome)
```

## Problemas Comuns

### Erro: "A variável de ambiente TMDB_API_KEY não está definida"

**Solução:** Configure a variável de ambiente conforme descrito na seção 1.

### Erro: "Rate limit exceeded" (Limite de requisições excedido)

**Solução:** O script já implementa delays entre requisições (0.25s a 1s). Se o erro persistir, aguarde alguns minutos antes de tentar novamente.

### Arquivos já existem localmente

Se você executar o script `fetch_data.py` novamente, ele pula filmes e pessoas já baixados. Para forçar um novo download, delete os arquivos em `seeder/movies/` e `seeder/person/`.

### Pessoa não encontrada durante criação de filme

O script cria automaticamente uma pessoa básica (apenas com nome) se ela não for encontrada. Isso pode acontecer se você limitou o número de pessoas na etapa 1 com `--max-people`.

## Estrutura de Diretórios

```
seeder/
├── fetch_data.py              # Script para buscar dados do TMDB
├── process_data.py            # Script para processar dados
├── seed_data_into_app.py      # Script para inserir no banco
├── movies_id.txt              # Lista de IDs de filmes
├── requirements.txt           # Dependências do seeder
├── movies/                    # Dados brutos dos filmes (JSON)
├── person/                    # Dados brutos das pessoas (JSON)
├── images/                    # Cache de imagens baixadas
└── output/
    ├── movies/                # Dados processados dos filmes
    │   ├── *.movie.processed.json
    │   ├── generos.txt
    │   └── funcoes_tecnicas.txt
    └── person/                # Dados processados das pessoas
        └── *.person.processed.json
```

## Notas Importantes

- **Imagens são baixadas em base64**: As imagens (pôsteres e fotos) são baixadas e armazenadas em base64 diretamente no banco de dados
- **Cache de imagens**: As imagens são primeiro baixadas para `seeder/images/` antes de serem inseridas no banco
- **Dados duplicados**: Os scripts verificam se dados já existem antes de inserir para evitar duplicação
- **Idioma**: Por padrão, os dados são buscados em `pt-BR`, mas você pode alterar usando `--language`
- **Commits automáticos**: O script de seed faz commit após cada filme para evitar transações muito grandes

## Recursos Adicionais

- **Documentação da API do TMDB**: [https://developers.themoviedb.org/3](https://developers.themoviedb.org/3)
- **Explorar filmes no TMDB**: [https://www.themoviedb.org/movie](https://www.themoviedb.org/movie)
- **Termos de Uso da API**: [https://www.themoviedb.org/terms-of-use](https://www.themoviedb.org/terms-of-use)
