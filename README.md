# MyMovieDB

Sistema de gerenciamento de filmes com autenticação completa de usuários.

## Funcionalidades

### Autenticação e Gerenciamento de Usuários
- **Registro de usuários** com validação de email obrigatória
- **Login/Logout** com suporte a "Permanecer conectado"
- **Validação de email** via token JWT enviado por email
- **Reset de senha** com link seguro por email
- **Controle de idade de senha** configurável (aviso quando senha expira)
- **Invalidação automática de sessão** ao trocar senha

### Perfil de Usuário
- **Upload de foto de perfil** com validação de formato e tamanho
- **Crop de imagem** com aspect ratio fixo 2:3 usando Cropper.js
- **Geração automática de avatar** redimensionado
- **Identicons automáticos** gerados baseados no email quando usuário não tem foto
- **Edição de nome** de usuário
- Email imutável após registro (por segurança)

### Segurança
- **Autenticação de Dois Fatores (2FA/TOTP)**:
  - Ativação via QR code para apps autenticadores (Google Authenticator, Microsoft Authenticator, Authy, etc.)
  - Validação de código TOTP durante login
  - Geração de códigos de backup para uso único
  - Desativação segura com confirmação de senha via modal
  - Secret OTP criptografado no banco de dados
- **Validação de complexidade de senha** configurável:
  - Tamanho mínimo
  - Letras maiúsculas/minúsculas
  - Números
  - Símbolos especiais
- **Tokens JWT** com expiração para validação e reset
- **Normalização de emails** para evitar duplicatas
- **Criptografia de dados sensíveis** no banco de dados (segredos 2FA)

### Email
- **Suporte a múltiplos provedores**:
  - Postmark (produção)
  - SMTP genérico (Gmail, etc.)
  - Mock (desenvolvimento/testes)
- **Templates HTML** para emails transacionais

### Tecnologias Utilizadas
- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Migrate
- **Frontend**: Bootstrap 5, Cropper.js (via CDN)
- **Banco de dados**: SQLite (dev) / PostgreSQL (produção)
- **Autenticação**: JWT, Werkzeug password hashing, PyOTP (TOTP/2FA)
- **Criptografia**: Cryptography (Fernet) para dados sensíveis
- **Email**: Postmark API / SMTP
- **Processamento de imagem**: Pillow (PIL)
- **QR Code**: qrcode + PIL para geração de QR codes

---

# Preparando a aplicação

Todas as operações devem ser executadas:

1. Dentro do ambiente virtual da aplicação.
2. No diretório raiz da aplicação (onde está o arquivo `flask_app.py`)

## O Ambiente virtual

Para verificar se o ambiente virtal está ativo, o prompt do terminal deve estar
precedido pelo nome do ambiente virtual, por exemplo: `(.venv) user@machine:~/path/to/project$` no
linux
ou `(.venv) C:\path\to\project>` no Windows.

Se o ambiente virtual não estiver ativo, ative-o com o comando:

- No Linux:
  ```bash
  source .venv/bin/activate
  ```
- No Windows:
  ```bash
  .\.venv\Scripts\activate.ps1
  ```

Se o ambiente virtual ainda não estiver criado (não existir o diretório `.venv`), crie-o com o
comando:

- No Linux:
  ```bash
  python3 -m venv .venv
  ```
- No Windows:
  ```bash
  python -m venv .venv
  ```

No PyCharm, você pode configurar o ambiente virtual nas configurações do projeto, ou na tela
principal do editor na parte mais inferior à direita.

## Configuração da aplicação

Para que a aplicação possa ser executado, é preciso que haja um arquivo JSON de configuração chamado
`config.dev.json` no diretório `instance`. Você pode criar esse arquivo copiando o conteúdo do
arquivo `sampleconfig.json` e ajustando os valores conforme necessário. O arquivo CONFIG.md contém
uma descrição detalhada de cada chave de configuração.

### Parâmetros Obrigatórios

Os seguintes parâmetros **DEVEM** ser configurados para o funcionamento correto da aplicação:

- **`SQLALCHEMY_DATABASE_URI`**: URI de conexão com o banco de dados
    - Exemplo SQLite: `"sqlite:///mymovie.db"`
    - Exemplo PostgreSQL: `"postgresql://user:pass@host/db"`

#### Obrigatórios em Produção
- **`SECRET_KEY`**: Chave secreta para criptografia de tokens JWT e sessões
  - Gere com: `python -c "import os; print(os.urandom(32).hex())"`
  - ⚠️ **NUNCA** comite esta chave no controle de versão

- **`EMAIL_SENDER`**: Email remetente padrão
  - Exemplo: `"noreply@mymoviedb.com"`

### Instalação de Dependências

1. Instale as dependências do projeto:
   ```bash
   pip install -r requirements.txt
   ```

### Geração da chave de criptografia

⚠️ Este passo é obrigatório para o funcionamento da aplicação.

Siga os procedimentos indicados no arquivo SECRETS.md para gerar a chave de criptografia dos dados
sensíveis (segredos 2FA).

## Migração do banco de dados

A migração do banco de dados, agora, está sendo feita pelo Flask-Migrate. Para preparar a aplicação,
você deve seguir os seguintes passos:

1. Configure a variável de ambiente `FLASK_APP` para apontar para o arquivo principal da aplicação:
   ```bash
   export FLASK_APP=app.py  # No Windows use: set FLASK_APP=app.py
   ```
2. Inicialize o repositório de migrações:
   ```bash
   flask db init
   ```
3. Faça as alterações necessárias no arquivo `migrations/env.py` para configurar o `target_metada` e
   carregar os modelos da aplicação (por volta da linha 30):
   ```python
   from app import db
   import app.models # noqa: F401
   target_metadata = db.metadata
   ```
4. Crie a primeira migração:
   ```bash
   flask db migrate -m "Migracao inicial"
   ```
5. Aplique a migração ao banco de dados:
   ```bash
   flask db upgrade
   ```

**Se a sua aplicação já tem migrações criadas (há arquivos no diretório `migrations\versions`), não
execute os passos 2, 3 e 4. Apenas execute o passo 5 para aplicar as migrações ao banco de dados.**

## Execução da aplicação

1. Agora, você pode rodar a aplicação:
   ```bash
   flask run
   ```
