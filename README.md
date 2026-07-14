## 📚Trabalho Acadêmico (CSI412)

Este repositório é um fork do [LinuxToys](https://github.com/psygreg/linuxtoys) desenvolvido como
Trabalho Prático da disciplina **CSI412 – Engenharia de Software I**, ministrada pelo professor
Igor Muzetti Pereira na Universidade Federal de Ouro Preto (UFOP), semestre 2026/1.

**Tema:** Open Source Discovery & Design — Acessibilidade Visual no LinuxToys

### Equipe
- Desenvolvedor: BrunoHPS7
- Revisor: YuriFerreira11

### Estrutura do trabalho

| Pasta | Conteúdo |
|---|---|
| [`/discovery`](./discovery) | JTBD, personas e mapa de empatia |
| [`/requirements`](./requirements) | Backlog de histórias de usuário e cenários de teste |
| [`/diagrams`](./diagrams) | Diagramas de sequência, classes e componentes (Mermaid) |
| [`/ai-usage`](./ai-usage) | Prompts utilizados e avaliação crítica do uso de IA |
| [`/scripts`](./scripts) | Implementação do MVP: instalação e reversão da fonte Atkinson Hyperlegible |

### O problema (JTBD)
Usuários com deficiência visual, baixa visão ou dificuldades severas de leitura enfrentam barreiras de acessibilidade 
ao interagir com o sistema operacional, já que o Linux não oferece um caminho nativo simples para aplicar tipografia 
otimizada para legibilidade. O job a ser feito:
- "Quando estou utilizando meu computador no dia a dia, quero que o LinuxToys configure automaticamente 
uma tipografia de alta acessibilidade no meu sistema operacional, para que eu possa ler e interagir com a 
interface sem barreiras visuais e sem precisar realizar configurações manuais complexas."*

### MVP implementado
Scripts de instalação (`scripts/instalation_font.sh`) e reversão
(`scripts/reversion_font.sh`) que baixam, instalam e aplicam a fonte **Atkinson Hyperlegible**
no ambiente GNOME/Ubuntu, sem exigir privilégios de superusuário.

### Pull Requests
- [PR #1 — especificação inicial](../../pull/1)
- [PR #3 — scripts de instalação/reversão de fonte](../../pull/3)
- [PR #4 — diagramas e relatório de discovery](../../pull/4)

---