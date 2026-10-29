**LatencyDevil** é um wrapper de lançamento que considera a GPU para jogos competitivos. Ele envolve o comando de inicialização do jogo, injeta variáveis de ambiente que consideram a GPU (preferindo GPUs dedicadas) e depois faz `exec` do jogo — assim o wrapper nunca permanece na árvore de processos: o Steam continua acompanhando o jogo como filho direto.

**Como funciona**

- Toda execução envolvida recebe `PROTON_USE_WAYLAND=1`, `LOW_LATENCY_LAYER=1` e `SDL_VIDEO_DRIVER=wayland`.
- Com uma GPU NVIDIA presente, ele também habilita `LOW_LATENCY_LAYER_REFLEX=1` e define `DXVK_CONFIG` para esconder a GPU AMD do DXVK (`dxgi.hideAmdGpu = True`). Um `DXVK_CONFIG` existente é preservado: a diretiva da NVIDIA é anexada em uma linha separada.
- **Flatpak**: quando o comando envolvido começa com `flatpak run`, as variáveis são repassadas como argumentos `--env=KEY=VALUE`, porque sandboxes do Flatpak descartam variáveis de ambiente que não estão na lista de permissões.
- A detecção de GPU percorre os dispositivos de classe de exibição PCI em `/sys/bus/pci/devices`. Se nenhuma GPU for detectada (configurações incomuns de VM), o conjunto universal de variáveis é aplicado como fallback.

**Uso**

- Opções de lançamento do Steam: `latencydevil -- %command%`
- Terminal, funciona com qualquer comando (Flatpak incluído): `latencydevil -- flatpak run app.id` ou `latencydevil -- wine /caminho/do/jogo.exe`
- Depuração: `latencydevil --print` mostra as variáveis que seriam definidas e sai; `latencydevil --debug -- <comando>` também mostra a detecção de GPU, as variáveis aplicadas e a linha de exec.
