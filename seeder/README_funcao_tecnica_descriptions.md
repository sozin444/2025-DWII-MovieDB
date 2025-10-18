# Seeding de Descrições para Funções Técnicas

Este script atualiza automaticamente as descrições das funções técnicas usando IA.

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
python seed_funcao_tecnica_descriptions.py
```

## Como funciona

1. O script busca todas as funções técnicas que não possuem descrição
2. Para cada função, faz uma consulta à API da OpenAI com o prompt:
   > "Na indústria cinematográfica, o que faz um {nome_da_funcao}? Responda em menos de 1000 caracteres em português brasileiro."
3. Atualiza o campo `descricao` da função técnica no banco de dados
4. Se a API falhar, usa uma descrição de fallback básica

## Recursos

- **Fallback automático:** Se a API da OpenAI não estiver disponível, o script usa descrições básicas
- **Limite de caracteres:** Garante que as descrições não excedam 1000 caracteres
- **Commit incremental:** Salva o progresso a cada função processada
- **Rate limiting:** Inclui pausa entre chamadas para não sobrecarregar a API

## Exemplo de saída

```
================================================================================
SEED DE DESCRIÇÕES - FUNÇÕES TÉCNICAS
================================================================================

📝 Encontradas 15 funções técnicas sem descrição:
  • Director
  • Producer
  • Cinematographer
  • Editor
  • ...

[1/15] Processando: Director
  ✓ Descrição gerada: O diretor é responsável pela visão criativa geral do filme...

[2/15] Processando: Producer
  ✓ Descrição gerada: O produtor supervisiona todos os aspectos da produção...

================================================================================
✅ SEED DE DESCRIÇÕES CONCLUÍDO!
================================================================================

Resumo:
  • 13 descrições geradas com IA
  • 2 descrições de fallback
  • 15 funções processadas
```