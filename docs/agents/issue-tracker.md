# Трекер задач: GitHub

Задачи и спеки этого репозитория живут как GitHub issues. Все операции — через `gh` CLI.

## Соглашения

- **Создать issue**: `gh issue create --title "..." --body "..."`. Для многострочного тела — heredoc.
- **Прочитать issue**: `gh issue view <number> --comments`, комментарии фильтровать через `jq`, метки получать отдельно.
- **Список issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` с нужными фильтрами `--label` и `--state`.
- **Прокомментировать**: `gh issue comment <number> --body "..."`
- **Поставить / снять метку**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Закрыть**: `gh issue close <number> --comment "..."`

Репозиторий определяется из `git remote -v`; внутри клона `gh` делает это автоматически.

## Pull request'ы как поверхность триажа

**PR как источник запросов: нет.** _(Поставьте `yes`, только если внешние PR считаются фиче-реквестами; `/triage` читает этот флаг.)_

При `yes` PR проходят те же метки и состояния, что и issues, через аналоги `gh pr`:
просмотр — `gh pr view <number> --comments` и `gh pr diff <number>`;
внешние PR для триажа — `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`,
оставляя только `authorAssociation` из `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, `NONE` (владельцы и члены команды отбрасываются);
комментарий/метка/закрытие — `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub использует общее пространство номеров для issues и PR, поэтому `#42` может быть чем угодно:
сначала `gh pr view 42`, при неудаче — `gh issue view 42`.

## Когда скилл говорит «опубликовать в трекер»

Создать GitHub issue.

## Когда скилл говорит «получить задачу»

Выполнить `gh issue view <number> --comments`.

## Wayfinder-операции

Используются скиллом `/wayfinder`. **Карта** — один issue с **дочерними** issues-задачами.

- **Карта**: один issue с меткой `wayfinder:map` (тело: Notes / Decisions-so-far / Fog): `gh issue create --label wayfinder:map`.
- **Дочерняя задача**: issue, привязанный к карте как GitHub sub-issue (`gh api`, эндпоинт sub-issues). Где sub-issues недоступны — добавить задачу в чек-лист тела карты и указать `Part of #<map>` в начале тела дочерней задачи. Метки: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). После взятия в работу задача назначается ведущему разработчику.
- **Блокировки**: нативные **issue dependencies** GitHub — каноничное, видимое в UI представление. Добавить ребро: `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, где `<blocker-db-id>` — числовой **database id** блокера (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`; это не `#number` и не `node_id`). GitHub отдаёт `issue_dependencies_summary.blocked_by` (только открытые блокеры — «живой» гейт). Где зависимости недоступны — строка `Blocked by: #<n>, #<n>` в начале тела дочерней задачи. Задача разблокирована, когда закрыты все блокеры.
- **Запрос фронтира**: список открытых дочерних задач карты (`gh issue list --state open` в пределах sub-issues / чек-листа карты), отбросить те, у кого есть открытый блокер (`issue_dependencies_summary.blocked_by > 0` или открытый issue в строке `Blocked by`) или исполнител; побеждает первый по порядку карты.
- **Взять в работу**: `gh issue edit <n> --add-assignee @me` — первая запись сессии.
- **Закрыть (resolve)**: `gh issue comment <n> --body "<ответ>"`, затем `gh issue close <n>`, затем добавить указатель на контекст (gist + ссылка) в Decisions-so-far карты.
