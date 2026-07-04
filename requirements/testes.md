# Cenários de Teste do MVP (Derivados dos Critérios de Aceite)

Este documento apresenta os critérios de aceite e os respectivos cenários de teste para as histórias mapeadas no escopo do MVP de acessibilidade.

---

## História 1: Automatizar a instalação de fontes de acessibilidade

### Critério de Aceite:
Dado que o usuário executa o script de instalação com conexão à internet,
Quando o processo de download e atualização de cache for concluído,
Então os arquivos da fonte devem estar localizados no diretório do usuário e reconhecidos pelo sistema.

### Cenários de Teste:
* **Cenário 1 (Sucesso - Dados Válidos):** Executar o script em ambiente Linux com internet ativa -> As fontes são baixadas com sucesso, o cache é atualizado (fc-cache) e o comando fc-list detecta a nova fonte.
* **Cenário 2 (Tratamento de Erro - Sem Internet):** Executar o script sem conexão à internet -> O script identifica a falha na requisição de download (curl), aborta a instalação de forma segura e exibe uma mensagem clara de erro, sem tentar atualizar o cache com arquivos corrompidos.
* **Cenário 3 (Validação Falha - Sistema Incompatível):** Executar o script em um sistema operacional que não possui o gerenciador de fontes fontconfig ou não seja Linux -> O script valida os requisitos do sistema antes de começar, identifica a ausência dos comandos base e encerra a execução alertando o usuário.

---

## História 2: Reverter alterações e restaurar fontes padrão do sistema

### Critério de Aceite:
Dado que o usuário deseja remover as fontes instaladas pela automação,
Quando aciona o comando de desinstalação,
Então o diretório específico de fontes criadas deve ser limpo e o cache do sistema atualizado para refletir o estado original.

### Cenários de Teste:
* **Cenário 1 (Remoção com Sucesso):** Executar o script de reversão -> A pasta dedicada da fonte é deletada, o cache é limpo e a fonte deixa de constar no sistema.
* **Cenário 2 (Diretório Inexistente):** Executar a reversão em um sistema que nunca instalou a fonte -> O script valida que o diretório não existe e encerra informando que o sistema já está no estado padrão, sem disparar erros de comando.

---

## História 3: Alternar o áudio do sistema para o modo Mono

### Critério de Aceite:
Dado que o sistema de áudio está operando em formato Estéreo,
Quando o script de automação de áudio for acionado,
Então o perfil de canais de áudio deve ser unificado em canal único (Mono).

### Cenários de Teste:
* **Cenário 1 (Mudança de Perfil Ativa):** Executar o script com Pipewire ativo -> Canais são mapeados para Mono com sucesso.
* **Cenário 2 (Servidor de Áudio Ausente):** Executar o script em um servidor sem subsistema de som configurado -> O script falha graciosamente notificando que o gerenciador de áudio não foi encontrado.

---

## História 4: Customizar o tamanho geral das fontes por linha de comando

### Critério de Aceite:
Dado que o usuário passa um parâmetro numérico válido de escala,
Quando o script processa o argumento,
Então o tamanho da fonte do terminal de monitoramento é adjusted proporcionalmente.

### Cenários de Teste:
* **Cenário 1 (Argumento Válido):** Passar o parâmetro de aumento (ex: +2) -> Fonte do terminal aumenta de tamanho.
* **Cenário 2 (Argumento Inválido/Campo Vazio):** Passar um caractere de texto ou nenhum valor -> O script aplica uma validação de tipo, rejeita a entrada e mantém a configuração padrão de segurança.

---

## História 5: Aplicar CSS customizado para botões e barras de títulos maiores

### Critério de Aceite:
Dado que os arquivos de estilo padrão possuem dimensões reduzidas de clique,
Quando o patch de acessibilidade visual de botões é injetado,
Então as propriedades de padding e dimensões dos botões de ação são expandidas.

### Cenários de Teste:
* **Cenário 1 (Injeção de Estilo):** Aplicar o patch CSS na interface web -> Elementos visuais aumentam a área útil de clique.
* **Cenário 2 (Incompatibilidade de Elemento):** Arquivo de layout original modificado ou ausente -> O validador interrompe a aplicação do patch para não quebrar a estrutura visual da página.