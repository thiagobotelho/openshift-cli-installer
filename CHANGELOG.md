# Changelog

## [Unreleased]

### Added

- Lockfile de versões, `--latest`, `--only`, `--dry-run` e testes.
- Suporte explícito a Fedora, Debian/Ubuntu e WSL.
- `jq` e `yq` no toolchain.

### Changed

- Subprocessos não usam shell.
- Login padrão do OpenShift usa OAuth/browser.
- Login Argo CD deixa a coleta de senha para a própria CLI.

### Removed

- Fallback fixo e obsoleto do `roxctl`.
- Senhas montadas em argumentos de processos.
