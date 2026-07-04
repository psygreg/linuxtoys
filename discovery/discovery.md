# Fase I: Discovery e Design Thinking (O "Porquê")

## 1. Escolha do Projeto
* **Nome do Projeto:** LinuxToys
* **Repositório Oficial:** `https://github.com/psygreg/linuxtoys`
* **Justificativa de Escolha:** Trata-se de um projeto de software livre ativo, com base de usuários reais, código e arquitetura baseados em Python/Web totalmente acessíveis à compreensão da dupla, e com demandas reais da comunidade abertas por meio de issues.

## 2. Jobs to Be Done (JTBD)
* **Qual problema o sistema resolve?** O LinuxToys centraliza e simplifica o monitoramento de recursos de sistemas Linux (como CPU, memória e processos). Ele resolve o problema de usuários que necessitam acompanhar a saúde do sistema de forma leve e prática, mas esbarram na complexity de ferramentas puramente baseadas em terminal ou em interfaces gráficas pesadas.
* **Qual “trabalho” (Job) o usuário deseja realizar?**
> "Quando estou monitorando o desempenho e as métricas do meu servidor ou máquina Linux, quero conseguir ler e interpretar os dados de hardware na interface com clareza e sem barreiras visuais, para que eu possa tomar decisões rápidas sobre o sistema sem sofrer com fadiga ocular ou dificuldades de leitura."
* **Onde há falhas ou oportunidades?** A interface atual carece de recursos robustos de acessibilidade digital (a11y). Identificamos uma oportunidade crítica mapeada na Issue #187, aberta pelo próprio mantenedor do projeto, que destaca a necessidade de ferramentas de inclusão. A maior limitação imediata é a ausência de suporte para usuários com dislexia ou dificuldades de leitura, que frequentemente se confundem com as fontes padrões do sistema ao ler tabelas densas com dados e identificadores de processos.

## 3. Definição da Solução Proposta (MVP)
Para mitigar essa limitação de acessibilidade de forma viável, ágil e automatizada, propomos o desenvolvimento de um script em Shell Script a ser integrado ao repositório. Este componente automatizará o download, a instalação e a atualização do cache de fontes no sistema operacional das variações **OpenDyslexic** (nas versões Regular para interfaces e Mono para terminais). Isso permitirá que tanto a interface gráfica do sistema quanto o terminal se tornem imediatamente inclusivos para este grupo de usuários.

* **Issue de Referência:** `https://github.com/psygreg/linuxtoys/issues/187`

## 4. Design Thinking com IA
### 4.1 Personas
* **Persona 1: O Desenvolvedor com Dislexia**
  * **Nome:** Lucas Rocha, 24 anos.
  * **Perfil:** Desenvolvedor Backend Júnior. Utiliza Linux (Ubuntu) diariamente para trabalhar e gerenciar servidores de teste locais.
  * **Relação com o LinuxToys:** Utiliza a ferramenta para monitorar o consumo de recursos de suas aplicações em tempo real de forma leve.
  * **Frustração:** Por ter dislexia, Lucas sente muita fadiga visual e frequentemente confunde números e letras graficamente parecidas (como b e d, ou 8 e B) ao ler rapidamente tabelas densas de processos no terminal ou na interface gráfica.
* **Persona 2: O Administrador de Sistemas Sênior (Foco em Acessibilidade Geral)**
  * **Nome:** Carlos Eduardo (Cadu), 42 anos.
  * **Perfil:** Administrador de Sistemas veterano. Gerencia dezenas de servidores remotos e preza estritamente por ferramentas minimalistas.
  * **Relação com o LinuxToys:** Acompanha o projeto para utilizar em servidores menores e apoiar iniciativas da comunidade open-source.
  * **Frustração:** Carlos não possui dislexia, mas sofre de forte astigmatismo e cansaço visual após longas jornadas de trabalho. Ele defende que ferramentas de monitoramento precisam ser inclusivas e fáceis de customizar (fontes e contrastes) para evitar erros operacionais decorrentes do cansaço de leitura.

### 4.2 Mapa de Empatia (Foco: Lucas Rocha)
* **O que pensa e sente?** "Preciso monitorar meu sistema rápido, mas essas tabelas cheias de dados me dão dor de cabeça." / "Tenho medo de encerrar o processo errado no terminal por confundir os IDs."
* **O que vê?** Interfaces saturadas de texto utilizando fontes padrões (como Arial ou Monospace comum), nas quais as letras parecem flutuar ou se misturar quando ele está cansado.
* **O que ouve?** Da comunidade: "Quem usa Linux tem que se acostumar com o terminal padrão". / Do mantenedor do projeto: "Precisamos de ajuda com ferramentas de acessibilidade".
* **O que fala e faz?** Tenta aumentar o zoom da tela (o que frequentemente quebra o layout da aplicação) ou copia o texto das métricas para um editor externo para conseguir ler com calma.
* **Dores (Pains):** Fadiga visual extrema após poucos minutos analisando relatórios de hardware; lentidão para tomar decisões simples por necessidade de reeler os dados várias vezes.
* **Necessidades (Gains):** Uma forma rápida de renderizar os textos e tabelas do sistema em uma tipografia desenhada especificamente para evitar a rotação mental das letras (como a OpenDyslexic).

### 4.3 Ideias de Solução Exploradas
Durante o processo de ideação com o auxílio da IA, foram levantadas três abordagens técnicas para sanar o problema relatado na issue #187:
* **Abordagem 1 (Injeção via CSS na Web):** Criar uma extensão de navegador ou alterar o código-fonte do front-end do LinuxToys para carregar a fonte dinamicamente via Google Fonts.
  * *Crítica:* Resolveria apenas o problema de visualização na interface web, deixando o terminal (CLI) totalmente de fora.
* **Abordagem 2 (Script de Automação no Sistema - Escolhida):** Desenvolver um script Shell que baixa as variações Regular e Mono da fonte OpenDyslexic, instala nativamente no diretório de fontes do usuário Linux e atualiza o cache de fontes do sistema.
  * *Vantagem:* Resolve o problema de forma global, leve e automatizada, afetando positivamente tanto o navegador quanto o terminal.
* **Abordagem 3 (Configuração manual via documentação):** Adicionar um tutorial descritivo no arquivo README ensinando o usuário a baixar e instalar as fontes manualmente por conta própria.
  * *Crítica:* Baixo valor agregado; transfere o esforço para o usuário e não resolve o problema através de automação de software.

### 4.4 Prompts Utilizados
* **Prompt 1 (Personas e Empatia):** `> "Atue como especialista em Design Thinking e UX. Com base no projeto open-source LinuxToys e no problema de acessibilidade visual/dislexia relatado na Issue #187, crie 2 personas (uma com dislexia e outra com visão cansada/astigmatismo) e um mapa de empatia focado na persona com dislexia."`
* **Prompt 2 (Ideação):** `> "Com base nas personas criadas, explore 3 ideias de solução técnica de diferentes níveis de complexidade para integrar a fonte OpenDyslexic ao ecossistema do LinuxToys (focando em automação)."`

## 5. Reflexão Crítica do uso da IA
O uso da Inteligência Artificial agilizou significativamente a etapa de empatia ao materializar com rapidez cenários cotidianos de dificuldade enfrentados por usuários neurodivergentes ou com limitações visuais ao interagir com fluxos densos de dados de hardware. No entanto, em um primeiro momento, a IA tendeu a sugerir soluções limitadas ao ecossistema estritamente Web (como manipulação dinâmica de propriedades CSS por JavaScript).

A decisão humana da dupla foi intervir criticamente sobre as propostas para direcionar a engenharia da solução rumo a um script Shell nativo. O motivo dessa escolha técnica baseou-se no fato de que usuários de ecossistemas Linux operam massivamente via terminal. Garantir que a fonte OpenDyslexic esteja instalada nativamente no sistema operacional de forma automatizada expande o ganho real de acessibilidade para além da interface web do LinuxToys, cobrindo também a interface de linha de comando (CLI) do desenvolvedor sem onerar o desempenho do software.