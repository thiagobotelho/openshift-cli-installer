#!/usr/bin/env python3

import os
import subprocess
import urllib.request
from pathlib import Path
import tarfile
import shutil
import json

DEST_DIR = str(Path.home() / ".local/bin")
ZSH_COMPLETIONS_DIR = Path.home() / ".zsh/completions"
os.environ["PATH"] += os.pathsep + DEST_DIR

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

    for bin_name in ["oc", "kubectl"]:
        src = Path(extract_dir) / bin_name
        dest = Path(DEST_DIR) / bin_name
        if src.exists():
            if dest.exists():
                dest.unlink()
            shutil.move(str(src), str(dest))
            os.chmod(dest, 0o755)
            print(f"✅ Binário '{bin_name}' instalado.")

    shutil.rmtree(extract_dir, ignore_errors=True)
    os.remove(tmp_file)

def install_kubectl():
    if shutil.which("kubectl"):
        print("🆗 kubectl já está instalado.")
        return
    version = urllib.request.urlopen(KUBECTL_URL).read().decode().strip()
    url = f"https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl"
    dest = Path(DEST_DIR) / "kubectl"
    download_file(url, dest)
    os.chmod(dest, 0o755)
    print("✅ kubectl instalado.")

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
    print("✅ argocd instalado.")

def setup_autocompletion():
    print("🔁 Configurando autocompletion (Zsh)...")
    ZSH_COMPLETIONS_DIR.mkdir(parents=True, exist_ok=True)
    completions = {
        "oc": "oc completion zsh",
        "kubectl": "kubectl completion zsh",
        "argocd": "argocd completion zsh"
    }

    for cli, cmd in completions.items():
        bin_path = Path(DEST_DIR) / cli
        if not bin_path.exists():
            print(f"⚠️  {cli} não encontrado, pulando autocomplete.")
            continue
        dest_file = ZSH_COMPLETIONS_DIR / f"_{cli}"
        with open(dest_file, "w") as f:
            subprocess.run(cmd.split(), stdout=f, check=True, env=os.environ)
            print(f"✅ Completion de {cli} gerado em {dest_file}")

    # Adiciona fpath no .zshrc se necessário
    zshrc = Path.home() / ".zshrc"
    fpath_line = 'fpath=(~/.zsh/completions $fpath)'
    marker = "# Autocomplete completions"
    content = zshrc.read_text()
    if fpath_line not in content:
        with open(zshrc, "a") as f:
            f.write(f"\n{marker}\n{fpath_line}\nautoload -Uz compinit\ncompinit\n")
        print("✅ .zshrc atualizado com fpath e compinit.")
    else:
        print("🆗 fpath já configurado no .zshrc.")

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
