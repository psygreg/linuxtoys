**OptiScaler Client** é um utilitário moderno e de alto desempenho para desktop, desenvolvido para simplificar a instalação, o gerenciamento e a atualização do mod OptiScaler em toda a sua biblioteca de jogos. Desenvolvido com C# e Avalonia UI.

**Detecção de Jogos**

- **Verificação Automática de Múltiplas Plataformas** — Verifica automaticamente jogos da *Steam* e do *Heroic* (*Epic Games, GOG*).
- Verificação de Pastas Personalizadas — Adicione qualquer pasta como fonte de verificação para jogos sem DRM ou instalações independentes.
- Adição Manual de Jogos — Adicione jogos selecionando diretamente o arquivo executável.
- Filtragem de Unidades — Limite a verificação a unidades específicas.
- Exclusões Inteligentes — Exclusões pré-configuradas para entradas que não são jogos (por exemplo, *Wallpaper Engine* e *Steamworks Redistributables*).
- Obtenção de Capas — Obtém automaticamente as capas dos jogos pela *API da Steam* e pelo *SteamGridDB*, com armazenamento em cache local.

**Instalação e Desinstalação**

- Instalação / Desinstalação Rápida — Instale ou desinstale com um único clique para cada jogo, diretamente pela tela principal. Baixa automaticamente os componentes caso não estejam em cache.
- Instalação Automática — Detecta automaticamente a estrutura de diretórios dos jogos, incluindo estruturas de jogos *UE5/Phoenix*.
- Instalação Manual — Selecione manualmente o executável de destino para jogos com estruturas não convencionais.
- Instalação em Lote — Instale o OptiScaler em vários jogos de uma só vez, com filtragem por plataforma, seleção de componentes e aplicação de perfis.
- Seleção do Método de Injeção — Escolha o método de injeção de DLL: `dxgi.dll`, `winmm.dll`, `d3d12.dll`, `dbghelp.dll`, `version.dll`, `wininet.dll`, `winhttp.dll`.
- Backup e Restauração — Os arquivos originais dos jogos são copiados para backup antes da instalação e restaurados durante a desinstalação.

**Gerenciamento de Componentes**

- **OptiScaler** — Mod principal de upscaling, com canais de versões estáveis, beta e de desenvolvimento (nightly).
- *Fakenvapi* — Camada de compatibilidade para GPUs AMD/Intel, instalada junto com o OptiScaler quando necessário.
- *Nukem's DLSSG-to-FSR3* — Ponte de geração de quadros que converte o DLSS Frame Generation para FSR3.
- *FSR 4 DLL (Swap)* — Alterne entre versões INT8 e FP8 do FSR 4 ou simplesmente substitua os arquivos FSR 4 do jogo diretamente, sem instalar o OptiScaler. Permite importar versões personalizadas das DLLs do FSR 4.
- *OptiPatcher* — Carregador de plugins ASI, configurado automaticamente com `LoadAsiPlugins=true` no arquivo `OptiScaler.ini`.
- *DLSS Enabler* — Suporte opcional à geração de quadros (Frame Generation / Multi Frame Generation), baixado de um espelho não oficial, já que as versões oficiais estão disponíveis apenas no Nexus Mods.

**Perfis**

- **Perfis do OptiScaler** — Crie, edite, clone e gerencie perfis de configuração baseados em arquivos INI.
- Editor em Modo Simples — Interface simplificada com opções de ativar e desativar para configurações comuns.
- Editor em Modo Avançado — Editor completo de configurações organizadas por seções, com pesquisa e navegação pela barra lateral.
- Perfil Padrão — Defina um perfil padrão que será aplicado automaticamente durante a Instalação Rápida e a Instalação em Lote.
- Perfil Padrão Integrado — O perfil "OptiScaler Standard" já vem incluído com configurações padrão adequadas.
- Configuração Recomendada — Configurações recomendadas para cada jogo, obtidas da página de compatibilidade do OptiScaler e da lista Luma Unreal Engine, com seleção automática do método de injeção com base em dados da comunidade.
- **Atualização sem Reinstalação** — Ao alterar uma única configuração simples, é possível atualizar apenas o arquivo de configuração, sem precisar reinstalar tudo.
