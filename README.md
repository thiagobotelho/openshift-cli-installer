# openshift-cli-installer

Automação em Python para provisionar o _toolchain_ de OpenShift/Kubernetes no Fedora, Ubuntu/Debian ou WSL, com **autocompletion** (Bash/Zsh), **validação de integridade** (SHA256, quando disponível) e operações **multi-cluster** via um gerenciador de **perfis e aliases**.

> Este pacote entrega **dois utilitários**:
> - `install.py` — instalador dos CLIs, autocomplete e dependências.
> - `manage_k8s_aliases.py` — gerenciador de **perfis multi‑cluster** e funções de login/uso no dia a dia.

---

## 📦 Escopo (CLIs e Configurações)

- **CLIs instalados e validados**
  - `oc` (OpenShift CLI)
  - `kubectl`
  - `argocd` (Argo CD CLI)
  - `helm`
  - `tkn` (Tekton / OpenShift Pipelines)
  - `clusteradm` (RHACM)
  - `roxctl` (ACS/StackRox)
  - `jq` e `yq` para processamento de JSON/YAML
  - **Containers** via DNF: `podman`, `buildah`, `skopeo`
- **Autocompletion** para **Bash** e **Zsh**, com geração de arquivos e _hook_ de carregamento
- **Hardening**
  - Seleção de artefato por arquitetura (`amd64`/`arm64`)
  - **SHA256** quando o fornecedor publica manifest
  - Extração **segura** (Python 3.13+) com bloqueio de _path traversal_ e links maliciosos
- **Multi-cluster / Aliases**
  - Perfis por cluster, _KUBECONFIG_ dedicado, login OAuth/token, _helpers_ `kubectl` e rotinas para **registry interno** e **Argo CD**

---

## ✅ Requisitos

- Fedora com `dnf`, ou Ubuntu/Debian com `apt-get`
- WSL 2 com uma dessas distribuições
- Python 3.10+
- Acesso à internet
- `sudo` (para instalar pacotes via `dnf` de forma opcional)

---

## 📁 Estrutura dos arquivos

```
.
├── install.py                  # Instalador de CLIs + autocomplete + deps
├── manage_k8s_aliases.py       # Perfis multi-cluster e funções/aliases
├── versions.lock.json          # Versões padrão reproduzíveis
├── tests/                      # Testes unitários
└── .github/workflows/          # Validação e releases por tag
```

> Instalação padrão dos binários em `~/.local/bin` (o instalador garante a inclusão no `PATH`).

---

## ⚙️ Versões reproduzíveis

Por padrão, as versões vêm de `versions.lock.json`. Para atualizar
deliberadamente para as versões mais recentes:

```bash
python3 install.py --latest
```

Variáveis de ambiente continuam disponíveis para override pontual:

Defina versões via _env vars_ (ou use `latest`):

```bash
export OC_VERSION=latest \
       KUBECTL_VERSION=v1.34.1 \
       ARGOCD_VERSION=v3.1.5 \
       HELM_VERSION=latest \
       TKN_VERSION=latest \
       CLUSTERADM_VERSION=latest \
       ROXCTL_VERSION=latest \
       YQ_VERSION=latest
```

Ordem de precedência: `--latest`, variável de ambiente, lockfile. O modo
`--latest` é deliberado e não modifica automaticamente o lockfile.

---

## 🚀 Instalação

```bash
python3 install.py

# Somente ferramentas selecionadas
python3 install.py --only oc kubectl helm

# Exibe o plano sem alterar o sistema
python3 install.py --dry-run

# Não instala dependências via dnf/apt
python3 install.py --skip-system-packages
```

Combinações são permitidas:

```bash
python3 install.py --only oc kubectl --skip-system-packages --dry-run
```

Ao final, **abra um novo terminal** ou recarregue seu shell:

```bash
source ~/.zshrc   # ou: source ~/.bashrc
```

---

## 🔁 Smoke tests (pós-instalação)

```bash
# Presença no PATH
which oc kubectl argocd helm tkn clusteradm roxctl skopeo podman buildah jq yq

# Versões (cliente)
oc version --client
kubectl version --client
argocd version --client
helm version --short
tkn version
clusteradm version || clusteradm --help
roxctl version || roxctl --help
jq --version
yq --version
```

---

## 🧭 Operação Multi‑Cluster (manage_k8s_aliases.py)

O gerenciador cria **perfis** por cluster e gera funções/aliases:
- `use-kcfg-<perfil>` / `use-kcfg <perfil>` — exporta `KUBECONFIG` dedicado
- `oc-login-<perfil>` — login OAuth pelo navegador, sem senha em argumentos
- `oc-login-token-<perfil> [TOKEN]` — login via token (parâmetro/`$OCP_TOKEN`)
- `skopeo-login-internal-<perfil>` — login no **registry interno** via `oc whoami -t`
- `argocd-login-<perfil> [usuario]` — login no **Argo CD** (se configurado)
- _helpers_ `kubectl`: `k`, `kg`, `kga`, `kgp`, `kdp`, `klogs`, `kns`, `kctx`

### 1) Criar/atualizar perfis
```bash
python3 manage_k8s_aliases.py add
# Informe: nome do perfil (ex.: prod), API server, (in)secure TLS,
# caminho do KUBECONFIG (ex.: ~/.kube/config-prod) e, opcionalmente, host do Argo CD.
```

### 2) Aplicar blocos (gerar funções + garantir sourcing)
```bash
python3 manage_k8s_aliases.py apply
source ~/.zsh_aliases   # ou: source ~/.bash_aliases
```

### 3) Administração de perfis
```bash
python3 manage_k8s_aliases.py list
python3 manage_k8s_aliases.py default <perfil>
python3 manage_k8s_aliases.py rm <perfil>
python3 manage_k8s_aliases.py check   # reachability TCP das APIs
```

### 4) Runbook diário (exemplos)
```bash
# Selecionar KUBECONFIG do perfil
use-kcfg-prod           # ou: use-kcfg prod

# Login seguro via navegador/OAuth
oc-login-prod

# Login por token
export OCP_TOKEN='<TOKEN>'
oc-login-token-prod     # ou: oc-login-token-prod <TOKEN>

# Registry interno do OpenShift (rota default)
skopeo-login-internal-prod

# Argo CD (se configurado no perfil)
argocd-login-prod [usuario=admin]

# Helpers kubectl
k       # kubectl
kgp -A  # kubectl get pods -A
kns my-namespace
kctx    # lista contexts / kctx <ctx> alterna
```

> O bloco gerado fica entre sentinelas em `~/.zsh_aliases` e `~/.bash_aliases`:
> ```
> # >>> k8s-aliases (managed) >>>
> ...
> # <<< k8s-aliases (managed) <<<
> ```

---

## 🧪 Testes com cluster (opcional)

```bash
oc whoami --show-server
kubectl config current-context
kubectl cluster-info
kubectl get ns
kubectl get pods -A --field-selector=status.phase!=Succeeded
helm repo add bitnami https://charts.bitnami.com/bitnami && helm repo update
tkn pipeline ls -n openshift-pipelines || true
clusteradm get clusters || true
```

---

## 🔐 Segurança

- **Sem segredos persistidos**: o fluxo padrão usa OAuth/browser.
- Tokens continuam opcionais para automação e não são gravados pelo
  gerenciador. Prefira o login web em estações interativas.
- Uso de `--insecure-skip-tls-verify` é **por perfil** (evite em produção; prefira CA confiável).
- _Checksums_ são validados quando o fornecedor publica manifest.
- `roxctl latest` falha de forma explícita se uma versão confiável não puder ser resolvida; não há fallback obsoleto silencioso.
- Arquivos de perfis e aliases gerenciados recebem permissão `0600`.
- Arquivos tar rejeitam links e tentativas de _path traversal_.

---

## 🔄 Atualização

Revise primeiro o plano e depois reexecute:
```bash
git pull --ff-only
python3 install.py --dry-run
python3 install.py
```

Para atualizar as versões padrão do projeto:

1. consulte as releases oficiais dos fornecedores;
2. altere `versions.lock.json`;
3. execute os testes e um dry-run;
4. instale apenas as ferramentas desejadas com `--only`.

Para perfis/aliases:
```bash
python3 manage_k8s_aliases.py add   # atualiza um perfil existente
python3 manage_k8s_aliases.py apply
```

---

## 🧹 Remoção (manual)

```bash
rm -f ~/.local/bin/{oc,kubectl,argocd,helm,tkn,clusteradm,roxctl,yq}
# edite ~/.zsh_aliases e ~/.bash_aliases para remover o bloco entre sentinelas
```

`jq`, `yq`, Podman, Buildah e Skopeo instalados pelo sistema devem ser
removidos com `dnf` ou `apt`, se desejado.

---

## 📍 Notas

- Suporta Linux nativo e WSL em `amd64` e `arm64`, com seleção automática de artefatos.
- Binários são instalados em `~/.local/bin` e o instalador injeta `PATH="$HOME/.local/bin:$PATH"` no shell.
- Para ambientes **air‑gapped**, considere integrar `oc-mirror` e _registries_ internos.

---

## 📜 Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

## 📚 Projeto

- Mudanças: [CHANGELOG.md](CHANGELOG.md)
- Contribuição: [CONTRIBUTING.md](CONTRIBUTING.md)
- Plataformas: [SUPPORT.md](SUPPORT.md)
