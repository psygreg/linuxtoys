O Sloth-Bash traz uma série de melhoramentos por cima do `bash` convencional. Alguns deles talvez sejam familiares se você já tiver usado `zsh`.

- **Resposta intuitiva:** basta digitar o nome do arquivo para executá-lo caso seja executável; carregar um venv caso exista e executá-lo com `python3` caso seja um arquivo *.py*; ou acionar o `xdg-open` nos demais casos.

- **Redirecionamento de Flatpaks:** simplifica a execução de aplicativos Flatpak pelo terminal, tornando o `flatpak run` desnecessário por meio do tratamento inteligente de comandos. Chega de `io.github.kolunmi.Bazaar`: basta usar `bazaar`!

- **Abra aplicativos facilmente pelo terminal, desvinculando-os automaticamente** com `detach nome-do-app`. Perfeito para usar com algo como o Quake Terminal para GNOME ou o `yakuake`. Também funciona com *redirecionamento de Flatpaks*, executáveis locais e *encaminhamento para Distrobox*.

- **Redirecionamento de `cp` e `mv` para `rsync`:** torne suas operações com arquivos mais eficientes usando as cópias incrementais do `rsync`, além de exibir o progresso de forma inteligente em tarefas maiores.

- **Gerenciamento simples de arquivos no shell:** executa `ls` automaticamente após `cd`, para que você nunca se perca entre seus arquivos, e habilita a opção *autocd* do shell para permitir uma navegação mais intuitiva pelos seus subdiretórios.

- **Atalhos mais usados do zsh:** `md`, `rd`, `mkcd`, `take`, `~` e `..` funcionam exatamente como no zsh, enquanto você pode usar `cd ...`, `cd ....` e `cd .....` para os demais comandos de navegação para diretórios superiores.

- **`all`:** seleciona todos os arquivos e subdiretórios no local atual como alvos para `rd`, `rm`, `cp` e `mv`.

- **Autocompletar aprimorado:** a tecla *Tab* percorre todas as opções em vez de apenas exibi-las.

- **Integrações do FZF com o shell:** se o *fzf* estiver instalado, o `sloth-bash` habilita a integração padrão com o Bash, incluindo pesquisa difusa no histórico com `Ctrl+R`.

- **Cores básicas para comandos:** habilita saída colorida para `ls`, `dir`, `vdir` e `grep`, além de aliases conhecidos como `ll`, `la` e `l`.

- **Interpretação de comandos sem distinção entre maiúsculas e minúsculas:** `ls`, `Ls`, `lS` ou `LS` — seu comando sempre funcionará.

- **Encaminhamento para Distrobox:** entre no shell do seu Distrobox usando `nomedodistrobox` e envie comandos para seus Distroboxes executando `nomedodistrobox comando` (seguido de quaisquer argumentos adicionais, se necessário). Como os Distroboxes utilizam o arquivo *`~/.bashrc`* do usuário, o sloth-bash também funciona dentro deles!
