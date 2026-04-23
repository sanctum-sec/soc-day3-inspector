> **English version:** [README.en.md](README.en.md)

# Команда 6 — Інспектор (Inspector): комплаєнс, аудит і конструктор навчальних матеріалів

**Ваш Lightsail:** `wic06.sanctumsec.com` (18.185.169.40)
**Ваш GitHub-репозиторій:** `https://github.com/sanctum-sec/soc-day3-inspector`
**Прочитайте спочатку:** [`sanctum-sec/soc-protocol`](https://github.com/sanctum-sec/soc-protocol) — це контракт, якого мають дотримуватися всі інші команди, і джерело істини, проти якого ви їх інспектуєте.

---

## 1. Ваша місія — два deliverable, не один

Ви — **регулятор** SOC. Там, де інші п'ять команд *будують* SOC, ви його *інспектуєте* проти задекларованого протоколу й політик — а потім **перетворюєте здобутий досвід на навчальні матеріали, які зможете передати колегам у вашому HQ.**

До кінця дня ви виробите **дві речі**, обидві однаково важливі:

### 1a. Живий інструмент комплаєнс-інспекції
- Probe, що безперервно перевіряє кожен із 5 SOC-інструментів проти спільного контракту
- Read-only компаєнс-дашборд, який може переглянути будь-хто
- Журнал знахідок (що пройшло, що ні, коли, чому)

### 1b. Навчальний пакет для вашого HQ (take-home)
- Двомовний **інспекційний чек-лист** (EN + UK) — можна використати у SNRIU чи будь-якому SOC, який ви наглядаєте
- **Runbook «Як інспектувати SOC»** (UA-first) — навчальний покроковий матеріал для ваших колег
- **Документ «Методологія AI-assisted розробки»** (UA + EN) — *як саме* ви сьогодні використовували Claude Code, щоб побудувати інспекційний інструмент за один день: справжні промпти, рішення, висновки. Це та частина, яка помножить ваш вплив у HQ — перетворює один день воркшопу на повторно використовуваний навчальний модуль.
- **Бібліотека промптів (prompt library)** — з анотаціями й позначками «що спрацювало», «обережно», «уникати».

Навчальний пакет — не декорація. Він **є** вашим deliverable. Інспекційний інструмент — те, що дає вам авторитет навчати.

---

## 2. Де це місце в реальному SOC

З Таблиці 1 «11 Strategies of a World-Class SOC» (MITRE, 2022):

- **External Training and Education** — ваша головна функція сьогодні.
- **Situational Awareness and Communications** — комплаєнс-дашборд = вид регулятора.
- **Vulnerability Assessment** — ви буквально тестуєте контрольні слабкості peer-інструментів.
- **Metrics** — ви визначаєте, що значить «відповідає вимогам», і вимірюєте це.
- **Strategy, Planning, and Process Improvement** — ваші знахідки змушують інші команди покращуватися.

У регульованих галузях (ядерна, фінансова, медична) ця роль має назву: функція внутрішнього аудиту. У менш регульованих — «GRC» (Governance, Risk, Compliance). В обох випадках це функція, що тримає решту п’ятьох чесними.

---

## 3. Доступ і що вже встановлено

```
ssh ubuntu@wic06.sanctumsec.com
# password/пароль: see https://wic-krakow.sanctumsec.com/wic-access-ghosttrace (ask the instructor for the Basic Auth credentials)
```

Встановлено: git, Python 3.10 + pip, Node.js LTS, `claude`, `codex`, AWS CLI + креденшли до `s3://wic-krakow-2026`, jupyter + pandas/numpy/matplotlib/seaborn/scikit-learn/requests/httpx, плюс `SOC_PROTOCOL_TOKEN` у `~/.soc_env`.

Відкриті порти: 22 (SSH), 80 (HTTP), 8000 (ваш застосунок), 8001 (ваша адмінка).

---

## 4. Потоки даних

На відміну від Команд 1–5, ви — **чистий споживач** інших інструментів, read-only спостерігач. Ви не емітите події в спільний протокол. Ваші виходи — **звіти, дашборди і навчальні артефакти**, не події.

### 4.1 Що ви споживаєте (входи)

Від кожного з 5 SOC-інструментів:

| Тип probe                  | Тестований endpoint                                        | Очікуваний результат                              |
| -------------------------- | ---------------------------------------------------------- | ------------------------------------------------- |
| Liveness                   | `GET /health`                                              | 200, `{"status":"ok","tool":"<name>"}`            |
| Unauth write               | `POST /ingest` (без `Authorization`)                       | 401                                               |
| Поганий токен              | `POST /ingest` із завідомо-неправильним bearer             | 401                                               |
| Malformed JSON             | `POST /ingest` з некоректним тілом (не JSON)               | 400                                               |
| Schema-порушення           | `POST /ingest` з пропущеними обов'язковими полями envelope | 400                                               |
| Неправильний event_type    | `event_type`, який target не повинен приймати              | 400                                               |
| Rate-limit enforcement     | 200 валідних запитів за 60с                                | Має спрацювати 429 до кінця                       |
| Admin-ізоляція             | `GET <host>:8001/admin` без auth                            | 401                                               |
| Admin auth працює          | `GET <host>:8001/admin` із Basic Auth                       | 200                                               |

### 4.2 Що ви виробляєте (виходи)

| Вихід                                    | Локація                                                                  | Аудиторія                               |
| ---------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------- |
| Живий комплаєнс-дашборд                  | `http://wic06.sanctumsec.com:8000/compliance`                            | Будь-хто у воркшопі                     |
| Findings JSON API                        | `GET http://wic06.sanctumsec.com:8000/findings`                          | Дашборд Диспетчера, усі цікаві          |
| Адмін-сторінка                           | `http://wic06.sanctumsec.com:8001/admin` (Basic Auth)                    | Тільки ваша команда                     |
| Ваш /health                              | `GET http://wic06.sanctumsec.com:8000/health`                            | Усі                                     |
| **Навчальні артефакти (S3)**             | `s3://wic-krakow-2026/public/inspector/*`                                | Ваші колеги в HQ, видно на landing page після upload |

### 4.3 Приклад finding-запису

Ваша таблиця знахідок зберігає по одному рядку на виконання probe:

```json
{
  "finding_id": "F-2026-0001",
  "probe_time": "2026-04-23T11:02:14Z",
  "target_tool": "scout",
  "target_host": "wic02.sanctumsec.com:8000",
  "check_id": "C-AUTH-001",
  "check_label": "POST /ingest without Authorization returns 401",
  "expected": 401,
  "observed": 200,
  "status": "FAIL",
  "severity": "high",
  "notes": "Endpoint accepted unauthenticated request — violates soc-protocol §7.1"
}
```

---

## 5. Архітектура — чотири шари (не три)

Ви будуєте все, що інші команди, плюс один унікальний шар.

### 5.1 Probe-движок

Невеликий Python-модуль, що раз на ~60 секунд виконує кожну зареєстровану перевірку проти кожного target-у. Результати дописуються у `findings.db` (SQLite). Кожна перевірка — одна Python-функція, що повертає `{status, expected, observed, notes}`.

Стартові **мінімум 8 перевірок** (пізніше можна додати):

| Check ID         | Що тестує                                                              |
| ---------------- | ---------------------------------------------------------------------- |
| `C-LIVE-001`     | `GET /health` повертає 200                                             |
| `C-AUTH-001`     | `POST /ingest` без bearer → 401                                        |
| `C-AUTH-002`     | `POST /ingest` з неправильним bearer → 401                             |
| `C-SCHEMA-001`   | Non-JSON body → 400                                                    |
| `C-SCHEMA-002`   | Envelope без `event_type` → 400                                        |
| `C-RATE-001`     | 200 швидких валідних запитів → хоча б одна відповідь 429               |
| `C-ADMIN-001`    | `GET <host>:8001/admin` без auth → 401                                 |
| `C-ISOLATION-001`| Порт застосунку (8000) не експонує адмін-роути                         |

### 5.2 Комплаєнс-дашборд

Сторінка FastAPI на `/compliance`: жива матриця — рядки це 5 інструментів, стовпці — перевірки, клітинки — ✓ / ✗ / ? з hover-деталями. Авто-refresh кожні 15с. Публічна (read-only, без auth) — це регулятор-facing вид.

### 5.3 Адмін-сторінка (порт 8001)

Такі самі вимоги, як у кожної команди — два таби (Operational + Security). Basic Auth за `ADMIN_USER` / `ADMIN_PASS`. Показує:

- Operational: перевірок виконано за годину, провалів сьогодні, статус per-target, глибина черги
- Security: невдалі auth-и проти ваших write-endpoint-ів, rate-limit-trips, падіння probe-движка

### 5.4 Конструктор навчальних артефактів *(ваш унікальний шар)*

Набір Markdown-файлів, які ваша команда пише протягом дня і публікує в `s3://wic-krakow-2026/public/inspector/` наприкінці:

| Файл                                     | Опис                                                                                                                        |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `inspection-checklist.en.md`             | Таблиця кожної перевірки: що тестує, як перевірити вручну, як виглядає pass/fail. **Повторно-використовується у HQ проти будь-якого SOC.** |
| `inspection-checklist.uk.md`             | Те саме, українською.                                                                                                        |
| `how-to-inspect-a-soc.uk.md`             | Розгорнутий runbook: «Що робити регулятору-інспектору, що прибув до SOC уперше» — послідовність дій і поводження зі знахідками. |
| `ai-assisted-build-methodology.uk.md`    | **Головний навчальний deliverable.** Описує, ЯК ви сьогодні використовували Claude Code: промпти, що спрацювали; ті, що ні; точки рішення; техніки верифікації; як критично читати AI-згенерований код. Стає AI-методологічним навчальним модулем у вашому HQ. |
| `ai-assisted-build-methodology.en.md`    | Англомовна версія для двомовного обміну.                                                                                     |
| `prompt-library.md`                      | Курована, анотована колекція справжніх промптів, які ваша команда використала. Кожен — зі стислим висновком: що згенеровано, чи прийняли, що б змінили. |
| `lessons-learned.uk.md`                  | «Що нас здивувало. Що зробили б інакше. Чого досі не розуміємо.» — чесна ретроспектива.                                      |

**Структура методологічного документа** (найважливіший артефакт): пишіть так, ніби навчаєте колегу, який ніколи не використовував Claude Code. Включіть скріншоти реальних prompt→output обмінів (заочищені). Це те, що помножує вплив воркшопу — один день вашого часу стає постійною навчальною спроможністю.

---

## 6. Рекомендований стек (не обовʼязковий)

| Компонент         | Рекомендація                             | Чому                                                                    |
| ----------------- | ---------------------------------------- | ----------------------------------------------------------------------- |
| Мова              | **Python 3.10**                          | Уже встановлено повний data-science набір                              |
| HTTP              | **FastAPI** + Uvicorn                    | Тими ж endpoint-ами ви стукатимете в peer-и                            |
| HTTP-клієнт       | **httpx** (async)                        | Probe 5 targets × 8 перевірок = 40 викликів за цикл — async допомагає  |
| Store             | **SQLite** (`findings.db`)               | Достатньо на день                                                       |
| Dashboard UI      | FastAPI + Jinja + HTMX                   | Узгоджено з peer-ами                                                    |
| Scheduler         | APScheduler або простий asyncio-loop     | Probe раз на 60с                                                        |
| Artifact-authoring | Просто **Markdown у репозиторії**         | `git push` — це ваш publish. S3-upload — фінальна дистрибуція           |

---

## 7. Security-інфраструктура — без компромісів (і мета)

Ви будуєте інструмент, що *шукає* слабкості у безпеці. Його власна безпека важлива вдвічі.

- [ ] Bearer на будь-яких write-endpoint-ах (`/findings` може лишитися read-only публічним, але НЕ writable)
- [ ] HTTP Basic на адмін-сторінці
- [ ] Rate-limit **ваших власних probe** — максимум 1 probe-cycle на target на хвилину. Швидше — ризикуєте покласти peer-а, що було б катастрофою для audit-team
- [ ] Логуйте кожен probe, який відправили (probe log) ТА кожну відповідь (response log) ТА кожне падіння probe-движка (security log). Ваша прозорість — ваш авторитет
- [ ] **Не** пробуйте brute-force чи експлойт — ви тестуєте задекларований контракт, не робите red-team. Якщо знайдете справжню вразливість — зупиніться, опишіть і передайте фасилітатору
- [ ] Чітке оголошення scope: публікуйте *що саме* перевіряєте на `/compliance`. Без прихованих перевірок

Попросіть Claude: *«Додай rate-limit на probe-движок: кожен target перевіряється максимум раз на 60 секунд на кожну перевірку. Якщо пробую частіше — queue + delay.»*

---

## 8. Специфікація адмін-сторінки

URL: `http://wic06.sanctumsec.com:8001/admin`, HTTP Basic.

**Operational:**
- Перевірок виконано за 5 хв / 1 год / 24 год
- Per-target процент комплаєнсу (pass/total)
- Per-check частота провалів по всіх targets
- Глибина probe-черги
- Delivery health: чи досяжний кожен target на `/health`

**Security:**
- Невдалі auth-и проти ваших endpoint-ів
- Rate-limit trips (на probe-submission)
- Винятки probe-движка
- Відповіді peer-ів, що виглядають як crash peer-side, а не політика — ви хочете ловити випадки, коли peer-сервіс упав, а не ввічливо відмовив

---

## 9. Ваш день — фази з Claude

### Фаза 0 — Kickoff (9:15–10:00)

Спільна сесія з фасилітатором. **Особливо уважно слухайте, що саме говорить контракт** — ті пункти стануть вашими перевірками. Розподіліть ролі.

**Унікальне для вас:** заведіть `methodology-journal.md` у репозиторії *уже зараз* і фіксуйте кожен промпт до Claude + одним рядком, що Claude повернув. Це сирий матеріал для ai-methodology-doc-у.

### Фаза 1 — Скафолд (10:00–10:45)

```
Start a FastAPI project in ~/app for a SOC compliance inspection tool. Create:
- main.py with /health, /findings (GET, returns recent findings),
  /compliance (GET, renders the matrix dashboard).
- probes/__init__.py — registry pattern for probe modules.
- storage/db.py — SQLite schema: findings (finding_id, probe_time, target_tool,
  target_host, check_id, check_label, expected, observed, status, severity, notes).
- schemas/envelope.py — shared Pydantic envelope for when WE POST to peers.
- templates/compliance.html — Jinja matrix template.
- scheduler.py — background task that runs every 60 seconds.
- systemd unit. requirements.txt: fastapi uvicorn httpx apscheduler pydantic jinja2.

Commit the scaffold. Keep methodology-journal.md updated with the prompt I used above
and a one-line note: what did Claude generate, what did we accept, what did we change?
```

### Фаза 2 — Перші probes (10:45–12:00)

Почніть з найпростішої перевірки — liveness — вдарте усі 5 інструментів. Ви виявите, хто реально вже живий (деякі ще можуть бути в mock-фазі — це теж валідна знахідка).

```
Create ~/app/probes/liveness.py with an async function check(target_host, http_client)
that GETs http://{target_host}/health with a 3-second timeout. Returns a dict with
{check_id: "C-LIVE-001", expected: 200, observed: <status>, status: "PASS"|"FAIL"|"UNREACHABLE", notes}.

Create ~/app/targets.py as a list of 5 dicts: trap (wic01), scout (wic02), analyst (wic03),
hunter (wic04), dispatcher (wic05). Each has tool name + host.

Wire scheduler.py to run ALL registered probes against ALL targets every 60 seconds,
write findings to the database. Run it.

Verify findings.db fills up. Serve /findings.
```

**Чекпоінт о 12:00.** Обід. Перед цим — commit, deploy, підтвердіть, що хоча б одна перевірка успішно виконується.

### Фаза 3 — Compliance-перевірки (13:00–14:30)

Додайте auth- і schema-перевірки. Тут ваша робота починає *знаходити*.

```
Add seven more probe modules under ~/app/probes/:
- auth_noheader.py — C-AUTH-001 — POST /ingest with no Authorization header, expect 401.
- auth_wrongtoken.py — C-AUTH-002 — POST /ingest with "Authorization: Bearer NOT_THE_TOKEN", expect 401.
- schema_nonjson.py — C-SCHEMA-001 — POST /ingest with body="<html>", expect 400.
- schema_missingfield.py — C-SCHEMA-002 — POST /ingest with {"event_type": "telemetry"} only, expect 400.
- rate_limit.py — C-RATE-001 — send 200 legitimate POSTs in 60 seconds using a valid bearer; expect at least one 429.
  THIS ONE IS DANGEROUS. Run it once per hour per target, not every minute. Put it on a separate slow schedule.
- admin_noauth.py — C-ADMIN-001 — GET http://target:8001/admin, expect 401.
- admin_isolation.py — C-ISOLATION-001 — GET http://target:8000/admin, expect 404 (admin must not be on app port).
```

### Фаза 4 — Комплаєнс-дашборд (14:30–15:30)

```
Fill in templates/compliance.html. Render a table:
- Columns: 5 tools (trap, scout, analyst, hunter, dispatcher)
- Rows: one per check_id
- Cells: ✓ (green, all recent results PASS), ✗ (red, any FAIL in last 10 min),
  ? (gray, no recent data or UNREACHABLE)
- Hover on a cell shows the most recent finding: expected vs observed, notes, time.

Below the table, show the 20 most-recent findings.

HTMX hx-get with every-15s refresh on the matrix.
Public (no auth). Dark-ish theme, readable at projection distance.
```

### Фаза 5 — Адмін-сторінка + хардінг (15:30–16:30)

```
Create ~/app/admin/ on port 8001, HTTP Basic (ADMIN_USER, ADMIN_PASS from env).
- Operational tab: checks executed in last 5m / 1h / 24h, per-target compliance %,
  per-check failure rate, probe queue depth.
- Security tab: auth failures on any write endpoint, rate-limit trips on probe
  submission, probe-engine exceptions (from try/except), responses from peers
  that looked like crashes vs policy violations.

Also add a probe-rate limiter: reject internal calls to run_probe(...) that try
to probe the same (target, check) combination more than once per 60 seconds.
```

### Фаза 6 — Навчальні артефакти (16:30–17:15) — *унікальна фаза регулятора*

Ця фаза щонайменше така сама важлива, як технічна робота вище.

Кожен член команди бере один артефакт. Використовуйте Claude як writing-assistant:

- **Інспекційний чек-лист (двомовний):**
  ```
  Take my list of 8 compliance checks from probes/ and draft an inspection
  checklist formatted for a regulatory inspector. Columns: check ID, what's
  being tested, why it matters, how to verify manually (curl command),
  expected result, failure implications. Output in English first, then translate
  to Ukrainian, preserving technical terms in English.
  ```

- **Runbook «Як інспектувати SOC» (UA-primary):**
  ```
  Write a Ukrainian-language runbook for a regulatory inspector arriving at
  a SOC for the first time. Cover: what to ask the SOC manager, how to read
  their declared contract, how to design your own check list, how to sample
  without overwhelming operators, how to write findings, how to distinguish
  non-conformity from implementation variance. Aim for 2–3 pages.
  ```

- **AI-методологія (UA + EN):**
  ```
  Read my methodology-journal.md (the log of every prompt we used today and
  what Claude produced). Reorganize it into a training document titled
  "How we used AI to build a SOC compliance inspector in one day." Include:
  (1) an honest preamble — what AI is and isn't good at in this context;
  (2) the prompt patterns that worked (with examples);
  (3) verification techniques — how we avoided accepting broken code;
  (4) moments where the AI was wrong and how we caught it;
  (5) a reusable prompt library;
  (6) limitations and when to stop using AI and think yourself.
  Write the primary version in Ukrainian, then an English translation.
  ```

- **Prompt-бібліотека:** курюйте з `methodology-journal.md` — один Markdown, кожен промпт із підсумком результату та теґом `⭐ рекомендовано` / `⚠ обережно` / `❌ уникати`.

- **Lessons-learned:** 1–2 сторінки чесної ретроспективи українською.

Завантажте всі артефакти в `s3://wic-krakow-2026/public/inspector/` — вони зʼявляться на landing-сторінці воркшопу.

### Фаза 7 — Підготовка до демо (17:15–17:30)

- Виведіть комплаєнс-дашборд на великий екран
- Оберіть одну провалену перевірку як наратив: «Ось що зробив наш probe, ось що Scout повернув, ось чому це невідповідність, ось що ми б сказали Scout виправити»
- Призначте людину презентувати take-home-навчальний пакет

---

## 10. Як поділити роботу між 3–5 людьми

Якщо вас **3**:

| Роль                     | Відповідає за                                            |
| ------------------------ | -------------------------------------------------------- |
| Probe engineer           | Усі 8 probe + scheduler + findings store                 |
| Dashboard + admin        | /compliance-дашборд, адмін-сторінка, деплой              |
| Training artifacts lead  | Methodology journal, 6 take-home-документів              |

Якщо вас **4**:

| Роль                     | Відповідає за                                   |
| ------------------------ | ----------------------------------------------- |
| Probe engineer           | Усі 8 probe + scheduler                         |
| Platform + storage       | FastAPI, findings DB, findings API              |
| Dashboard + admin        | /compliance, адмінка, деплой                    |
| Training artifacts lead  | Methodology journal + усі 6 документів          |

Якщо вас **5**:

Поділіть «training artifacts» на (a) інспекційний чек-лист + runbook (workshop-domain) і (b) AI-методологія + prompt-бібліотека + lessons-learned (domain «навчання про AI»). Обидві ролі спільно ведуть methodology-journal.

---

## 11. Чекліст «спочатку мок»

До 11:00:

- [ ] `GET /health` працює
- [ ] `GET /findings` повертає щонайменше 3 заздалегідь створених фейкових finding-записи (щоб Диспетчер бачив форму)
- [ ] `GET /compliance` повертає статичну HTML-матрицю (поки без реальних даних)
- [ ] `methodology-journal.md` має щонайменше 3 записи з ранкових промптів

---

## 12. Definition of done

**Мінімум — інструмент:**
- [ ] Probe працює проти всіх 5 інструментів у 60-секундному циклі
- [ ] Щонайменше 6 з 8 перевірок імплементовано
- [ ] Findings у SQLite
- [ ] `/compliance` живий, показує поточну матрицю
- [ ] Адмінка на 8001 з обома табами
- [ ] Bearer на write-endpoint-ах, rate-limit, schema-валідація
- [ ] systemd + GitHub Actions деплой

**Мінімум — навчальний пакет:**
- [ ] Інспекційний чек-лист (EN + UK)
- [ ] Runbook «Як інспектувати SOC» (UA)
- [ ] AI-методологічний документ (UA primary, EN переклад)
- [ ] Prompt-бібліотека
- [ ] Lessons learned
- [ ] Усі 6 файлів завантажено в `s3://wic-krakow-2026/public/inspector/`

**Бонус:**
- [ ] Усі 8 перевірок
- [ ] Read-only публічна сторінка `/inspection-report` — аудиторський звіт у форматі, придатному для показу
- [ ] Авто-публікація ваших знахідок на спільну landing-сторінку `https://wic-krakow.sanctumsec.com/`

---

## 13. Stretch goals (якщо випереджаєте)

- Per-tool «compliance score» (зважене середнє перевірок) із трекінгом у часі
- Email / Telegram-дайджест наприкінці дня зі зведенням комплаєнсу кожного інструмента
- Розширити навчальний пакет зразковим 5-сторінковим «інспекційним звітом», який можна передати керівнику підприємства після реального аудиту
- Короткий screencast із вашим інструментом, озвучений українською, у навчальних матеріалах

Вдалого полювання — і насолоджуйтеся статусом команди, яка має право бути правою.

---

## Наскрізні цілі Дня 3 (AI-CTI-теми)

На додачу до специфічних-для-команди deliverable-ів вище, **наступні три теми з програми Дня 3 (Модулі 4–6) мають помітно проявитися десь у вашому інструменті, адмін-сторінці або навчальних артефактах.** Claude Code — те, що робить це виконуваним за один день — використовуйте його.

### Ціль 1 — AI-Augmented CTI

Використайте Claude (чи будь-який LLM) для автоматизації щонайменше одного кроку CTI-циклу *всередині* вашого інструмента: extraction, classification, correlation чи enrichment threat intelligence. Це — практична реалізація Модуля 4.

### Ціль 2 — TTP та AI-enabled attack patterns

Коли мапуєте поведінку в MITRE ATT&CK, розпізнавайте також TTP, які AI-enabled зловмисник створить інакше: LLM-генерований phishing, автоматизований OSINT-driven recon, машинно-генеровані polymorphic payloads, scripted beaconing на незвичних інтервалах. Відобразіть це у ваших детекціях, гіпотезах, тегах IOC чи playbook-ах.

### Ціль 3 — AI Social Engineering (offense *та* defense)

Справжні зловмисники зараз використовують AI для масштабування phishing-у, voice-cloning, impersonation. Ваш інструмент має хоч раз цього торкнутися: захопити SE-артефакт, тегнути один, алертити на один, збагатити один — або, щонайменше, документувати, *як би* ваш інструмент реагував на AI-enabled SE-спробу.

### Як кожна ціль потрапляє у вашу роботу — специфічна для команди

- **AI-Augmented CTI:** Ваш власний інструмент *є* AI-assisted build. Документуйте у methodology-journal-і кожне місце, де ви використали Claude для CTI-задач (написання правил, чеклістів, inspection-звітів). Це — навчальний матеріал Модуля 4 дослівно.
- **TTP / AI attack patterns:** Додайте у ваш inspection-чекліст рядок на команду, що запитує: *«Does this tool detect or reason about AI-enabled attack patterns?»* Вимагайте evidence (правило, тег, рядок логу) для «галочки». Компаєнс-дашборд має показувати, хто пройшов цей аудит.
- **AI social engineering:** Додайте спеціальний SE-аудит: *«Does this tool's admin page resist credential harvesting?»* (стуканіть fake phishing-kit POST-ом, очікуйте 401 + логований security event). Runbook має містити розділ про SE-resilience.
