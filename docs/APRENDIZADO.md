# Versões, integridade e contexto

## O que observar

versions.lock.json define versões padrão; overrides devem ser intencionais e explícitos. Checksums validam o artefato baixado, não a autorização do contexto de cluster. Execute os testes offline antes de instalar. Não armazene senha em aliases; confira servidor e identidade antes de usar qualquer perfil.

## Roteiro de leitura e validação

1. Leia o README e identifique o componente que recebe a configuração.
2. Confira namespaces, seletores, portas, identidades e dependências nos exemplos.
3. Ajuste apenas os campos necessários em um ambiente isolado; não use credenciais de produção.
4. Valide sintaxe e contratos locais antes de aplicar. Registre o resultado real separado deste guia.
5. Execute um caso permitido e um caso negado, conferindo a causa da resposta.
6. Defina reversão por recurso/arquivo e preserve dados persistentes antes de mudanças.

Os comentários dos manifests explicam escolhas; não comprovam disponibilidade do componente. Exemplos fora de entradas Kustomize não são implantados automaticamente.
