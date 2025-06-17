#!/usr/bin/env python3

import os
import shutil
import subprocess
from pathlib import Path
import urllib.request
import tarfile

OC_VERSION = "4.14.9"
BASE_URL = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{OC_VERSION}/openshift-client-linux-{OC_VERSION}.tar.gz"
DEST_DIR = Path.home() / ".local/bin"
BASH_COMPLETION_PATH = "/etc/bash_completion.d/oc"
ZSH_COMPLETION_PATH = Path.home() / ".oh-my-zsh/completions/_oc"

def run(cmd: str):
    print(f"⚙️ Executando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def download_and_extract():
    print("⬇️ Baixando oc...")
    os.makedirs("tmp_oc", exist_ok=True)
    tar_path = "tmp_oc/oc.tar.gz"
    urllib.request.urlretrieve(BASE_URL, tar_path)
    with tarfile.open(tar_path) as tar:
        tar.extractall(path="tmp_oc")

def install_oc():
    print("📦 Instalando oc no diretório local...")
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy("tmp_oc/oc", DEST_DIR / "oc")
    shutil.copy("tmp_oc/kubectl", DEST_DIR / "kubectl")
    run(f"chmod +x {DEST_DIR}/oc {DEST_DIR}/kubectl")

def configure_path():
    bashrc = Path.home() / ".bashrc"
    zshrc = Path.home() / ".zshrc"
    export_line = f'export PATH="$PATH:{DEST_DIR}"\n'
    for rc in [bashrc, zshrc]:
        if rc.exists() and export_line.strip() not in rc.read_text():
            with open(rc, "a") as f:
                f.write(f"
{export_line}")

def configure_completion():
    print("🔁 Configurando autocompletion...")
    run(f"{DEST_DIR}/oc completion bash | sudo tee {BASH_COMPLETION_PATH} > /dev/null")
    run(f"{DEST_DIR}/oc completion zsh > {ZSH_COMPLETION_PATH}")
    print("✅ Autocompletion configurado.")

if __name__ == "__main__":
    download_and_extract()
    install_oc()
    configure_path()
    configure_completion()
    print("🎉 Instalação finalizada com sucesso.")

# ✅ Geração de aliases personalizados para oc e skopeo
print("\n🔗 Executando script de aliases personalizados para oc e skopeo...")
alias_script_url = "https://raw.githubusercontent.com/thiagobotelho/openshift-cli-installer/main/create_oc_aliases.py"
alias_script_path = "/tmp/create_oc_aliases.py"
urllib.request.urlretrieve(alias_script_url, alias_script_path)
subprocess.run(["python3", alias_script_path], check=True)
