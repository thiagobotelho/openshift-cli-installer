#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

HOME = Path.home()
zsh_aliases = HOME / ".zsh_aliases"
bash_aliases = HOME / ".bash_aliases"

def get_input(prompt):
    return input(f"{prompt}: ").strip()

def append_alias(file_path, alias_line):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists() or alias_line not in file_path.read_text():
        with open(file_path, "a") as f:
            f.write(f"\n# Alias gerado automaticamente\n{alias_line}\n")
        print(f"✅ Alias adicionado em: {file_path}")
    else:
        print(f"ℹ️ Alias já existe em: {file_path}")

def main():
    print("🔐 Configurando alias para `oc login`")
    oc_user = get_input("Informe o usuário do OpenShift (ex: kubeadmin)")
    oc_server = get_input("Informe o servidor (ex: https://api.cluster:6443)")
    oc_alias = f'alias oc-login=\'oc login -u {oc_user} --server={oc_server}\''

    print("\n📦 Configurando alias para `skopeo login`")
    reg_user = get_input("Informe o usuário do registry")
    reg_server = get_input("Informe o registry (ex: registry.redhat.io)")
    skopeo_alias = f'alias skopeo-login=\'skopeo login -u {reg_user} -p "$(oc whoami -t)" {reg_server}\''

    for aliases_file in [zsh_aliases, bash_aliases]:
        append_alias(aliases_file, oc_alias)
        append_alias(aliases_file, skopeo_alias)

    print("\n🔁 Execute `source ~/.zsh_aliases` ou `source ~/.bash_aliases` para ativar os aliases.")

    print("\n🚀 Executando oc-login automaticamente...")
    subprocess.run("zsh", input=f"source {zsh_aliases}\noc-login\n", text=True, shell=True)

if __name__ == "__main__":
    main()
