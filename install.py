#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import tarfile
import shutil
import hashlib
import platform
import tempfile
import subprocess
import urllib.request
from urllib.parse import urljoin
from pathlib import Path
from typing import Optional, List, Tuple

# =========================
# Configuração base
# =========================
DEST_DIR = str(Path.home() / ".local" / "bin")
os.environ["PATH"] += os.pathsep + DEST_DIR  # garante PATH em runtime

# Pinagens por ambiente (podem ser "latest" ou versões específicas)
OC_VERSION         = os.getenv("OC_VERSION", "latest")              # ex: "latest" ou "4.19.11"
KUBECTL_VERSION    = os.getenv("KUBECTL_VERSION", "latest")         # ex: "latest" ou "v1.34.1"
ARGOCD_VERSION     = os.getenv("ARGOCD_VERSION", "latest")          # ex: "latest" ou "v3.1.5"
HELM_VERSION       = os.getenv("HELM_VERSION", "latest")            # ex: "latest" ou "v3.15.3"
TKN_VERSION        = os.getenv("TKN_VERSION", "latest")             # ex: "latest" ou "v0.37.0"
CLUSTERADM_VERSION = os.getenv("CLUSTERADM_VERSION", "latest")      # ex: "latest" ou "v0.6.2"
ROXCTL_VERSION     = os.getenv("ROXCTL_VERSION", "latest")          # "latest" (mirror) ou versão específica do seu ACS

# =========================
# Utilitários
# =========================
def run(cmd: str):
    print(f"🚀 Executando: {cmd}")
    subprocess.run(cmd, shell=True, check=True, env=os.environ)

def download_file(url: str, dest_path: Path | str):
    dest_path = str(dest_path)
    print(f"📥 Baixando: {url}")
    urllib.request.urlretrieve(url, dest_path)

def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode()

def _sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _detect_arch() -> str:
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"):
        return "amd64"
    if m in ("aarch64", "arm64"):
        return "arm64"
    return "amd64"

def _safe_extract_tar_gz(file_path: Path, extract_to: Path):
    # Compatível com Python 3.13/3.14: filter(member, path)
    with tarfile.open(file_path, "r:gz") as tar:
        def _safe(member: tarfile.TarInfo, path):
            base = Path(path).resolve()
            target = (base / member.name).resolve()
            if not str(target).startswith(str(base)):
                raise Exception(f"Entrada suspeita no tar: {member.name}")
            if member.issym() or member.islnk():
                link_target = (base / (member.linkname or "")).resolve()
                if not str(link_target).startswith(str(base)):
                    raise Exception(f"Link suspeito fora do destino: {member.name} -> {member.linkname}")
            return member
        tar.extractall(path=extract_to, filter=_safe)

def _file_read_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""

def ensure_path_exports():
    export_line = 'export PATH="$HOME/.local/bin:$PATH"'
    for rc in [Path.home() / ".zshrc", Path.home() / ".bashrc"]:
        content = _file_read_text(rc)
        if export_line not in content:
            with open(rc, "a") as f:
                f.write("\n" + export_line + "\n")
            print(f"✅ PATH persistente atualizado em {rc.name}")
        else:
            print(f"🆗 PATH já presente em {rc.name}")

def _try_download_text(urls: List[str]) -> Optional[str]:
    for u in urls:
        try:
            print(f"📥 Tentando baixar: {u}")
            return _fetch_text(u)
        except Exception:
            continue
    return None

def _first_hex256(s: str) -> Optional[str]:
    m = re.search(r"\b[a-fA-F0-9]{64}\b", s)
    return m.group(0) if m else None

def _extract_checksum_for(chk_content: str, filename: str) -> Optional[str]:
    lines = [ln.strip() for ln in chk_content.splitlines() if ln.strip()]
    for ln in lines:
        if filename in ln:
            h = _first_hex256(ln)
            if h:
                return h
    if len(lines) == 1:
        return _first_hex256(lines[0])
    return None

def _roxctl_assets_version() -> str:
    """
    Resolve a versão de assets do RHACS para baixar o roxctl.
    Regras:
      1) Se ROXCTL_VERSION for 'X.Y.Z' (sem 'v'), usa direto.
      2) Se ROXCTL_VERSION começa com 'v', remove o 'v' e usa 'X.Y.Z'.
      3) Se for 'latest', varre páginas de doc conhecidas e extrai o primeiro assets/X.Y.Z/bin/Linux/roxctl.
      4) Fallbacks estáticos se nada for encontrado.
    """
    v = os.getenv("ROXCTL_VERSION", "latest").strip()
    # 1/2) versão explícita
    m = re.fullmatch(r"v?(\d+\.\d+\.\d+)", v)
    if m:
        return m.group(1)

    # 3) tentar extrair da doc (ordem do mais novo para o mais antigo)
    doc_tracks = [
        "4.8","4.7","4.6","4.5","4.4","4.3","4.2","4.1","4.0",
        "3.74","3.73","3.72","3.71","3.70","3.69",
    ]
    pat = re.compile(r"/rhacs/assets/(\d+\.\d+\.\d+)/bin/Linux/roxctl")
    for track in doc_tracks:
        url = f"https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_security_for_kubernetes/{track}/html/roxctl_cli/installing-the-roxctl-cli-1"
        try:
            html = _fetch_text(url)
            m = pat.search(html)
            if m:
                return m.group(1)
        except Exception:
            continue

    # 4) fallbacks conservadores (conhecidos na doc)
    return "4.4.8"  # fallback padrão; alternativos: "4.2.5", "3.71.3"

# =========================
# OC (OpenShift Client)
# =========================
def _oc_base_url(version: str) -> str:
    if version == "latest":
        return "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/"
    return f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{version}/"

def _select_oc_artifact(filenames: list[str], arch: str) -> str | None:
    """
    Seleciona o artefato OC correto para a arquitetura.
    Regras:
      - rejeita s390x/ppc64/ppc64le
      - prioriza:
         1) genérico 'openshift-client-linux.tar.gz' (apenas para amd64)
         2) arquivos que contenham tokens da nossa arch (amd64/x86_64 ou arm64/aarch64)
         3) versão mais nova (ordem lexicográfica)
    """
    bad_tokens = ("s390x", "ppc64le", "ppc64")
    arch_tokens = {
        "amd64": ("amd64", "x86_64"),
        "arm64": ("arm64", "aarch64"),
    }
    toks = arch_tokens.get(arch, ("amd64", "x86_64"))

    if arch == "amd64" and "openshift-client-linux.tar.gz" in filenames:
        return "openshift-client-linux.tar.gz"

    candidates = [f for f in filenames if f.startswith("openshift-client-linux") and f.endswith(".tar.gz")]
    candidates = [f for f in candidates if not any(bt in f.lower() for bt in bad_tokens)]

    arch_candidates = [f for f in candidates if any(t in f.lower() for t in toks)]
    if arch_candidates:
        arch_candidates.sort()
        return arch_candidates[-1]

    if arch == "amd64" and "openshift-client-linux.tar.gz" in candidates:
        return "openshift-client-linux.tar.gz"
    return None

def install_oc():
    def _oc_runs() -> bool:
        try:
            subprocess.check_output([str(Path(DEST_DIR) / "oc"), "version", "--client"],
                                    env=os.environ, stderr=subprocess.STDOUT)
            return True
        except OSError:
            return False
        except Exception:
            return False

    oc_path = Path(DEST_DIR) / "oc"
    if oc_path.exists():
        if _oc_runs():
            print(f"🆗 oc já está instalado em {oc_path}.")
            try:
                run("oc version --client")
            except Exception:
                pass
            return
        else:
            print("⚠️ 'oc' existente é incompatível (provável arquitetura incorreta). Removendo para reinstalar...")
            try:
                oc_path.unlink()
            except Exception as e:
                raise RuntimeError(f"❌ Não foi possível remover o 'oc' inválido: {e}")

    base = _oc_base_url(OC_VERSION)
    checksum_sources = [
        urljoin(base, "sha256sum.txt"),
        urljoin(base, "SHA256SUMS"),
        urljoin(base, "SHA256SUMS.txt"),
        urljoin(base, "openshift-client-linux.tar.gz.sha256"),
    ]
    chk_content = _try_download_text(checksum_sources)
    if not chk_content:
        raise RuntimeError("❌ Não foi possível obter os checksums para o OC.")

    lines = [l.strip() for l in chk_content.splitlines() if l.strip()]
    filename_to_hash: dict[str, str] = {}
    if len(lines) == 1 and " " not in lines[0]:
        filename_to_hash["openshift-client-linux.tar.gz"] = lines[0]
    else:
        for l in lines:
            parts = l.split()
            if len(parts) >= 2:
                h = parts[0]
                fname = parts[-1].lstrip("*")
                filename_to_hash[fname] = h

    arch = _detect_arch()
    artifact = _select_oc_artifact(list(filename_to_hash.keys()), arch)
    if not artifact:
        raise RuntimeError("❌ Não foi possível determinar o artefato OC correto para esta arquitetura.")

    expected = filename_to_hash.get(artifact)
    if not expected:
        raise RuntimeError("❌ Hash esperado não encontrado para o artefato OC selecionado.")

    oc_tgz_url = urljoin(base, artifact)
    with tempfile.TemporaryDirectory(prefix="oc-install-") as tmpd:
        tmpd = Path(tmpd)
        tgz = tmpd / artifact

        print(f"📥 Baixando OC de {oc_tgz_url}")
        download_file(oc_tgz_url, tgz)

        actual = _sha256sum(tgz)
        if actual != expected:
            print("ℹ️ Debug checksum:")
            print(f"   Artefato: {artifact}")
            print(f"   Esperado: {expected}")
            print(f"   Obtido  : {actual}")
            raise RuntimeError("❌ SHA256 inválido do pacote OC.")

        extract_dir = tmpd / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 Extraindo {tgz} → {extract_dir}")
        _safe_extract_tar_gz(tgz, extract_dir)

        oc_src = extract_dir / "oc"
        kubectl_src = extract_dir / "kubectl"
        oc_dest = Path(DEST_DIR) / "oc"
        kubectl_dest = Path(DEST_DIR) / "kubectl"

        if not oc_src.exists():
            raise FileNotFoundError("❌ Arquivo 'oc' não encontrado no pacote extraído.")

        oc_dest.parent.mkdir(parents=True, exist_ok=True)
        if oc_dest.exists():
            oc_dest.unlink()
        shutil.move(str(oc_src), str(oc_dest))
        os.chmod(oc_dest, 0o755)
        print(f"✅ 'oc' instalado em {oc_dest}")

        if kubectl_src.exists() and not shutil.which("kubectl"):
            if kubectl_dest.exists():
                kubectl_dest.unlink()
            shutil.move(str(kubectl_src), str(kubectl_dest))
            os.chmod(kubectl_dest, 0o755)
            print(f"✅ 'kubectl' (bundle OC) instalado em {kubectl_dest}")
        else:
            if shutil.which("kubectl"):
                print("🛈 kubectl já existente — não será sobrescrito.")
            else:
                print("⚠️ 'kubectl' não encontrado no pacote; seguirá instalação dedicada.")

    run("oc version --client")

# =========================
# kubectl
# =========================
def _kubectl_desired_version() -> str:
    if KUBECTL_VERSION.lower() == "latest":
        return _fetch_text("https://dl.k8s.io/release/stable.txt").strip()
    return KUBECTL_VERSION if KUBECTL_VERSION.startswith("v") else f"v{KUBECTL_VERSION}"

def _kubectl_current_version() -> Optional[str]:
    if not shutil.which("kubectl"):
        return None
    try:
        out = subprocess.check_output(
            ["kubectl", "version", "--client", "--output", "json"],
            env=os.environ, stderr=subprocess.STDOUT
        )
        data = json.loads(out.decode())
        return data.get("clientVersion", {}).get("gitVersion") or data.get("gitVersion")
    except Exception:
        return None

def install_kubectl():
    desired = _kubectl_desired_version()
    arch = _detect_arch()
    bin_url = f"https://dl.k8s.io/release/{desired}/bin/linux/{arch}/kubectl"
    sha_url = f"{bin_url}.sha256"

    current = _kubectl_current_version()
    if current == desired:
        print(f"🆗 kubectl já está na versão desejada ({current}).")
        return

    with tempfile.TemporaryDirectory(prefix="kubectl-install-") as tmpd:
        tmpd = Path(tmpd)
        bin_path = tmpd / "kubectl"
        sha_path = tmpd / "kubectl.sha256"

        print(f"📥 Baixando kubectl {desired} ({arch}) de {bin_url}")
        download_file(bin_url, bin_path)
        print(f"🔒 Baixando SHA256 de {sha_url}")
        download_file(sha_url, sha_path)

        expected = sha_path.read_text().split()[0].strip()
        actual = _sha256sum(bin_path)
        if actual != expected:
            raise RuntimeError(f"❌ SHA256 inválido do kubectl. Esperado {expected}, obtido {actual}")

        dest = Path(DEST_DIR) / "kubectl"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.move(str(bin_path), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ kubectl {desired} instalado em {dest}")

    run("kubectl version --client")

# =========================
# Argo CD CLI
# =========================
def _argocd_desired_version() -> str:
    if ARGOCD_VERSION.lower() == "latest":
        data = json.loads(_fetch_text("https://api.github.com/repos/argoproj/argo-cd/releases/latest"))
        return data["tag_name"]
    return ARGOCD_VERSION if ARGOCD_VERSION.startswith("v") else f"v{ARGOCD_VERSION}"

def _argocd_current_version() -> Optional[str]:
    if not shutil.which("argocd"):
        return None
    try:
        out = subprocess.check_output(["argocd", "version", "--client"], env=os.environ, stderr=subprocess.STDOUT)
        m = re.search(rb"v\d+\.\d+\.\d+", out)
        return m.group(0).decode() if m else None
    except Exception:
        return None

def _argocd_fetch_checksums_asset(desired_tag: str) -> Optional[tuple[str, str]]:
    try:
        api = f"https://api.github.com/repos/argoproj/argo-cd/releases/tags/{desired_tag}"
        data = json.loads(_fetch_text(api))
        for a in data.get("assets", []):
            name = a.get("name", "")
            url = a.get("browser_download_url", "")
            if re.search(r"(sha256|checksum)", name, re.IGNORECASE):
                return name, url
    except Exception:
        return None
    return None

def install_argocd():
    desired = _argocd_desired_version()
    arch = _detect_arch()
    filename = f"argocd-linux-{arch}"
    bin_url = f"https://github.com/argoproj/argo-cd/releases/download/{desired}/{filename}"

    current = _argocd_current_version()
    if current == desired:
        print(f"🆗 argocd já está na versão desejada ({current}).")
        return

    with tempfile.TemporaryDirectory(prefix="argocd-install-") as tmpd:
        tmpd = Path(tmpd)
        bin_path = tmpd / filename
        print(f"📥 Baixando Argo CD CLI {desired} ({arch}) de {bin_url}")
        download_file(bin_url, bin_path)

        checksum_sources = [
            f"https://github.com/argoproj/argo-cd/releases/download/{desired}/{filename}.sha256",
            f"https://github.com/argoproj/argo-cd/releases/download/{desired}/sha256sum.txt",
            f"https://github.com/argoproj/argo-cd/releases/download/{desired}/SHA256SUMS",
            f"https://github.com/argoproj/argo-cd/releases/download/{desired}/SHA256SUMS.txt",
        ]
        chk_content = _try_download_text(checksum_sources)
        if not chk_content:
            asset = _argocd_fetch_checksums_asset(desired)
            if asset:
                name, url = asset
                print(f"📥 Baixando checksums via asset do GitHub: {name}")
                chk_content = _fetch_text(url)

        if not chk_content:
            raise RuntimeError("❌ Não foi possível obter o checksum SHA256 para o Argo CD CLI.")

        expected = None
        lines = [l.strip() for l in chk_content.splitlines() if l.strip()]
        if len(lines) == 1 and " " not in lines[0]:
            expected = lines[0]
        else:
            for l in lines:
                if filename in l:
                    expected = l.split()[0]
                    break
            if not expected:
                for l in lines:
                    if "argocd-linux" in l and arch in l:
                        expected = l.split()[0]
                        break

        if not expected:
            raise RuntimeError("❌ Checksum não encontrado para o binário Argo CD alvo.")

        actual = _sha256sum(bin_path)
        if actual != expected:
            print("ℹ️ Debug checksum (argocd):")
            print(f"   Arquivo : {filename}")
            print(f"   Esperado: {expected}")
            print(f"   Obtido  : {actual}")
            raise RuntimeError(f"❌ SHA256 inválido do argocd.")

        dest = Path(DEST_DIR) / "argocd"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.move(str(bin_path), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ argocd {desired} instalado em {dest}")

    run("argocd version --client")

# =========================
# HELM
# =========================
def _helm_desired_version() -> str:
    if HELM_VERSION.lower() == "latest":
        data = json.loads(_fetch_text("https://api.github.com/repos/helm/helm/releases/latest"))
        return data["tag_name"]  # ex: v3.15.x
    return HELM_VERSION if HELM_VERSION.startswith("v") else f"v{HELM_VERSION}"

def install_helm():
    desired = _helm_desired_version()
    arch = _detect_arch()
    tar_name = f"helm-{desired}-linux-{arch}.tar.gz"
    base = f"https://get.helm.sh/"
    tar_url = urljoin(base, tar_name)

    # checksums: arquivo "helm-{version}-linux-{arch}.tar.gz.sha256sum" ou "helm-{version}-checksums.txt"
    checksum_sources = [
        urljoin(base, f"{tar_name}.sha256sum"),
        urljoin(base, f"helm-{desired}-checksums.txt"),
        urljoin(base, f"helm-{desired}-linux-{arch}.tar.gz.sha256"),
    ]
    chk_content = _try_download_text(checksum_sources)
    if not chk_content:
        raise RuntimeError("❌ Não foi possível obter checksums do Helm.")

    with tempfile.TemporaryDirectory(prefix="helm-install-") as tmpd:
        tmpd = Path(tmpd)
        tar_path = tmpd / tar_name
        print(f"📥 Baixando Helm {desired} ({arch}) de {tar_url}")
        download_file(tar_url, tar_path)

        # extrai hash esperado
        expected = None
        lines = [l.strip() for l in chk_content.splitlines() if l.strip()]
        if len(lines) == 1 and " " not in lines[0]:
            expected = lines[0]
        else:
            for l in lines:
                if tar_name in l:
                    expected = l.split()[0]
                    break
        if not expected:
            raise RuntimeError("❌ Checksum não encontrado para o tar do Helm.")

        actual = _sha256sum(tar_path)
        if actual != expected:
            print("ℹ️ Debug checksum (helm):")
            print(f"   Arquivo : {tar_name}")
            print(f"   Esperado: {expected}")
            print(f"   Obtido  : {actual}")
            raise RuntimeError("❌ SHA256 inválido do Helm.")

        extract_dir = tmpd / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 Extraindo {tar_path} → {extract_dir}")
        _safe_extract_tar_gz(tar_path, extract_dir)

        # binário está em linux-{arch}/helm
        helm_src = extract_dir / f"linux-{arch}" / "helm"
        if not helm_src.exists():
            raise FileNotFoundError("❌ Binário 'helm' não encontrado no pacote extraído.")
        dest = Path(DEST_DIR) / "helm"
        if dest.exists():
            dest.unlink()
        shutil.move(str(helm_src), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ helm {desired} instalado em {dest}")

    # valida
    run("helm version --short")

# =========================
# Tekton CLI (tkn)
# =========================
def _tkn_desired_version() -> str:
    if TKN_VERSION.lower() == "latest":
        data = json.loads(_fetch_text("https://api.github.com/repos/tektoncd/cli/releases/latest"))
        return data["tag_name"]
    return TKN_VERSION if TKN_VERSION.startswith("v") else f"v{TKN_VERSION}"

def install_tkn():
    desired = _tkn_desired_version()           # ex: v0.42.0
    ver = desired.lstrip("v")                  # ex: 0.42.0

    # Map correto de arquitetura para o naming do asset:
    arch = _detect_arch()                      # 'amd64' | 'arm64'
    tek_arch = "x86_64" if arch == "amd64" else "aarch64"

    tar_name = f"tkn_{ver}_Linux_{tek_arch}.tar.gz"
    base = f"https://github.com/tektoncd/cli/releases/download/{desired}/"
    tar_url = urljoin(base, tar_name)

    # checksums ficam em checksums.txt na mesma release
    checksum_sources = [
        urljoin(base, "checksums.txt"),
        urljoin(base, f"{tar_name}.sha256"),  # fallback se existir
    ]
    chk_content = _try_download_text(checksum_sources)
    if not chk_content:
        raise RuntimeError("❌ Não foi possível obter checksums do Tekton CLI (tkn).")

    with tempfile.TemporaryDirectory(prefix="tkn-install-") as tmpd:
        tmpd = Path(tmpd)
        tar_path = tmpd / tar_name
        print(f"📥 Baixando Tekton CLI {desired} ({tek_arch}) de {tar_url}")
        download_file(tar_url, tar_path)

        # Seleciona o hash esperado do arquivo certo
        expected = None
        for l in [ln.strip() for ln in chk_content.splitlines() if ln.strip()]:
            if tar_name in l:
                expected = l.split()[0]
                break
        if not expected and len(chk_content.splitlines()) == 1:
            expected = chk_content.strip()

        if not expected:
            raise RuntimeError("❌ Checksum não encontrado para o pacote tkn.")

        actual = _sha256sum(tar_path)
        if actual != expected:
            print("ℹ️ Debug checksum (tkn):")
            print(f"   Arquivo : {tar_name}")
            print(f"   Esperado: {expected}")
            print(f"   Obtido  : {actual}")
            raise RuntimeError("❌ SHA256 inválido do tkn.")

        extract_dir = tmpd / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 Extraindo {tar_path} → {extract_dir}")
        _safe_extract_tar_gz(tar_path, extract_dir)

        # binário 'tkn' pode estar na raiz ou dentro de subdir
        tkn_src = extract_dir / "tkn"
        if not tkn_src.exists():
            candidates = list(extract_dir.glob("**/tkn"))
            if not candidates:
                raise FileNotFoundError("❌ Binário 'tkn' não encontrado no pacote extraído.")
            tkn_src = candidates[0]

        dest = Path(DEST_DIR) / "tkn"
        if dest.exists():
            dest.unlink()
        shutil.move(str(tkn_src), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ tkn {desired} instalado em {dest}")

    run("tkn version")

# =========================
# clusteradm (RHACM)
# =========================
def _clusteradm_desired_version() -> str:
    if CLUSTERADM_VERSION.lower() == "latest":
        data = json.loads(_fetch_text("https://api.github.com/repos/open-cluster-management-io/clusteradm/releases/latest"))
        return data["tag_name"]
    return CLUSTERADM_VERSION if CLUSTERADM_VERSION.startswith("v") else f"v{CLUSTERADM_VERSION}"

def _clusteradm_find_assets(tag: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Descobre o tarball e o asset de checksums pela API do GitHub.
    Retorna (tar_name, checksums_url) — qualquer um pode ser None.
    """
    api = f"https://api.github.com/repos/open-cluster-management-io/clusteradm/releases/tags/{tag}"
    data = json.loads(_fetch_text(api))

    goarch = "amd64" if arch == "amd64" else "arm64"
    # padrões possíveis observados
    tar_candidates = [
        f"clusteradm_linux_{goarch}.tar.gz",
        f"clusteradm-linux-{goarch}.tar.gz",
    ]

    tar_name = None
    checksums_url = None
    for a in data.get("assets", []):
        name = a.get("name", "")
        url  = a.get("browser_download_url", "")
        # acha tarball
        if not tar_name and any(name == cand for cand in tar_candidates):
            tar_name = name
        # acha checksums
        if not checksums_url and re.search(r"(sha256|checksum)", name, re.IGNORECASE):
            checksums_url = url

    return tar_name, checksums_url

def install_clusteradm():
    desired = _clusteradm_desired_version()
    arch = _detect_arch()
    tar_name, checksums_url = _clusteradm_find_assets(desired, arch)
    base = f"https://github.com/open-cluster-management-io/clusteradm/releases/download/{desired}/"

    if not tar_name:
        # fallback: tenta o nome mais comum
        goarch = "amd64" if arch == "amd64" else "arm64"
        tar_name = f"clusteradm_linux_{goarch}.tar.gz"
    tar_url = urljoin(base, tar_name)

    # Tenta obter checksums (via asset → preferencial; depois fallbacks diretos)
    chk_content = None
    if checksums_url:
        print(f"📥 Baixando checksums via asset do GitHub: {checksums_url.split('/')[-1]}")
        try:
            chk_content = _fetch_text(checksums_url)
        except Exception:
            chk_content = None
    if not chk_content:
        chk_content = _try_download_text([
            urljoin(base, "checksums.txt"),
            urljoin(base, f"{tar_name}.sha256"),
            urljoin(base, "SHA256SUMS"),
            urljoin(base, "sha256sum.txt"),
        ])

    with tempfile.TemporaryDirectory(prefix="clusteradm-install-") as tmpd:
        tmpd = Path(tmpd)
        tar_path = tmpd / tar_name
        print(f"📥 Baixando clusteradm {desired} ({arch}) de {tar_url}")
        download_file(tar_url, tar_path)

        # Validação (melhor esforço): usa checksum se disponível
        if chk_content:
            expected = _extract_checksum_for(chk_content, tar_name)
            if expected:
                actual = _sha256sum(tar_path)
                if actual != expected:
                    print("ℹ️ Debug checksum (clusteradm):")
                    print(f"   Arquivo : {tar_name}")
                    print(f"   Esperado: {expected}")
                    print(f"   Obtido  : {actual}")
                    raise RuntimeError("❌ SHA256 inválido do clusteradm.")
            else:
                print("⚠️ Manifest de checksums encontrado, mas não há linha correspondente ao tarball — prosseguindo sem validar.")
        else:
            print("⚠️ Checksums do clusteradm não publicados/indisponíveis — prosseguindo sem validar (melhor esforço).")

        extract_dir = tmpd / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 Extraindo {tar_path} → {extract_dir}")
        _safe_extract_tar_gz(tar_path, extract_dir)

        src = next(iter(extract_dir.glob("**/clusteradm")), None)
        if not src:
            raise FileNotFoundError("❌ Binário 'clusteradm' não encontrado no pacote extraído.")

        dest = Path(DEST_DIR) / "clusteradm"
        if dest.exists():
            dest.unlink()
        shutil.move(str(src), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ clusteradm {desired} instalado em {dest}")

    # versão pode não existir em algumas builds — usa help como fallback
    run("clusteradm version || clusteradm --help")

# =========================
# roxctl (ACS)
# =========================
def _roxctl_urls(arch: str) -> Tuple[str, Optional[str]]:
    # Mirror oficial RHACS; nomes de asset costumam ser 'roxctl-linux' + '.sha256'
    base = f"https://mirror.openshift.com/pub/rhacs/{'x86_64' if arch=='amd64' else arch}/"
    bin_url = urljoin(base, "roxctl-linux")
    sha_url = urljoin(base, "roxctl-linux.sha256")
    return bin_url, sha_url

def install_roxctl():
    arch = _detect_arch()  # não influencia o path (Linux/roxctl), mas mantemos para logs
    assets_ver = _roxctl_assets_version()
    base = f"https://mirror.openshift.com/pub/rhacs/assets/{assets_ver}/bin/Linux/"
    bin_url = urljoin(base, "roxctl")

    with tempfile.TemporaryDirectory(prefix="roxctl-install-") as tmpd:
        tmpd = Path(tmpd)
        bin_path = tmpd / "roxctl"
        print(f"📥 Baixando roxctl {assets_ver} ({arch}) de {bin_url}")
        download_file(bin_url, bin_path)

        # Tentativas de checksum (melhor esforço)
        checksum_sources = [
            urljoin(base, "sha256sum.txt"),
            urljoin(base, "SHA256SUMS"),
            urljoin(base, "SHA256SUMS.txt"),
            urljoin(base, "roxctl.sha256"),
        ]
        chk_content = _try_download_text(checksum_sources)

        if chk_content:
            # procura hash na linha do arquivo 'roxctl' ou pega o primeiro hash válido
            expected = _extract_checksum_for(chk_content, "roxctl") if "_extract_checksum_for" in globals() else None
            if not expected:
                # fallback: primeiro hex de 64 chars na lista
                m = re.search(r"\b[a-fA-F0-9]{64}\b", chk_content)
                expected = m.group(0) if m else None

            if expected:
                actual = _sha256sum(bin_path)
                if actual != expected:
                    print("ℹ️ Debug checksum (roxctl):")
                    print(f"   Esperado: {expected}")
                    print(f"   Obtido  : {actual}")
                    raise RuntimeError("❌ SHA256 inválido do roxctl.")
            else:
                print("⚠️ Manifest de checksums disponível, mas sem hash correlato — prosseguindo sem validar.")
        else:
            print("⚠️ Checksums do roxctl indisponíveis — prosseguindo sem validar (melhor esforço).")

        dest = Path(DEST_DIR) / "roxctl"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.move(str(bin_path), str(dest))
        os.chmod(dest, 0o755)
        print(f"✅ roxctl {assets_ver} instalado em {dest}")

    # Validação básica
    try:
        run("roxctl version")
    except subprocess.CalledProcessError:
        print("⚠️ roxctl instalado; versão não pôde ser exibida (sem endpoint). Use 'roxctl --help' para smoke test.")

# =========================
# Autocomplete Zsh e Bash
# =========================
def setup_autocompletion():
    print("🔁 Configurando autocompletion para Zsh e Bash...")
    completions_dir = Path.home() / ".zsh" / "completions"
    completions_dir.mkdir(parents=True, exist_ok=True)

    completions_cmds = {
        "oc": "oc completion zsh",
        "kubectl": "kubectl completion zsh",
        "argocd": "argocd completion zsh",
        "skopeo": "skopeo completion zsh",
        "helm": "helm completion zsh",
        "tkn": "tkn completion zsh",
        "clusteradm": "clusteradm completion zsh",
        "roxctl": "roxctl completion zsh",
    }
    for cli, cmd in completions_cmds.items():
        cli_path = Path(DEST_DIR) / cli
        if not cli_path.exists() and shutil.which(cli) is None:
            print(f"⚠️  {cli} não encontrado, pulando autocomplete Zsh.")
            continue
        target = completions_dir / f"_{cli}"
        try:
            with open(target, "w") as f:
                subprocess.run(cmd.split(), stdout=f, check=True, env=os.environ)
            print(f"✅ Completion Zsh de {cli} gerado em {target}")
        except OSError:
            print(f"⚠️  {cli} incompatível/executável inválido. Pulando completion.")
        except subprocess.CalledProcessError:
            print(f"⚠️  Falha ao gerar completion de {cli}. Pulando.")

    # Zshrc hooks
    zshrc = Path.home() / ".zshrc"
    zsh_lines = [
        'export PATH="$HOME/.local/bin:$PATH"',
        'fpath=(~/.zsh/completions $fpath)',
        'autoload -Uz compinit',
        'compinit',
        'autoload -Uz _oc', 'compdef _oc oc',
        'autoload -Uz _kubectl', 'compdef _kubectl kubectl',
        'autoload -Uz _argocd', 'compdef _argocd argocd',
        'autoload -Uz _skopeo', 'compdef _skopeo skopeo',
        'autoload -Uz _helm', 'compdef _helm helm',
        'autoload -Uz _tkn', 'compdef _tkn tkn',
        'autoload -Uz _clusteradm', 'compdef _clusteradm clusteradm',
        'autoload -Uz _roxctl', 'compdef _roxctl roxctl',
    ]
    content_zsh = _file_read_text(zshrc)
    for line in zsh_lines:
        if line not in content_zsh:
            with open(zshrc, "a") as f:
                f.write("\n" + line)
            print(f"✅ Adicionado ao .zshrc: {line}")
        else:
            print(f"🆗 Já presente no .zshrc: {line}")

    # Bash
    bashrc = Path.home() / ".bashrc"
    bash_lines = [
        'export PATH="$HOME/.local/bin:$PATH"',
        'source <(oc completion bash)',
        'source <(kubectl completion bash)',
        'source <(argocd completion bash)',
        'source <(skopeo completion bash)',
        'source <(helm completion bash)',
        'source <(tkn completion bash)',
        'source <(clusteradm completion bash)',
        'source <(roxctl completion bash)',
    ]
    content_bash = _file_read_text(bashrc)
    for line in bash_lines:
        if line not in content_bash:
            with open(bashrc, "a") as f:
                f.write("\n" + line)
            print(f"✅ Adicionado ao .bashrc: {line}")
        else:
            print(f"🆗 Já presente no .bashrc: {line}")

# =========================
# Dependências opcionais (Fedora)
# =========================
def install_dependencies():
    try:
        print("📦 Instalando dependências de sistema (opcional)...")
        run("sudo dnf -y install zsh podman buildah skopeo || true")
    except Exception:
        print("🛈 Skipping dependências (não críticas).")

# =========================
# Main
# =========================
def main():
    Path(DEST_DIR).mkdir(parents=True, exist_ok=True)
    install_dependencies()
    ensure_path_exports()
    install_oc()
    install_kubectl()
    install_argocd()
    install_helm()
    install_tkn()
    install_clusteradm()
    install_roxctl()
    setup_autocompletion()

    print(f"\n🔎 Verificação final:")
    print(f" - oc:         {shutil.which('oc')}")
    print(f" - kubectl:    {shutil.which('kubectl')}")
    print(f" - argocd:     {shutil.which('argocd')}")
    print(f" - helm:       {shutil.which('helm')}")
    print(f" - tkn:        {shutil.which('tkn')}")
    print(f" - clusteradm: {shutil.which('clusteradm')}")
    print(f" - roxctl:     {shutil.which('roxctl')}")
    print("✅ Ferramentas instaladas e autocomplete configurado. Abra um novo terminal ou rode `source ~/.zshrc`/`source ~/.bashrc`.")

if __name__ == "__main__":
    main()
