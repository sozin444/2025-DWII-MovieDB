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
arquivo `config.sample.json` e ajustando os valores conforme necessário.

1. Instale as dependências do projeto:
   ```bash
   pip install -r requirements.txt
   ```

## Execução da aplicação

1. Agora, você pode rodar a aplicação:
   ```bash
   flask run
   ```
