# AGENTS.md — Regras para Contribuição no LinuxToys

## Sobre o Projeto

LinuxToys é uma coleção de ferramentas amigáveis para Linux. O repositório original fica em `psygreg/linuxtoys`. Nosso fork está em `pdl-clay/linuxtoys`.

---

## Regras de Contribuição

### Prioridades de Desenvolvimento (ordem de importância)

1. **Segurança e Privacidade primeiro** — Nunca implementar funcionalidades que comprometam dados ou segurança do usuário. Validar todos os inputs.
2. **Usabilidade e Acessibilidade** — Projetar para o usuário médio. Interfaces claras, descrições úteis, linguagem simples.
3. **Confiabilidade e Autossuficiência** — Tudo deve funcionar sem workarounds. Tratar casos extremos, mensagens de erro claras.
4. **Restrições CLI** — Interfaces de linha de comando só para menus de Desenvolvimento e Administração de Sistema.

### Fluxo de Trabalho

1. Sempre criar uma **feature branch** a partir de `master` atualizado
2. Seguir o estilo de código existente
3. Documentar novas funcionalidades ou mudanças significativas
4. Testar em container isolado (veja abaixo)
5. Enviar Pull Request com descrição clara das alterações

### Referências

- [Knowledge Base](https://github.com/psygreg/linuxtoys/wiki/Knowledge-Base)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [dev/README.md](dev/README.md)
- [dev/build/README.md](dev/build/README.md)
- [dev/libs/README.md](dev/libs/README.md)

---

## Testes em Container Isolado

**NUNCA teste scripts diretamente no sistema host.** Sempre usar container isolado.

### Pré-requisitos

```bash
# Docker
sudo apt install docker.io

# ou Podman
sudo apt install podman
```

### Testar scripts bash isoladamente

```bash
# Fedora (mais próximo do target principal)
docker run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c "cd /workspace && bash p3/scripts/SEU_SCRIPT.sh"

# ou com Podman
podman run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c "cd /workspace && bash p3/scripts/SEU_SCRIPT.sh"
```

### Testar a instalação completa

```bash
# Criar container Fedora e rodar install.sh
docker run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c "
  cd /workspace &&
  chmod +x install.sh &&
  ./install.sh
"
```

### Testar em múltiplas distros

```bash
# Fedora
docker run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c "cd /workspace && bash install.sh"

# Ubuntu
docker run --rm -it -v "$(pwd)":/workspace ubuntu:24.04 bash -c "cd /workspace && bash install.sh"

# Arch Linux
docker run --rm -it -v "$(pwd)":/workspace archlinux:latest bash -c "cd /workspace && bash install.sh"
```

### Verificar sintaxe de scripts

```bash
# Bash syntax check
bash -n p3/scripts/SEU_SCRIPT.sh
```

---

## Atualizar o Fork com o Repositório Original

Quando o usuário pedir para "fazer merge" ou "atualizar o fork", seguir este procedimento:

### Procedimento

```bash
# 1. Garantir que estamos no diretório do projeto
cd /home/pdl/Documentos/linuxtoys

# 2. Buscar alterações do upstream
git fetch upstream

# 3. Merge com upstream/master
git checkout master
git merge upstream/master

# 4. Resolver conflitos (se houver)
#    - Verificar arquivos conflitantes com: git status
#    - Editar arquivos e remover marcadores de conflito
#    - git add ARQUIVO_CONFLITANTE
#    - git commit -m "resolve merge conflict"

# 5. Push para o fork
git push origin master
```

### Regras importantes

- **Sempre usar `upstream/master`** como branch de origem
- Se houver conflito, aceitar a versão do upstream (repositório original) como padrão, a menos que o usuário especifique o contrário
- **Remover workflows do upstream** que não se aplicam ao fork (arquivos em `.github/workflows/` que usem secrets como `SCR_TOKEN` ou `PAT_TOKEN`)
- Após o push, informar ao usuário se houve conflitos e como foram resolvidos

### Workflows a remover ao sincronizar

Estes workflows são específicos do repositório original e não devem existir no fork:

- `.github/workflows/sync-scripts.yml` — Sincroniza com `psygreg/scripts`
- `.github/workflows/update-tools.yml` — Atualiza `psygreg/linuxtoys-site`

Para remover:
```bash
git rm .github/workflows/sync-scripts.yml .github/workflows/update-tools.yml
git commit -m "remove workflows that only apply to upstream repo"
```

---

## Estrutura do Projeto

```
linuxtoys/
├── .github/workflows/    # CI/CD (manter apenas workflows relevantes ao fork)
├── dev/                  # Código de desenvolvimento e build
├── p3/                   # Código principal da aplicação
│   ├── app/              # Interface (Python/Tkinter)
│   ├── libs/             # Bibliotecas compartilhadas
│   └── scripts/          # Scripts de instalação de ferramentas
├── resources/            # Ícones e recursos
├── src/                  # Scripts de compilação
├── install.sh            # Instalador principal
├── flake.nix             # Nix flake
└── shell.nix             # Shell Nix para desenvolvimento
```
