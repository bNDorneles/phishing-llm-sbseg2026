# GitHub Release Checklist

Use este checklist antes de publicar ou atualizar o repositorio.

- [ ] `.env` nao esta versionado.
- [ ] Nenhuma API key aparece em arquivos versionaveis.
- [ ] Datasets grandes nao estao versionados.
- [ ] `data/raw/` contem somente `.gitkeep` no Git.
- [ ] `data/processed/` contem somente `.gitkeep` no Git.
- [ ] `data/baseline_historico/` contem somente `.gitkeep` no Git.
- [ ] `results/` contem somente `.gitkeep` no Git.
- [ ] Respostas brutas nao estao versionadas.
- [ ] Logs nao estao versionados.
- [ ] ZIPs, RARs e CSVs nao estao versionados.
- [ ] README revisado.
- [ ] `requirements.txt` revisado.
- [ ] Scripts principais funcionando.
- [ ] Documentacao em `docs/` revisada.
- [ ] `git status --short --untracked-files=all` mostra apenas arquivos esperados.
- [ ] Commit preparado sem `git add .env`.

Comandos de verificacao uteis:

```powershell
git status --short --untracked-files=all
Get-ChildItem -Recurse -Force -File | Select-String -Pattern "sk-|gsk_|AIza|secret|token"
```
