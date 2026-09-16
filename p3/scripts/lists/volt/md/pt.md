Painel de controle para jogos Vulkan no Linux. As configurações são aplicadas pelo volt, uma camada Vulkan implícita escrita em Rust, portanto funcionam com qualquer driver.

São 21 configurações distribuídas em 5 abas. Todas usam `default` como valor padrão, o que mantém a escolha feita pelo próprio jogo. Um perfil com todas as opções definidas como padrão não altera nada.

| Aba             | Seção         | Quantidade | Abrange                                                                |
| --------------- | ------------- | ---------: | ---------------------------------------------------------------------- |
| GPU             | `[gpu]`       |          1 | qual dispositivo o jogo enxerga                                        |
| Tela            | `[display]`   |          4 | modo de apresentação, quantidade de imagens, composição, recorte       |
| Texturas        | `[textures]`  |          7 | filtragem, mipmaps, anisotropia, LOD                                   |
| Renderização    | `[rendering]` |          4 | sombreamento por amostra, alpha to coverage, alpha to one, depth clamp |
| Taxa de quadros | `[framerate]` |          5 | limite, offset, cadência, método, pacing                               |

A maioria das listas de opções é obtida diretamente do seu hardware, em vez de vir de uma tabela no volt-gui. Modos de apresentação, quantidades de imagens, modos alpha, nomes das GPUs, anisotropia, níveis de mipmap e viés de LOD são todos obtidos por meio de uma sondagem do seu próprio dispositivo. Se o seu hardware não oferecer suporte a uma determinada configuração, ela terá apenas a opção `default`.

Listas fixas são usadas quando não há nada a ser consultado. `nearest` e `linear` fazem parte do núcleo do Vulkan e não possuem uma consulta correspondente. As configurações de taxa de quadros também não têm nada a consultar, já que um jogo nunca informa ao Vulkan qual taxa de quadros deseja usar.

As configurações são lidas uma única vez quando o jogo é iniciado. Pressione Aplicar e, em seguida, reinicie o jogo.

Use com:

```
volt -- ./game
```

ou nas opções de inicialização da Steam:

```
volt -- %command%
```
