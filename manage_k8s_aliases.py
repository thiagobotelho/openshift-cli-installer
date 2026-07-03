#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import socket
import sys
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

HOME = Path.home()
ZSH_ALIASES = HOME / ".zsh_aliases"
BASH_ALIASES = HOME / ".bash_aliases"
ZSHRC = HOME / ".zshrc"
BASHRC = HOME / ".bashrc"

CONF_DIR = HOME / ".config" / "k8s-aliases"
CONF_DIR.mkdir(parents=True, exist_ok=True)
CONF_FILE = CONF_DIR / "profiles.json"

SENTINEL_BEGIN = "# >>> k8s-aliases (managed) >>>"
SENTINEL_END   = "# <<< k8s-aliases (managed) <<<"

def load_profiles() -> Dict[str, Any]:
    if CONF_FILE.exists():
        try:
            return json.loads(CONF_FILE.read_text())
        except Exception:
            pass
    return {"default": None, "profiles": {}}

def save_profiles(cfg: Dict[str, Any]):
    CONF_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    CONF_FILE.chmod(0o600)

def ensure_rc_sources():
    for rc, al in [(ZSHRC, ZSH_ALIASES), (BASHRC, BASH_ALIASES)]:
        line = f'[ -f "{al}" ] && source "{al}"'
        content = rc.read_text() if rc.exists() else ""
        if line not in content:
            with open(rc, "a") as f:
                f.write("\n" + line + "\n")
            print(f"✅ Incluído source no {rc.name}: {line}")
        else:
            print(f"🆗 Source já presente no {rc.name}")

def tcp_reachable(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def parse_host_port_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    return parsed.hostname or "", parsed.port or 6443

def prompt_profile() -> Dict[str, Any]:
    print("➕ Criando perfil de cluster")
    name = input("Nome do perfil (ex.: prod, hml, dev): ").strip()
    if not name:
        print("Nome inválido."); sys.exit(2)
    server = input("API server (ex.: https://api.cluster:6443): ").strip()
    insecure = input("Skip TLS verif? (y/N) [N]: ").strip().lower().startswith("y")
    kubeconfig = input(f"Caminho KUBECONFIG p/ este perfil [~/.kube/config-{name}]: ").strip() or f"~/.kube/config-{name}"
    kubeconfig = str(Path(os.path.expanduser(kubeconfig)))

    add_argocd = input("Deseja configurar Argo CD para este perfil? (y/N) [N]: ").strip().lower().startswith("y")
    argocd_server = input("Argo CD server (ex.: argocd.apps.cluster): ").strip() if add_argocd else None

    return {
        "name": name,
        "server": server,
        "insecure": insecure,
        "kubeconfig": kubeconfig,
        "argocd_server": argocd_server or None,
    }

def upsert_profile(p: Dict[str, Any]):
    cfg = load_profiles()
    cfg["profiles"][p["name"]] = p
    if not cfg.get("default"):
        cfg["default"] = p["name"]
    save_profiles(cfg)
    print(f"✅ Perfil salvo: {p['name']}")

def remove_profile(name: str):
    cfg = load_profiles()
    if name in cfg["profiles"]:
        del cfg["profiles"][name]
        if cfg.get("default") == name:
            cfg["default"] = next(iter(cfg["profiles"].keys()), None)
        save_profiles(cfg)
        print(f"🗑️  Perfil removido: {name}")
    else:
        print("Perfil não encontrado.")

def set_default(name: str):
    cfg = load_profiles()
    if name not in cfg["profiles"]:
        print("Perfil não encontrado."); return
    cfg["default"] = name
    save_profiles(cfg)
    print(f"⭐ Perfil padrão alterado: {name}")

def list_profiles():
    cfg = load_profiles()
    d = cfg.get("default")
    if not cfg["profiles"]:
        print("Nenhum perfil cadastrado."); return
    print("Perfis cadastrados:")
    for n, p in cfg["profiles"].items():
        star = " *" if n == d else ""
        print(f" - {n}{star} :: server={p['server']} kubeconfig={p['kubeconfig']} insecure={p['insecure']} argocd={bool(p['argocd_server'])}")

def render_shell_block(cfg: Dict[str, Any]) -> str:
    """
    Gera um bloco POSIX-shell compatível tanto com bash quanto zsh:
    - helpers globais (k, k*; kns; kctx; use-kcfg)
    - funções por perfil (oc-login-<name>, oc-login-token-<name>, use-kcfg-<name>, skopeo-login-internal-<name>, argocd-login-<name>)
    """
    lines = []
    lines.append(SENTINEL_BEGIN)

    # Helpers globais (kubectl shortcuts + ns/context + use-kcfg)
    lines += [
        '# Helpers globais',
        'alias k="kubectl"',
        'alias kg="kubectl get"',
        'alias kd="kubectl describe"',
        'alias kga="kubectl get -A"',
        'alias kgp="kubectl get pods"',
        'alias kgs="kubectl get svc"',
        'alias kgn="kubectl get nodes"',
        'alias kdp="kubectl describe pod"',
        'alias klogs="kubectl logs"',
        '',
        'kns(){ if [ -z "$1" ]; then echo "uso: kns <namespace>"; return 2; fi; kubectl config set-context --current --namespace="$1"; }',
        'kctx(){ if [ -z "$1" ]; then kubectl config get-contexts; return; fi; kubectl config use-context "$1"; }',
        'use-kcfg(){ if [ -z "$1" ]; then echo "uso: use-kcfg <perfil>"; return 2; fi; export KUBECONFIG="$HOME/.kube/config-$1"; echo "KUBECONFIG=$KUBECONFIG"; }',
        ''
    ]

    for name, p in cfg["profiles"].items():
        server = p["server"]
        insecure = "true" if p["insecure"] else "false"
        kubeconfig = p["kubeconfig"]

        lines += [
            f'# ---- Perfil: {name}',
            f'use-kcfg-{name}()' + ' { export KUBECONFIG="' + kubeconfig + '"; echo "KUBECONFIG=$KUBECONFIG"; }',
            '',
            # Login padrão via OAuth/browser; nenhuma senha é passada em argv.
            f'oc-login-{name}()' + ' {',
            '  OC_BIN="${OC_BIN:-$HOME/.local/bin/oc}"',
            f'  "$OC_BIN" login --web --server="{server}" {"--insecure-skip-tls-verify=true" if insecure=="true" else ""} --kubeconfig="' + kubeconfig + '"',
            '}',

            # oc login com token (env/arg/prompt)
            f'oc-login-token-{name}()' + ' {',
            '  OC_BIN="${OC_BIN:-$HOME/.local/bin/oc}"',
            '  local tok="${1:-${OCP_TOKEN}}";',
            '  if [ -z "$tok" ]; then printf "Token: " 1>&2; stty -echo; read -r tok; stty echo; printf "\\n" 1>&2; fi',
            f'  "$OC_BIN" login --token="$tok" --server="{server}" {"--insecure-skip-tls-verify=true" if insecure=="true" else ""} --kubeconfig="' + kubeconfig + '"',
            '}',

            # skopeo login no registry interno (default-route)
            f'skopeo-login-internal-{name}()' + ' {',
            '  OC_BIN="${OC_BIN:-$HOME/.local/bin/oc}"',
            '  if ! "$OC_BIN" whoami >/dev/null 2>&1; then echo "Faça oc-login primeiro." 1>&2; return 1; fi',
            '  local host; host=$("$OC_BIN" -n openshift-image-registry get route default-route -o jsonpath="{.spec.host}" 2>/dev/null)',
            '  if [ -z "$host" ]; then echo "default-route do image-registry não encontrado (verifique a exposição externa)." 1>&2; return 2; fi',
            '  local tok; tok=$("$OC_BIN" whoami -t)',
            '  skopeo login --tls-verify=false -u unused -p "$tok" "$host"',
            '}',

        ]
        # argocd (opcional por perfil)
        if p.get("argocd_server"):
            host = p["argocd_server"]
            lines += [
                f'argocd-login-{name}()' + ' {',
                '  local user="${1:-admin}"',
                f'  argocd login "{host}" --username "$user" --insecure',
                '}',

            ]
        lines.append('')  # linha em branco entre perfis

    lines.append(SENTINEL_END)
    return "\n".join(lines) + "\n"

def write_managed_block(aliases_path: Path, block: str):
    aliases_path.parent.mkdir(parents=True, exist_ok=True)
    old = aliases_path.read_text() if aliases_path.exists() else ""
    if SENTINEL_BEGIN in old and SENTINEL_END in old:
        pre = old.split(SENTINEL_BEGIN)[0]
        post = old.split(SENTINEL_END)[-1]
        new = pre + block + post
    else:
        new = (old.rstrip() + "\n\n" + block) if old.strip() else block
    tmp = aliases_path.with_suffix(aliases_path.suffix + ".tmp")
    tmp.write_text(new)
    tmp.chmod(0o600)
    tmp.replace(aliases_path)
    print(f"✅ Bloco gerenciado atualizado em {aliases_path}")

def apply_aliases():
    cfg = load_profiles()
    block = render_shell_block(cfg)
    write_managed_block(ZSH_ALIASES, block)
    write_managed_block(BASH_ALIASES, block)
    ensure_rc_sources()
    print("🔁 Ative no shell atual com:")
    print("   source ~/.zsh_aliases  # ou  source ~/.bash_aliases")

def check_reachability_all():
    cfg = load_profiles()
    for name, p in cfg["profiles"].items():
        host, port = parse_host_port_from_url(p["server"])
        ok = tcp_reachable(host, port, 3.0)
        print(f"[{name}] {p['server']} → {'OK' if ok else 'NOK'}")

def usage():
    print(f"""Uso:
  {sys.argv[0]} add                 # cria/atualiza um perfil (interativo)
  {sys.argv[0]} rm <perfil>         # remove perfil
  {sys.argv[0]} list                # lista perfis
  {sys.argv[0]} default <perfil>    # seta perfil padrão
  {sys.argv[0]} apply               # (re)gera blocos de funções/aliases e configura sourcing
  {sys.argv[0]} check               # teste de reachability TCP para todos os servidores

Dica:
  Depois do 'apply', use:
    use-kcfg-<perfil>       # exporta KUBECONFIG daquele perfil
    oc-login-<perfil>       # login OAuth pelo navegador
    oc-login-token-<perfil> # login via token (param/ENV OCP_TOKEN)
    skopeo-login-internal-<perfil>
    argocd-login-<perfil>   # se configurado no perfil
""")

def main():
    args = sys.argv[1:]
    if not args:
        usage(); sys.exit(0)

    cmd = args[0]
    if cmd == "add":
        p = prompt_profile()
        upsert_profile(p)
        apply_aliases()
    elif cmd == "rm" and len(args) >= 2:
        remove_profile(args[1]); apply_aliases()
    elif cmd == "list":
        list_profiles()
    elif cmd == "default" and len(args) >= 2:
        set_default(args[1]); apply_aliases()
    elif cmd == "apply":
        apply_aliases()
    elif cmd == "check":
        check_reachability_all()
    else:
        usage(); sys.exit(2)

if __name__ == "__main__":
    main()
