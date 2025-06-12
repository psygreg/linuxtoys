## ESTAS SÃO AS INSTRUÇÕES PARA ADICIONAR JOGOS NÃO-STEAM À STEAM FLATPAK.
Isto é necessário para acessá-los pelo Modo Console.

### Limitações
- Jogos do Heroic Games Launcher não podem ser iniciados a menos que o HGL esteja aberto em segundo plano. Você deve marcar "Fechar para a barra de tarefas", "Iniciar minimizado" e "Minimizar Heroic ao iniciar um jogo" nas configurações do HGL.
- Jogos do Lutris devem funcionar sem problemas, mas você ainda precisará de mouse e teclado para usar launchers de outras lojas (como Epic, Battle.net, etc.), então é recomando que você só adicione atalhos diretos aos jogos à Steam.
- É recomendado habilitar o início de sessão automático já que ter que digitar sua senha de usuário faz o Modo Console perder um pouco de seu propósito. Para desktops Plasma, vá em Configurações do Sistema > Cores e Temas > Tela de Autenticação (SDDM) > Comportamento > marque a primeira caixa e selecione a sessão adequada.

## How-To

### Lutris

1. No Lutris, clique com o direito e em Configurar para qualquer jogo que deseje adicionar ao Big Picture.
2. Procure o Identificador, mais especificamente, seu número de ID interno.
3. Crie um atalho de desktop para o jogo a partir do mesmo menu do botão direito. Isto é importante.
4. Na Steam, adicione um jogo não-Steam e aponte-o para o atalho no desktop. Você pode precisar mudar a janela de busca para procurar por qualquer tipo de arquivo.
5. Você irá encontrar uma nova entrada chamada 'env' na lista. Clique com o botão direito nela e vá até Propriedades, e substitua cada linha com o conteúdo a seguir, substituindo 'YOUR-USERNAME' com seu nome de usuário Linux, e '6' com o número ID que obteve antes:
- Nome: o nome do jogo, assim aparecerá corretamente no menu em vez de como 'env'.
- Target: `flatpak-spawn --host`
- Launch from: `"/home/YOUR-USERNAME"`
- Launch options: `env LUTRIS_SKIP_INIT=1 flatpak run net.lutris.Lutris lutris:rungameid/6`

### Heroic

1. Vá às configurações do Heroic
2. Mude o caminho da Steam para `/home/YOUR-USERNAME/.var/app/com.valvesoftware.Steam/.steam/steam`
3. Siga os passos mencionados em **Limitações** para garantir que o Heroic inicie minimizado com o seu sistema.
4. Você agora pode configurar o Heroic para adicionar atalhos à Steam automaticamente, ou adicionar cada jogo manualmente o selecionando, indo no botão "..." e "Adicionar à Steam"

Você pode usar a [SteamGridDB](https://www.steamgriddb.com/) para obter artes de capa e outras para deixar os atalhos do Big Picture visualmente agradáveis.