#!/usr/bin/env python3

import subprocess
from pathlib import Path
import socket

HOME = Path.home()
zsh_aliases = HOME / ".zsh_aliases"
bash_aliases = HOME / ".bash_aliases"

def get_input(prompt):
    return input(f"{prompt}: ").strip()

def remove_old_alias(file_path, alias_key):
    if not file_path.exists():
        return
    lines = file_path.read_text().splitlines()
    filtered = [line for line in lines if alias_key not in line]
    file_path.write_text("\n".join(filtered))

def append_alias(file_path, alias_line):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "a") as f:
        f.write(f"\n# Alias gerado automaticamente\n{alias_line}\n")
    print(f"✅ Alias adicionado em: {file_path}")

def check_oc_connectivity(server_url):
    import re
    from urllib.parse import urlparse

    parsed = urlparse(server_url)
    host = parsed.hostname or ""
    port = parsed.port or 6443  # default OpenShift API port
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except Exception:
        return False

def main():
    print("🔐 Configurando alias para `oc login`")
    oc_user = get_input("Informe o usuário do OpenShift (ex: kubeadmin)")
    oc_server = get_input("Informe o servidor (ex: https://api.cluster:6443)")
    oc_path = str(Path.home() / ".local/bin/oc")
    oc_alias = f'alias oc-login="{oc_path} login -u {oc_user} --server={oc_server} --insecure-skip-tls-verify=true"'

    print("\n📦 Configurando alias para `skopeo login`")
    reg_user = get_input("Informe o usuário do registry")
    reg_server = get_input("Informe o registry (ex: registry.redhat.io)")
    skopeo_alias = f'alias skopeo-login="skopeo login --tls-verify=false -u {reg_user} -p \\"$({oc_path} whoami -t)\\" {reg_server}"'

    for aliases_file in [zsh_aliases, bash_aliases]:
        remove_old_alias(aliases_file, "oc-login")
        remove_old_alias(aliases_file, "skopeo-login")
        append_alias(aliases_file, oc_alias)
        append_alias(aliases_file, skopeo_alias)

    print("\n🔁 Execute `source ~/.zsh_aliases` ou `source ~/.bash_aliases` para ativar os aliases.")

    print("\n🚀 Efetuando login direto no OpenShift...")

    if check_oc_connectivity(oc_server):
        subprocess.run(f'{oc_path} login -u {oc_user} --server={oc_server} --insecure-skip-tls-verify=true', shell=True)
    else:
        print("❌ Não foi possível conectar ao servidor. Verifique se o cluster está acessível.")

if __name__ == "__main__":
    main()
