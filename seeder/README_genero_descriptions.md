# Seeding de Descrições para Gêneros Cinematográficos

Este script atualiza automaticamente as descrições dos gêneros cinematográficos usando IA.

## Configuração

1. **Instalar dependências:**
   ```bash
   cd seeder
   pip install -r requirements.txt
   ```

2. **Configurar chave da OpenAI (opcional):**
   - Obtenha uma chave da API em: https://platform.openai.com/api-keys
   - Edite o arquivo `seeder/.env` e adicione sua chave:
     ```
     OPENAI_API_KEY=sua_chave_aqui
     ```
   - Se não configurar a chave, o script usará descrições de fallback básicas

## Uso

Execute o script a partir do diretório seeder:

```bash
cd seeder
python seed_genero_descriptions.py
```

## Como funciona

1. O script busca todos os gêneros cinematográficos que não possuem descrição
2. Para cada gênero, faz uma consulta à API da OpenAI com o prompt:
   > "Descreva as principais características do gênero cinematográfico {nome_do_genero}, e liste três filmes clássicos desse gênero. Responda em menos de 1000 caracteres em português brasileiro."
3. Atualiza o campo `descricao` do gênero no banco de dados
4. Se a API falhar, usa uma descrição de fallback básica

## Recursos

- **Fallback automático:** Se a API da OpenAI não estiver disponível, o script usa descrições básicas
- **Limite de caracteres:** Garante que as descrições não excedam 1000 caracteres
- **Commit incremental:** Salva o progresso a cada gênero processado
- **Rate limiting:** Inclui pausa entre chamadas para não sobrecarregar a API
- **Filmes clássicos:** Inclui exemplos de filmes representativos do gênero

## Exemplo de saída

```
================================================================================
SEED DE DESCRIÇÕES - GÊNEROS CINEMATOGRÁFICOS
================================================================================

📝 Encontrados 8 gêneros sem descrição:
  • Action
  • Comedy
  • Drama
  • Horror
  • ...

[1/8] Processando: Action
  ✓ Descrição gerada: O gênero de ação caracteriza-se por sequências dinâmicas, perseguições...

[2/8] Processando: Comedy
  ✓ Descrição gerada: A comédia busca entreter através do humor, situações cômicas...

================================================================================
✅ SEED DE DESCRIÇÕES CONCLUÍDO!
================================================================================

Resumo:
  • 6 descrições geradas com IA
  • 2 descrições de fallback
  • 8 gêneros processados
```

## Exemplo de descrição gerada

Para o gênero "Action", a IA pode gerar algo como:

> "O gênero de ação caracteriza-se por sequências dinâmicas, perseguições, lutas e explosões, focando na adrenalina e espetáculo visual. Enfatiza movimento constante e conflitos físicos. Filmes clássicos: Die Hard (1988), Mad Max: Fury Road (2015), Terminator 2 (1991)."