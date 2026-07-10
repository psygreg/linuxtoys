# Fase II: Engenharia de Requisitos - Cenários de Teste

Este documento detalha os cenários de teste derivados diretamente dos critérios de aceite do backlog do MVP.

## História 1: Automatizar a instalação de fontes de acessibilidade
* **Cenário 1 (Sucesso com Isolamento de Ambiente):** Executar o script no terminal com o ambiente Anaconda (base) ou venv ativo $\rightarrow$ O script detecta e desativa o ambiente virtual localmente, baixa os 4 arquivos variantes (`.ttf`) da Atkinson Hyperlegible, atualiza o cache (`fc-cache`) e injeta os comandos `gsettings set` no sistema real, alterando as fontes da interface para o tamanho 12 instantaneamente.
* **Cenário 2 (Tratamento de Erro - Sem Internet):** Executar o script sem conexão à internet $\rightarrow$ O script identifica a falha na requisição de download (`curl` com flag `--fail`), aborta a instalação de forma segura antes de modificar o sistema e exibe uma mensagem de erro clara, sem corromper as configurações vigentes do usuário.
* **Cenário 3 (Validação Falha - Escopo de Sistema):** Executar o script em uma distribuição não baseada em Debian/Ubuntu ou sem suporte ao banco de dados `dconf/gsettings` $\rightarrow$ O script falha ao tentar aplicar as chaves de interface da Canonical/GNOME, garantindo que o sistema operacional não sofra inconsistências visuais e notificando o usuário sobre a incompatibilidade.

## História 2: Reverter alterações e restaurar fontes padrão do sistema
* **Cenário 1 (Remoção e Reset com Sucesso):** Executar o script de reversão $\rightarrow$ O script limpa o isolamento de ambientes virtuais, executa o comando `gsettings reset` para as chaves de interface, documentos e monospace (fazendo o Ubuntu voltar ao visual original nativo na hora), deleta fisicamente a pasta `atkinson_hyperlegible` do disco e atualiza o cache de fontes do sistema para garantir lixo zero absoluto.
* **Cenário 2 (Diretório Inexistente / Sistema já Limpo):** Executar a reversão em um sistema onde a fonte nunca foi instalada ou já foi removida $\rightarrow$ O comando `rm -rf` lida de forma silenciosa com o diretório ausente, o `gsettings reset` garante que as chaves estejam em modo padrão e o script encerra informando o sucesso da operação sem disparar falhas ou travar o terminal.

## História 3: Alternar o áudio do sistema para o modo Mono
* **Cenário 1 (Mudança de Perfil Ativa):** Executar o script com o servidor de áudio Pipewire ativo $\rightarrow$ Os canais de áudio esquerdo e direito são mapeados para Mono com sucesso através dos comandos de controle de canais.
* **Cenário 2 (Servidor de Áudio Ausente):** Executar o script em um servidor headless ou sem subsistema de som configurado $\rightarrow$ O script falha graciosamente notificando que o gerenciador de áudio não foi encontrado, finalizando com código de erro seguro.

## História 4: Customizar o tamanho geral das fontes por linha de comando
* **Cenário 1 (Argumento Válido):** Executar o script passando o parâmetro numérico fixo `12` $\rightarrow$ O sistema atualiza o nome e o tamanho nominal da fonte para `Atkinson Hyperlegible 12` mantendo o fator de escala em `1.0`, impedindo o comportamento de invasão/corte de caixas de texto que ocorre em escalas fracionadas.
* **Cenário 2 (Argumento Inválido/Campo Vazio):** Passar uma string de texto, caracteres especiais ou nenhum valor como parâmetro $\rightarrow$ O script aplica uma validação de tipo por expressão regular, rejeita a entrada malformada por segurança e mantém o tamanho 12 padrão estável sem alterar o sistema do usuário.

## História 5: Aplicar CSS customizado para botões e barras de títulos maiores
* **Cenário 1 (Injeção de Estilo):** Aplicar o patch CSS na estrutura do front-end do LinuxToys $\rightarrow$ Os elementos visuais recebem a folha de estilo injetada e aumentam a área útil de clique e leitura conforme o padding especificado.
* **Cenário 2 (Incompatibilidade de Elemento):** Executar a injeção em um cenário onde o arquivo de layout original foi modificado ou está ausente $\rightarrow$ O validador interrompe a aplicação do patch para não quebrar a estrutura visual da página e emite um alerta de integridade.