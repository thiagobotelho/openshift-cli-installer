#!/usr/bin/env python3

import os
import subprocess
import urllib.request
from pathlib import Path
import tarfile
import shutil
import json

DEST_DIR = str(Path.home() / ".local/bin")
os.environ["PATH"] += os.pathsep + DEST_DIR  # Atualiza PATH na execução do script

OC_VERSION = "4.8.0"
OC_URL = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{OC_VERSION}/openshift-client-linux.tar.gz"
KUBECTL_URL = "https://dl.k8s.io/release/stable.txt"
ARGOCD_URL = "https://api.github.com/repos/argoproj/argo-cd/releases/latest"

def run(cmd):
    print(f"🚀 Executando: {cmd}")
    subprocess.run(cmd, shell=True, check=True, env=os.environ)

def download_file(url, dest):
    print(f"📥 Baixando: {url}")
    urllib.request.urlretrieve(url, dest)

def extract_tar_gz(file_path, extract_to):
    print(f"📦 Extraindo: {file_path}")
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=extract_to)

def ensure_path():
    export_line = f'export PATH="$PATH:{DEST_DIR}"\n'
    for shell_rc in [".bashrc", ".zshrc"]:
        rc_path = Path.home() / shell_rc
        if rc_path.exists() and export_line.strip() not in rc_path.read_text():
            with open(rc_path, "a") as f:
                f.write(f"\n{export_line}")
            print(f"✅ PATH persistente atualizado em {rc_path.name}")

def install_oc():
    if shutil.which("oc"):
        print("🆗 oc já está instalado.")
        return

    tmp_file = "/tmp/oc.tar.gz"
    extract_dir = "/tmp/oc-extract"
    Path(extract_dir).mkdir(parents=True, exist_ok=True)

    download_file(OC_URL, tmp_file)
    extract_tar_gz(tmp_file, extract_dir)

    oc_src = Path(extract_dir) / "oc"
    kubectl_src = Path(extract_dir) / "kubectl"
    oc_dest = Path(DEST_DIR) / "oc"
    kubectl_dest = Path(DEST_DIR) / "kubectl"

    if oc_src.exists():
        if oc_dest.exists():
            oc_dest.unlink()
        shutil.move(str(oc_src), str(oc_dest))
        os.chmod(oc_dest, 0o755)
        print("✅ Binário 'oc' instalado.")

    if kubectl_src.exists():
        if kubectl_dest.exists():
            kubectl_dest.unlink()
        shutil.move(str(kubectl_src), str(kubectl_dest))
        os.chmod(kubectl_dest, 0o755)
        print("✅ Binário 'kubectl' instalado.")

def install_kubectl():
    if shutil.which("kubectl"):
        print("🆗 kubectl já está instalado.")
        return
    version = urllib.request.urlopen(KUBECTL_URL).read().decode().strip()
    url = f"https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl"
    dest = Path(DEST_DIR) / "kubectl"
    download_file(url, dest)
    os.chmod(dest, 0o755)

def install_argocd():
    if shutil.which("argocd"):
        print("🆗 argocd já está instalado.")
        return
    response = urllib.request.urlopen(ARGOCD_URL)
    data = json.loads(response.read())
    version = data["tag_name"]
    url = f"https://github.com/argoproj/argo-cd/releases/download/{version}/argocd-linux-amd64"
    dest = Path(DEST_DIR) / "argocd"
    download_file(url, dest)
    os.chmod(dest, 0o755)

def setup_autocompletion():
    print("🔁 Configurando autocompletion para oc, kubectl e argocd...")

    shells = {"bash": ".bashrc", "zsh": ".zshrc"}
    for cli in ["oc", "kubectl", "argocd"]:
        binary_path = Path(DEST_DIR) / cli
        if not binary_path.exists():
            print(f"⚠️  {cli} não encontrado, pulando autocomplete.")
            continue

        for shell, rc_file in shells.items():
            rc_path = Path.home() / rc_file
            if not rc_path.exists():
                continue

            line_to_add = f"source <({cli} completion {shell})"
            tag = f"# Autocomplete {cli}"
            content = rc_path.read_text()

            if line_to_add in content:
                print(f"🆗 Autocomplete de {cli} já configurado em {rc_file}.")
                continue

            with open(rc_path, "a") as f:
                f.write(f"\n{tag}\n{line_to_add}\n")
                print(f"✅ Autocomplete de {cli} adicionado em {rc_file}.")

def install_dependencies():
    print("📦 Instalando dependências de sistema...")
    run("sudo dnf install -y skopeo")

def run_alias_script():
    print("🔗 Executando script de aliases personalizados...")
    alias_script = Path(__file__).parent / "create_oc_aliases.py"
    if alias_script.exists():
        subprocess.run(["python3", str(alias_script)], check=True, env=os.environ)

def main():
    Path(DEST_DIR).mkdir(parents=True, exist_ok=True)
    install_dependencies()
    install_oc()
    install_kubectl()
    install_argocd()
    ensure_path()
    setup_autocompletion()
    run_alias_script()
    print(f"\n🔎 Verificação final: oc está em {shutil.which('oc')}")
    print("✅ Todas as ferramentas foram instaladas e configuradas com sucesso!")

if __name__ == "__main__":
    main()
