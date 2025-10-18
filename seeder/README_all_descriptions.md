# Seeding Completo de Descrições

Este script unificado atualiza automaticamente as descrições de **funções técnicas** e **gêneros cinematográficos** usando IA.

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

### Executar tudo (padrão)
```bash
cd seeder
python seed_all_descriptions.py
```

### Opções específicas
```bash
# Apenas funções técnicas
python seed_all_descriptions.py --funcoes

# Apenas gêneros cinematográficos
python seed_all_descriptions.py --generos

# Forçar atualização de TODAS as descrições (mesmo as que já existem)
python seed_all_descriptions.py --force

# Combinar opções
python seed_all_descriptions.py --funcoes --force
```

## Como funciona

### Para Funções Técnicas
- **Prompt:** "Na indústria cinematográfica, o que faz um {nome_da_funcao}? Responda em menos de 1000 caracteres em português brasileiro."
- **Fallback:** "Profissional responsável pela função de {nome} na produção cinematográfica."

### Para Gêneros Cinematográficos
- **Prompt:** "Descreva as principais características do gênero cinematográfico {nome_do_genero}, e liste três filmes clássicos desse gênero. Responda em menos de 1000 caracteres em português brasileiro."
- **Fallback:** "Gênero cinematográfico {nome} com características e elementos específicos que o distinguem de outros gêneros."

## Recursos

- **Processamento inteligente:** Por padrão, só processa itens sem descrição
- **Modo força:** Atualiza todas as descrições, mesmo as existentes
- **Processamento seletivo:** Pode processar apenas funções ou apenas gêneros
- **Fallback automático:** Funciona mesmo sem OpenAI API key
- **Rate limiting:** Pausas entre chamadas para respeitar limites da API
- **Commit incremental:** Salva progresso a cada item processado
- **Tratamento de erros:** Continua processando mesmo se alguns itens falharem

## Scripts individuais

Se preferir executar separadamente:

- `seed_funcao_tecnica_descriptions.py` - Apenas funções técnicas
- `seed_genero_descriptions.py` - Apenas gêneros cinematográficos

## Exemplo de saída

```
================================================================================
SEED DE DESCRIÇÕES - COMPLETO
================================================================================

📝 PROCESSANDO FUNÇÕES TÉCNICAS
--------------------------------------------------
Encontradas 5 funções técnicas sem descrição
[1/5] Director
  ✓ IA: O diretor é responsável pela visão criativa geral do filme, coordenando todos...
[2/5] Producer
  ✓ IA: O produtor supervisiona todos os aspectos da produção cinematográfica...

📝 PROCESSANDO GÊNEROS CINEMATOGRÁFICOS
--------------------------------------------------
Encontrados 3 gêneros sem descrição
[1/3] Action
  ✓ IA: O gênero de ação caracteriza-se por sequências dinâmicas, perseguições...

================================================================================
✅ SEED COMPLETO CONCLUÍDO!
================================================================================
Resumo geral:
  • 7 descrições geradas com IA
  • 1 descrições de fallback
  • 8 itens processados
```