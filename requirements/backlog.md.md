# Fase II: Engenharia de Requisitos - Backlog do MVP

Este documento define o escopo do MVP de Acessibilidade Visual e Sonora mapeado para o ecossistema do projeto LinuxToys.

## 1. Backlog de Histórias de Usuário

### História 1: Instalação Automatizada de Fontes de Acessibilidade
* **Estrutura:** **Como** Lucas (desenvolvedor com baixa visão), **quero** executar um script que automatize o download e instalação da fonte Atkinson Hyperlegible no tamanho 12, **para que** eu consiga ler tabelas densas de processos sem sofrer fadiga ocular imediata.
* **Critério de Aceite:**
  * **Dado que** o usuário executa o script de instalação em ambiente Ubuntu ou derivado com conexão à internet,
  * **Quando** o processo de download, limpeza de isolamento de ambiente e atualização de cache for concluído,
  * **Então** os arquivos da família completa da fonte Atkinson Hyperlegible devem estar localizados no diretório local e aplicados instantaneamente com tamanho 12 no GNOME Ajustes.

### História 2: Reversão Completa de Modificações do Sistema
* **Estrutura:** **Como** Carlos (SysAdmin focado em ergonomia), **quero** acionar um comando de rollback/restauração, **para que** o meu sistema retorne ao visual de fábrica com lixo zero absoluto caso eu não queira mais a modificação.
* **Critério de Aceite:**
  * **Dado que** o usuário deseja remover as modificações feitas pela automação,
  * **Quando** aciona o comando de restauração,
  * **Então** o diretório local de fontes deve ser removido, o cache limpo e os registros do GNOME Ajustes resetados para o padrão de fábrica.

### História 3: Alternância de Áudio para o Modo Mono
* **Estrutura:** **Como** um usuário com limitações de percepção espacial ou auditiva, **quero** alternar o áudio do sistema para o modo Mono via script, **para que** eu não perca notificações sonoras ou alertas de hardware emitidos em canais isolados.
* **Critério de Aceite:**
  * **Dado que** o sistema de áudio está operando em formato Estéreo,
  * **Quando** o script de automação de áudio for acionado,
  * **Então** o perfil de canais de áudio deve ser unificado em canal único (Mono).

### História 4: Customização do Tamanho da Fonte via Linha de Comando
* **Estrutura:** **Como** um desenvolvedor que trabalha com diferentes resoluções de tela, **quero** passar o tamanho numérico fixo desejado para a fonte como argumento do script, **para que** o texto da interface seja atualizado sem distorcer as caixas de layout.
* **Critério de Aceite:**
  * **Dado que** o usuário passa o tamanho numérico fixo desejado para a fonte da interface,
  * **Quando** o script valida e processa o argumento,
  * **Então** o tamanho do texto do ambiente gráfico é atualizado diretamente nas chaves do sistema sem distorcer o layout de janelas.

### História 5: Patch CSS para Elementos de Interface Expandidos
* **Estrutura:** **Como** Lucas, **quero** injetar um patch CSS customizado na interface web do LinuxToys, **para que** as propriedades de padding das barras de títulos e botões aumentem a área útil de clique.
* **Critério de Aceite:**
  * **Dado que** os arquivos de estilo padrão possuem dimensões reduzidas de clique,
  * **Quando** o patch de acessibilidade visual de botões é injetado,
  * **Então** as propriedades de padding e dimensões dos botões de ação são expandidas.

---

## 2. Tabela de Priorização do MVP e Implementação do PR

Abaixo está o mapeamento de prioridades do backlog. A História 1 foi selecionada como o núcleo técnico do Pull Request (PR).

| ID       | História de Usuário                    | Status                | Justificativa Técnica da Priorização                                                                                                          |
| :------- | :------------------------------------- | :-------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| **US01** | Instalação de Fontes de Acessibilidade | **IMPLEMENTADA (PR)** | **Core do MVP:** Resolve a dor de legibilidade de glifos da persona principal diretamente no SO de forma global (afeta terminal e navegador). |
| **US02** | Reverter alterações e restaurar padrão | **IMPLEMENTADA**      | **Segurança e Idempotência:** Garante o rollback completo do sistema sem deixar arquivos órfãos (requisito de boa vizinhança open-source).    |
| **US03** | Alternar o áudio para Mono             | Mapeada (MVP)         | Escopo secundário focado em acessibilidade de áudio. Será abordado em sprints futuras.                                                        |
| **US04** | Customizar tamanho via CLI             | **IMPLEMENTADA**      | Evolução direta da US01, adicionando flexibilidade para diferentes resoluções de monitores.                                                   |
| **US05** | Aplicar CSS customizado na interface   | Mapeada (MVP)         | Alteração de menor prioridade global por ficar restrita exclusivamente ao front-end web.                                                      |