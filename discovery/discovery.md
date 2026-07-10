# Fase I: Discovery e Design Thinking (O "Porquê")

## 1. Escolha do Projeto
* **Nome do Projeto:** LinuxToys
* **Repositório Oficial:** https://github.com/psygreg/linuxtoys
* **Justificativa de Escolha:** Trata-se de um projeto de software livre ativo, com base de usuários reais e arquitetura baseada em Python/Web acessível. O projeto apresenta demandas reais da comunidade abertas por meio de issues, o que viabiliza uma intervenção de engenharia com impacto prático imediato.

## 2. Jobs to Be Done (JTBD)
* **Qual problema o sistema resolve?** O LinuxToys centraliza e simplifica o monitoramento de recursos de sistemas Linux (como CPU, memória e processos), resolvendo o problema de usuários que necessitam acompanhar a saúde do sistema de forma leve, sem a complexidade de ferramentas puramente baseadas em terminal ou interfaces gráficas pesadas.
* **Qual “trabalho” (Job) o usuário deseja realizar?**
  > *"Quando estou monitorando o desempenho e as métricas do meu servidor ou máquina Linux, quero conseguir ler e interpretar os dados de hardware na interface com clareza e sem barreiras visuais, para que eu possa tomar decisões rápidas sobre o sistema sem sofrer com fadiga ocular ou dificuldades de leitura."*
* **Onde há falhas ou oportunidades?** A interface carece de recursos robustos de acessibilidade digital (a11y). Identificamos uma oportunidade crítica mapeada na **Issue #187**, aberta pelo próprio mantenedor do projeto, que destaca a necessidade de ferramentas de inclusão. A maior limitação imediata é a fadiga visual e a dificuldade de leitura ao analisar tabelas densas com dados de hardware e identificadores de processos, onde fontes comuns do sistema fundem ou confundem caracteres graficamente parecidos.

## 3. Design Thinking com IA e Evolução do Escopo

### 3.1 Personas

#### Persona 1: O Desenvolvedor com Baixa Visão e Fadiga Cognitiva
* **Nome:** Lucas Rocha, 24 anos.
* **Perfil:** Desenvolvedor Backend Júnior. Utiliza Linux (Ubuntu) diariamente para trabalhar e gerenciar servidores de teste locais.
* **Relação com o LinuxToys:** Utiliza a ferramenta para monitorar o consumo de recursos de suas aplicações em tempo real.
* **Frustração:** Sente muita fadiga visual e frequentemente confunde números e letras graficamente parecidas (como `l`, `1` e `I`, ou `0` e `O`) ao ler rapidamente tabelas densas de processos (PIDs). Aumentar a escala por porcentagem no sistema de forma fracionada (a partir de 1.04) invade, corta e quebra os layouts das janelas que ele utiliza.

#### Persona 2: O Administrador de Sistemas Sênior (Foco em Astigmatismo e Ergonomia)
* **Nome:** Carlos Eduardo (Cadu), 42 anos.
* **Perfil:** Administrador de Sistemas veterano. Gerencia dezenas de servidores remotos e preza estritamente por ferramentas minimalistas.
* **Relação com o LinuxToys:** Acompanha o projeto para utilizar em servidores menores e apoiar iniciativas open-source.
* **Frustração:** Sofre de forte astigmatismo e cansaço visual após longas jornadas frente a fontes comuns. Ele defende que ferramentas de monitoramento precisam ser inclusivas e fáceis de customizar ou reverter para evitar erros operacionais graves decorrentes do cansaço de leitura.

### 3.2 Mapa de Empatia (Foco: Lucas Rocha)
* **O que pensa e sente?** "Preciso monitorar meu sistema rápido, mas essas tabelas cheias de dados fundem na minha tela." / "Tenho medo de encerrar o processo errado no terminal por confundir os IDs dos PIDs."
* **O que vê?** Interfaces saturadas de texto utilizando fontes padrões de sistema, nas quais caracteres semelhantes se misturam quando ele está cansado, além de menus que quebram quando tenta aplicar zoom forçado por escala fracionada.
* **O que ouve?** Da comunidade: "Quem usa Linux tem que se acostumar com o terminal padrão". Do mantenedor do projeto: "Precisamos de ajuda com ferramentas de acessibilidade".
* **O que fala e faz?** Tenta aplicar multiplicadores de escala no sistema (o que descobre que invade e esmaga o layout das aplicações) ou copia o texto das métricas para editores externos para conseguir ler com calma.
* **Dores (Pains):** Fadiga visual extrema após poucos minutos analisando relatórios de hardware; lentidão para tomar decisões simples por necessidade de reeler os dados várias vezes.
* **Necessidades (Gains):** Uma automação nativa que aplique uma tipografia com alta distinção de glifos em tamanho padrão confortável, sem deformar as janelas e caixas de diálogo do Ubuntu.

---

## 4. Histórico de Engenharia e Reflexão Crítica (Uso de IA)

### 4.1 Prompts Utilizados na Fase de Concepção
1. *Empathy & Persona Prompt:* `Atue como especialista em Design Thinking e UX. Com base no projeto open-source LinuxToys e no problema de acessibilidade visual relatado na Issue #187, crie 2 personas (uma com forte fadiga/baixa visão e outra com astigmatismo) e um mapa de empatia focado na persona principal.`
2. *Ideation Prompt:* `Com base nas personas criadas, explore 3 ideias de solução técnica de diferentes níveis de complexidade para integrar uma solução tipográfica de acessibilidade ao ecossistema do LinuxToys (focando em automação e no comportamento global do sistema).`

### 4.2 Avaliação Crítica e Tomada de Decisão Humana (A Pivotagem)
O desenvolvimento deste projeto não seguiu uma linha perfeitamente linear, o que reflete um processo real de Engenharia de Software:

1. **O Marco Zero e o Primeiro Commit:** Inicialmente, influenciados pelas primeiras sugestões da IA, o foco estava direcionado para a fonte *OpenDyslexic* e fatores de escala dinâmicos (`text-scaling-factor`). O primeiro commit estrutural foi realizado com base nessa premissa de escopo.
2. **A Intervenção Humana e Testes em Ambiente Real:** Ao realizarmos testes práticos no ecossistema Ubuntu/GNOME, a dupla identificou falhas graves de layout: fatores de escala fracionados (como `1.04`) quebravam caixas de texto e invadiam o design de aplicações desktop e do próprio terminal. Adicionalmente, a *OpenDyslexic* mostrou-se excessivamente agressiva para a densidade de dados do LinuxToys.
3. **A Decisão de Pivotar:** Decidimos pivotar a solução técnica para a família de fontes **Atkinson Hyperlegible** (desenvolvida pelo Braille Institute especificamente para legibilidade de glifos individuais). Fixamos o tamanho nominal em `12` diretamente via chaves `gsettings`, mantendo o fator de escala em `1.0` estável.
4. **Resolução de Conflitos Ocultos (PATH e Isolamento):** A IA não previu que a execução do script por desenvolvedores utilizando ambientes virtuais ativos (como instâncias Anaconda ou venv) bloquearia o escopo das variáveis do sistema real, impedindo os comandos `gsettings` de atingirem o banco de dados `dconf` do GNOME do usuário. A engenharia humana interveio inserindo rotinas de detecção e bypass de isolamento de sub-shell dentro do script final.