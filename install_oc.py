#!/usr/bin/env python3

import os
import subprocess
import urllib.request
from pathlib import Path
import tarfile

OC_VERSION = "4.8.0"
DEST_DIR = str(Path.home() / ".local/bin")
OC_TARBALL_URL = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{OC_VERSION}/openshift-client-linux.tar.gz"

def run(cmd):
    print(f"🚀 Executando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def download_and_extract():
    print("📥 Baixando e extraindo OC CLI...")
    tmp_tar = "/tmp/oc.tar.gz"
    urllib.request.urlretrieve(OC_TARBALL_URL, tmp_tar)

    with tarfile.open(tmp_tar, "r:gz") as tar:
        tar.extractall(path=DEST_DIR)
    print(f"✅ Extraído para: {DEST_DIR}")

def add_to_path():
    print("🔧 Garantindo que ~/.local/bin esteja no PATH...")
    export_line = f'export PATH="$PATH:{DEST_DIR}"\n'
    bashrc = Path.home() / ".bashrc"
    zshrc = Path.home() / ".zshrc"

    for rc in [bashrc, zshrc]:
        if rc.exists() and export_line.strip() not in rc.read_text():
            with open(rc, "a") as f:
                f.write(f"\n{export_line}")
            print(f"✅ PATH atualizado em {rc.name}")

def setup_autocompletion():
    print("🔁 Configurando autocompletion...")
    completion_cmd = f"{DEST_DIR}/oc completion"
    if Path.home().joinpath(".zshrc").exists():
        with open(Path.home() / ".zshrc", "a") as f:
            f.write('\n# OpenShift CLI autocomplete\n')
            f.write('source <(oc completion zsh)\n')
    if Path.home().joinpath(".bashrc").exists():
        with open(Path.home() / ".bashrc", "a") as f:
            f.write('\n# OpenShift CLI autocomplete\n')
            f.write('source <(oc completion bash)\n')

def run_alias_script():
    print("🔗 Executando script de aliases personalizados...")
    alias_script_path = Path(__file__).parent / "create_oc_aliases.py"
    subprocess.run(["python3", str(alias_script_path)], check=True)

if __name__ == "__main__":
    Path(DEST_DIR).mkdir(parents=True, exist_ok=True)
 
    # Instalar dependências
    print("📦 Instalando dependências...")
    run("sudo dnf install -y skopeo")
    
    download_and_extract()
    add_to_path()
    setup_autocompletion()
    run_alias_script()
    print("\n✅ Instalação e configuração do OpenShift CLI concluídas com sucesso!")
