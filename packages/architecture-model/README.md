# @rorikit/vamos-architecture-model

Версионируемый контракт между Vamos Subscription Tracker и внешними архитектурными инструментами.

Пакет собирается из `docs/architecture/architecture_snapshot.json`, `README.md` и `SUMMARY.md`. Он не содержит бизнес-код, секреты или доступ к production API.

```powershell
cd packages/architecture-model
npm run build
npm run check
npm pack
```

Публикация выполняется в GitHub Packages. Потребители импортируют только опубликованные артефакты и не зависят от файловой структуры основного приложения.
