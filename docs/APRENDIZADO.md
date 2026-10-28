# Versões, integridade e contexto


versions.lock.json define versões padrão; overrides devem ser intencionais e explícitos. Checksums validam o artefato baixado, não a autorização do contexto de cluster. Execute os testes offline antes de instalar. Não armazene senha em aliases; confira servidor e identidade antes de usar qualquer perfil.

## Relação com o cluster

Instalar oc/kubectl não autentica o usuário nem concede RBAC. Após a instalação, confira versão do cliente, contexto, servidor e `oc whoami` no terminal de execução. Para problemas da stack, use os procedimentos de argocd-gitops; evite repetir bootstrap ou alterar aliases para contornar uma sessão expirada.
