# Fase V: Relatório de Uso de Inteligência Artificial / Artificial Intelligence Usage Report

## 1. Transparência: Prompts Utilizados

Toda a base estrutural, mapeamento inicial de personas, engenharia de requisitos e modelagem UML textual deste repositório contaram com o auxílio de inteligência artificial generativa como aceleradora, sendo posteriormente refinados, corrigidos e validados pela dupla[cite: 1].

### 1.1 Planejamento Estratégico e Engenharia Reversa (Fase Zero)
* **Contexto:** Usado antes de iniciar qualquer linha de código ou especificação, com o objetivo de analisar sistematicamente as restrições pedagógicas do projeto e traçar uma esteira de execução sem desvios de escopo[cite: 1].
* **Prompt Real Adaptado:** 
  > "Atue como um Engenheiro de Software e Consultor Acadêmico. Com base no PDF em anexo contendo as instruções formais do Trabalho Prático (Open Source Discovery & Design), analise minuciosamente todas as regras, entregáveis por pasta, critérios de avaliação e restrições metodológicas[cite: 1]. Forneça um passo a passo sistemático e cronológico de tudo o que a dupla deve realizar — desde a configuração do ambiente Git até a preparação dos slides finais —, garantindo que nenhum requisito obrigatório seja omitido[cite: 1]."

### 1.2 Concepção Inicial e Discovery (Fase I)
* **Contexto:** Usado para abrir o entendimento sobre o ecossistema do projeto analisado e ferramentas de acessibilidade[cite: 1].
* **Prompt:** 
  > "Atue como um Engenheiro de Software Sênior e Especialista em Produto. Analise o contexto do repositório LinuxToys[cite: 1]. Preciso identificar oportunidades de melhoria focadas em acessibilidade visual (como dislexia e fadiga visual)[cite: 1]. Crie o Job to Be Done (JTBD) principal, proponha uma solução de automação via script Shell que baixe fontes de acessibilidade de forma local no Ubuntu, e gere 2 personas completas com seus respectivos Mapas de Empatia[cite: 1]."

### 1.3 Engenharia de Requisitos e Cenários de Teste (Fase II)
* **Contexto:** Usado para estruturar a primeira versão do backlog e cenários (ainda sob a premissa conceitual da fonte OpenDyslexic)[cite: 1].
* **Prompt:** 
  > "Com base no MVP do instalador de fontes de acessibilidade para o LinuxToys, estruture um backlog com no mínimo 5 histórias de usuário no padrão 'Como/Quero/Para que'[cite: 1]. Para cada história, defina critérios de aceite usando a sintaxe 'Dado que/Quando/Então' e derive cenários de teste detalhando caminhos de sucesso, erro (falha de conexão com a internet) e restrição (sistema operacional incompatível)[cite: 1]."

### 1.4 Modelagem UML Textual em Mermaid (Fase III)
* **Contexto:** Prompt inserido após a pivotagem e decisão técnica humana pela tipografia Atkinson Hyperlegible[cite: 1].
* **Prompt:** 
  > "Com base no MVP revisado (instalação da fonte Atkinson Hyperlegible 12 via gsettings no Ubuntu, com tratamento de erro para queda de internet e rotina de desligamento de ambientes virtuais como Anaconda/venv), gere três códigos textuais em formato Mermaid: um Diagrama de Sequência do fluxo de instalação, um Diagrama de Classes das responsabilidades lógicas do script e um Diagrama de Componentes demonstrando o acoplamento com o host do sistema operacional[cite: 1]."

### 1.5 Auditoria Final, Formatação e Code Review de Documentos (Fase de Fechamento)
* **Contexto:** Usado na reta final do projeto para consolidar todas as alterações históricas (como a pivotagem de fontes), garantir que a sintaxe exigida pelo professor estivesse correta e gerar os diagramas UML que faltavam de forma integrada[cite: 1].
* **Prompt Real Adaptado:** 
  > "Atue como um Engenheiro de Software especialista em Garantia de Qualidade (QA). Estou te enviando o rascunho dos meus documentos de Discovery, Backlog e Testes, junto com o PDF de diretrizes da disciplina e as decisões que tomamos (como a pivotagem da OpenDyslexic para a Atkinson Hyperlegible por problemas de layout no GNOME). Revise tudo sistematicamente, corrija a sintaxe das histórias de usuário para o padrão formal e gere os códigos Mermaid para os diagramas de classe, sequência e componentes que faltam, exportando os arquivos prontos no formato Markdown."

---

## 2. Avaliação Crítica e Decisão Humana (Human-in-the-Loop)

O desenvolvimento deste projeto comprova que a IA funciona como uma excelente ferramenta de aceleração de rascunhos, mas falha ao compreender nuances práticas de ambientes de execução reais e usabilidade cotidiana[cite: 1]. A engenharia humana da dupla foi o fator determinante para o sucesso do MVP através das seguintes intervenções críticas[cite: 1]:

### 2.1 Planejamento Prévio vs. Execução Ágil
A decisão humana de rodar um prompt focado na interpretação do PDF de diretrizes antes de iniciar o projeto foi o que garantiu a consistência entre todas as fases[cite: 1]. A IA estruturou um cronograma macro que permitiu à dupla correlacionar as dores das Personas (Fase I) diretamente com os critérios de aceite e cenários de teste (Fase II)[cite: 1], impedindo o desenvolvimento de scripts isolados ou desconectados das exigências pedagógicas estabelecidas[cite: 1].

### 2.2 A Pivotagem da Fonte (OpenDyslexic vs. Atkinson Hyperlegible)
* **O que a IA sugeriu:** A IA inicialmente recomendou o uso da fonte *OpenDyslexic* combinada com um fator de escala dinâmico (`text-scaling-factor`) acima de 1.04[cite: 1].
* **A Crítica Humana:** Em testes reais executados pela dupla no ecossistema Ubuntu/GNOME, descobrimos que escalas fracionadas quebram completamente o layout das janelas, cortam caixas de texto e poluem as tabelas densas de processos do LinuxToys[cite: 1]. Além disso, a tipografia OpenDyslexic mostrou-se excessivamente agressiva para a leitura ágil de caracteres alfanuméricos curtos (como PIDs e hashes)[cite: 1].
* **Decisão Humana:** Pivotamos o escopo técnico para a família de fontes **Atkinson Hyperlegible** (desenvolvida pelo Braille Institute para distinção clara de glifos individuais)[cite: 1]. Fixamos seu tamanho nominal em 12 estável e mantivemos o fator de escala do sistema em 1.0[cite: 1]. Isso garantiu hiperlegibilidade sem deformar o ambiente gráfico[cite: 1].

### 2.3 O Bug Oculto do Isolamento de PATH (Anaconda e venv)
* **O que a IA sugeriu:** A IA gerou os comandos de injeção `gsettings set org.gnome.desktop.interface...` assumindo que eles rodariam de maneira transparente em qualquer terminal Bash genérico[cite: 1].
* **A Crítica Humana:** A IA não previu que desenvolvedores frequentemente utilizam ambientes virtuais ativos (como instâncias Anaconda (base) ou venv de Python)[cite: 1]. Quando ativos, esses ambientes alteram e isolam o sub-shell do terminal, bloqueando o acesso direto dos comandos de automação ao banco de dados `dconf` do sistema real, fazendo o script falhar de forma silenciosa[cite: 1].
* **Decisão Humana:** Injetamos manualmente no código do script uma rotina em Shell Script para detectar se variáveis do `conda` ou `virtualenv` estão ativas no PATH[cite: 1]. O script efetua de forma programática o bypass/desativação temporária no sub-shell, aumentando a robustez da solução e garantindo que a configuração de acessibilidade atinja o ecossistema real do usuário[cite: 1].

### 2.4 Segurança de Privilégios e Diretórios
* **O que a IA sugeriu:** Inicialmente, os scripts conceituais fornecidos pela IA utilizavam privilégios de superusuário (`sudo`) para mover arquivos para a pasta global de sistema `/usr/share/fonts`[cite: 1].
* **A Crítica Humana:** Exigir privilégios root para um script de customização estética de interface viola boas práticas de segurança em Engenharia de Software e traz riscos desnecessários de corrupção do sistema operacional do usuário[cite: 1].
* **Decisão Humana:** Alteramos a arquitetura de implantação do MVP para mapear, criar e popular exclusivamente o diretório local do usuário comum (`~/.local/share/fonts`)[cite: 1]. Todo o ciclo de instalação e atualização de cache roda sem necessidade de privilégios elevados, mantendo a integridade e segurança do host de maneira isolada[cite: 1].

### 2.5 Engenharia de Prompt para Validação de Entregáveis
A inclusão de uma etapa de auditoria assistida por IA na fase final nos permitiu cruzar os rascunhos gerados ao longo do ciclo com o PDF original de diretrizes do trabalho[cite: 1]. Embora a IA tenha proposto uma estrutura puramente teórica de arquivos, a decisão humana da dupla foi aplicar uma filtragem fina para garantir que as inconsistências de nomenclatura fossem sanadas e as evoluções do projeto (como o histórico do primeiro commit versus o escopo final implementado) fossem explicadas como parte do ciclo de vida iterativo real do desenvolvimento de software.