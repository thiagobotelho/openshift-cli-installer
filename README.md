# 🔧 openshift-cli-installer

Script automatizado em Python para instalar o OpenShift CLI (`oc`) no Fedora, com suporte completo a autocompletion e criação de aliases personalizados.

📚 Baseado na [documentação oficial da Red Hat](https://docs.redhat.com/en/documentation/openshift_container_platform/4.8/html/cli_tools/openshift-cli-oc).

---

## ✅ Funcionalidades

- Instalação automatizada do `oc` na versão desejada
- Autocompletion para bash e zsh
- Criação de aliases personalizados:
  - `oc-login`: login no cluster com usuário/servidor
  - `skopeo-login`: login no registry com token do `oc whoami -t`

---

## 📦 Requisitos

- Fedora 38 ou superior
- Python 3.x
- curl, tar, sudo

---

## 🚀 Como usar

```bash
python3 install_oc.py
```

Durante a execução, serão solicitadas informações de login para criação dos aliases.

---

## 📁 Estrutura

- `install_oc.py`: script principal de instalação e configuração
- `create_oc_aliases.py`: gerado e executado automaticamente ao final, adiciona aliases em `~/.zsh_aliases` e `~/.bash_aliases`

---

## 🧪 Exemplo de uso pós-instalação

```bash
source ~/.zsh_aliases   # ou ~/.bash_aliases
oc-login                # Executa login no cluster
skopeo-login            # Executa login no registry com token
```

---

## 📍 Observações

- O caminho padrão de instalação do OC é `~/.local/bin`
- Certifique-se de que esse caminho está no seu `PATH`
