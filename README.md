# openshift-cli-installer

Automação em Python para provisionar o _toolchain_ de OpenShift/Kubernetes no Fedora, com **autocompletion** (Bash/Zsh), **validação de integridade** (SHA256, quando disponível) e operações **multi-cluster** via um gerenciador de **perfis e aliases**.

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
  - **Containers** via DNF: `podman`, `buildah`, `skopeo`
- **Autocompletion** para **Bash** e **Zsh**, com geração de arquivos e _hook_ de carregamento
- **Hardening**
  - Seleção de artefato por arquitetura (`amd64`/`arm64`)
  - **SHA256** quando o fornecedor publica manifest
  - Extração **segura** (Python 3.13+) com bloqueio de _path traversal_ e links maliciosos
- **Multi-cluster / Aliases**
  - Perfis por cluster, _KUBECONFIG_ dedicado, logins seguros (senha/token), _helpers_ `kubectl` e rotinas para **registry interno** e **Argo CD**

---

## ✅ Requisitos

- Fedora 38+
- Python 3.10+
- Acesso à internet
- `sudo` (para instalar pacotes via `dnf` de forma opcional)

---

## 📁 Estrutura dos arquivos

```
.
├── install.py               # Instalador de CLIs + autocomplete + deps
└── manage_k8s_aliases.py    # Perfis multi-cluster e funções/aliases
```

> Instalação padrão dos binários em `~/.local/bin` (o instalador garante a inclusão no `PATH`).

---

## ⚙️ Parametrização (version pinning)

Defina versões via _env vars_ (ou use `latest`):

```bash
export OC_VERSION=latest \
       KUBECTL_VERSION=v1.34.1 \
       ARGOCD_VERSION=v3.1.5 \
       HELM_VERSION=latest \
       TKN_VERSION=latest \
       CLUSTERADM_VERSION=latest \
       ROXCTL_VERSION=latest
```

---

## 🚀 Instalação

```bash
python3 install.py
# (opcional) com as variáveis acima exportadas
```

Ao final, **abra um novo terminal** ou recarregue seu shell:

```bash
source ~/.zshrc   # ou: source ~/.bashrc
```

---

## 🔁 Smoke tests (pós-instalação)

```bash
# Presença no PATH
which oc kubectl argocd helm tkn clusteradm roxctl skopeo podman buildah

# Versões (cliente)
oc version --client
kubectl version --client
argocd version --client
helm version --short
tkn version
clusteradm version || clusteradm --help
roxctl version || roxctl --help
```

---

## 🧭 Operação Multi‑Cluster (manage_k8s_aliases.py)

O gerenciador cria **perfis** por cluster e gera funções/aliases:
- `use-kcfg-<perfil>` / `use-kcfg <perfil>` — exporta `KUBECONFIG` dedicado
- `oc-login-<perfil>` — login seguro (senha, via _prompt_)
- `oc-login-token-<perfil> [TOKEN]` — login via token (parâmetro/`$OCP_TOKEN`)
- `skopeo-login-internal-<perfil>` — login no **registry interno** via `oc whoami -t`
- `argocd-login-<perfil> [usuario]` — login no **Argo CD** (se configurado)
- _helpers_ `kubectl`: `k`, `kg`, `kga`, `kgp`, `kdp`, `klogs`, `kns`, `kctx`

### 1) Criar/atualizar perfis
```bash
python3 manage_k8s_aliases.py add
# Informe: nome do perfil (ex.: prod), API server, usuário, (in)secure TLS,
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

# Login seguro com senha
oc-login-prod           # solicitará a senha (sem eco)

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

- **Sem segredos persistidos**: senhas/tokens são solicitados no momento do uso.
- Uso de `--insecure-skip-tls-verify` é **por perfil** (evite em produção; prefira CA confiável).
- _Checksums_ são validados quando o fornecedor publica manifest; caso contrário, segue em **melhor esforço** com _logging_ explícito.

---

## 🔄 Atualização

Reexecute o instalador — ele é **idempotente**:
```bash
python3 install.py
```

Para perfis/aliases:
```bash
python3 manage_k8s_aliases.py add   # atualiza um perfil existente
python3 manage_k8s_aliases.py apply
```

---

## 🧹 Remoção (manual)

```bash
rm -f ~/.local/bin/{oc,kubectl,argocd,helm,tkn,clusteradm,roxctl}
# edite ~/.zsh_aliases e ~/.bash_aliases para remover o bloco entre sentinelas
```

---

## 📍 Notas

- Suporta `amd64` e `arm64` com seleção automática de artefatos.
- Binários são instalados em `~/.local/bin` e o instalador injeta `PATH="$HOME/.local/bin:$PATH"` no shell.
- Para ambientes **air‑gapped**, considere integrar `oc-mirror` e _registries_ internos.

---

## 📜 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` (se aplicável).
