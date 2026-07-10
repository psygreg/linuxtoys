# Fase III: Modelagem UML Textual (O "Como")

Esta seção apresenta os diagramas arquiteturais baseados estritamente nas regras e fluxos de execução do MVP de acessibilidade tipográfica.

## 2. Diagrama de Componentes (Estrutura e Acoplamento com o Host)

O diagrama de componentes abaixo ilustra o acoplamento lógico das funções do script de automação, detalhando como a suíte interage com os subsistemas nativos do sistema operacional host (Ubuntu/GNOME).

```mermaid
graph TD

subgraph UI["Interface do Usuário"]
    CLI["Terminal / Interface CLI"]
end

subgraph Suite["Suíte de Automação"]
    Core["Core Engine\ninstall_font.sh"]
    EnvLimper["Limpador de Ambiente Virtual"]
    NetClient["Cliente de Download"]
    SysInjetor["Injetor de Configurações"]
end

subgraph Host["Subsistemas do Host (Ubuntu/GNOME)"]
    Net["Rede / Internet"]
    FS["Sistema de Arquivos Local"]
    FCache["fc-cache"]
    Dconf["dconf / gsettings"]
end

CLI --> Core

Core --> EnvLimper
Core --> NetClient
Core --> SysInjetor

NetClient -->|"curl --fail"| Net
SysInjetor -->|"Salva .ttf"| FS
SysInjetor -->|"Atualiza"| FCache
SysInjetor -->|"Ajusta Fonte/Tamanho"| Dconf