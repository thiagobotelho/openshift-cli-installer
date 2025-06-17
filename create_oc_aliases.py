#!/usr/bin/env python3

import subprocess
from pathlib import Path

BASH_ALIASES = Path.home() / ".bash_aliases"
ZSH_ALIASES = Path.home() / ".zsh_aliases"

def prompt_oc_login():
    print("🔐 Configurando alias para oc login...")
    user = input("Informe o usuário do OpenShift: ").strip()
    server = input("Informe o endereço do servidor OpenShift: ").strip()
    alias_oc = f"alias oc-login='oc login -u {user} --server={server}'\n"
    return alias_oc

def prompt_skopeo_login():
    print("🔐 Configurando alias para skopeo login com token do oc...")
    registry = input("Informe o endereço do registro container (registry): ").strip()
    user = input("Informe o usuário do registro: ").strip()
    alias_skopeo = f"alias skopeo-login='skopeo login -u {user} -p "$(oc whoami -t)" {registry}'\n"
    return alias_skopeo

def append_aliases(alias_oc, alias_skopeo):
    for aliases_file in [BASH_ALIASES, ZSH_ALIASES]:
        with open(aliases_file, "a") as f:
            f.write("
# Aliases OpenShift
")
            f.write(alias_oc)
            f.write(alias_skopeo)
        print(f"✅ Aliases adicionados em: {aliases_file}")

if __name__ == "__main__":
    alias_oc = prompt_oc_login()
    alias_skopeo = prompt_skopeo_login()
    append_aliases(alias_oc, alias_skopeo)
    print("🎯 Finalizado. Reabra o terminal ou execute: source ~/.zsh_aliases ou ~/.bash_aliases")