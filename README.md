# 🔧 openshift-cli-installer

Script automatizado em Python para instalar os CLIs `oc`, `kubectl` e `argocd` no Fedora, com suporte completo a **autocompletion**, aliases personalizados e configuração de ambiente.

📚 Baseado na [documentação oficial da Red Hat](https://docs.redhat.com/en/documentation/openshift_container_platform/4.8/html/cli_tools/openshift-cli-oc) e nas práticas recomendadas de instalação dos binários do Kubernetes e Argo CD.

---

## ✅ Funcionalidades

- Instalação automatizada de:
  - `oc` (OpenShift CLI) – versão definida no script
  - `kubectl` – última versão estável
  - `argocd` – última versão disponível via GitHub
- Autocompletion para `bash` e `zsh`, com verificação de duplicidade
- Criação de aliases personalizados:
  - `oc-login`: login no cluster com `oc`
  - `skopeo-login`: login no registry com token (`oc whoami -t`)

---

## 📦 Requisitos

- Fedora 38 ou superior
- Python 3.x
- Dependências: `curl`, `tar`, `sudo`, `dnf`, `python3`, `jq` (para debug)
- Internet para download dos binários

---

## 🚀 Como usar

```bash
python3 install_oc_kubectl_argocd.py

Durante a execução, serão solicitadas informações de login para criação dos aliases.

---

## 📁 Estrutura

- `install_oc.py`: script principal de instalação e configuração
- `create_oc_aliases.py`: gerado e executado automaticamente ao final, adiciona aliases em `~/.zsh_aliases` e `~/.bash_aliases`

---

## 🧪 Exemplo de uso pós-instalação

```bash
source ~/.zsh_aliases   # ou ~/.bash_aliases
source ~/.zshrc         # ou ~/.bashrc
oc-login                # Executa login no cluster
skopeo-login            # Executa login no registry com token
```

---

## 📍 Observações

- O caminho padrão de instalação do OC é `~/.local/bin`
- Certifique-se de que esse caminho está no seu `PATH`
