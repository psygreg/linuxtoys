# Fase III: Modelagem UML Textual (O "Como")

Esta seção apresenta os diagramas arquiteturais baseados estritamente nas regras e fluxos de execução do MVP de acessibilidade tipográfica.

## 1. Diagrama de Sequência (Instalação da Fonte e Injeção no GNOME)

O diagrama abaixo ilustra o fluxo cronológico de execução do script core priorizado para o Pull Request, mapeando o tratamento de limpeza de ambiente virtual e injeção no sistema operacional.

# Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário (Lucas/Carlos)
    participant S as install_font.sh
    participant E as EnvManager (Venv/Conda)
    participant N as Servidor Remoto (Internet)
    participant OS as Sistema Operacional (Ubuntu)

    U->>S: Executa o script de instalação
    S->>E: Verifica e desativa ambientes virtuais locais (limpeza de PATH)
    E-->>S: Ambiente limpo / Variáveis nativas restauradas
    S->>N: Realiza requisição das variantes (.ttf) via curl --fail
    
    alt Sem conexão com a internet (Cenário 2)
        N-->>S: Falha na requisição (Erro de Rede)
        S-->>U: Aborta a execução de forma segura (Aviso de erro)
    else Conexão ativa e Sucesso (Cenário 1)
        N-->>S: Retorna os arquivos da Atkinson Hyperlegible
        S->>OS: Move arquivos para o diretório local (~/.local/share/fonts)
        S->>OS: Atualiza o cache de fontes do sistema (fc-cache -fv)
        S->>OS: Injeta as configurações via gsettings set
        OS-->>S: Alterações aplicadas instantaneamente no GNOME Ajustes
        S-->>U: Notifica sucesso da operação (Tamanho 12 ativo)
    end