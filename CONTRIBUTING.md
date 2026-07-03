# Contribuindo

1. Crie uma branch a partir de `main`.
2. Preserve Python 3.10+, `amd64` e `arm64`.
3. Todo download deve usar HTTPS e SHA256 quando o fornecedor publicar hash.
4. Não use `shell=True`, não persista credenciais e não passe senhas em argv.
5. Atualize `versions.lock.json` e o changelog quando alterar versões padrão.
6. Execute:

```bash
python3 -m unittest discover -s tests -v
python3 install.py --dry-run
```
