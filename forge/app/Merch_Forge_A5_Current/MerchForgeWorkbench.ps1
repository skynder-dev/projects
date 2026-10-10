# Merch Forge Workbench
# Native WPF desktop UI. Internal alpha build; not owner-accepted visual design.
# Version: 2.22.1-third-review

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Security

[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

$script:AppVersion = '2.22.1-forge-third-review'
$script:MinimumBackendVersion = [version]'0.2.70'
$script:ApiUrl = 'https://ldlhnedbqeqcbqelhuhm.supabase.co/functions/v1/forge-app'
$script:OwnerKey = $null
$script:Session = $null
$script:Queue = @()
$script:Current = $null
$script:Dirty = $false
$script:Busy = $false
$script:RestoreSourceRevisionId = $null
$script:Publication = $null
$script:PublicationDirty = $false
$script:ReviewWorkspace = $null
$script:Delivery = $null
$script:PendingOwnerActionKeys = @{}
$script:BackendVersion = $null
$script:ConnectionState = 'Not connected'
$script:OfflineMode = $false
$script:OfflineSnapshotMode = $false
$script:ProductSection = 'home'
$script:DiscoverSnapshot = $null
$script:DiscoverLoadedAt = $null
$script:LastDiagnostic = [ordered]@{ when=''; category=''; http_status=0; action=''; technical=''; user_message='' }
$script:StateRoot = Join-Path $env:LOCALAPPDATA 'MerchForge'
$script:KeyPath = Join-Path $script:StateRoot 'owner.key'
$script:LogRoot = Join-Path $script:StateRoot 'logs'
$script:RuntimeLogPath = Join-Path $script:LogRoot 'MerchForge-workbench-runtime.log'
$script:PreviewCacheRoot = Join-Path $script:StateRoot 'preview-cache-v1'
$script:PreviewCacheMaxFiles = 32
$script:PreviewCacheMaxBytes = 52428800
$script:PreviewCacheContract = 'forge.preview_cache.v1'
$script:LastPreviewSource = ''
$script:ConceptLoadInProgress = $false
$script:LocalePath = Join-Path $script:StateRoot 'ui-locale.txt'
$script:QueueSnapshotPath = Join-Path $script:StateRoot 'queue-snapshot.json'
$script:EmbeddedIdeasPath = Join-Path $PSScriptRoot 'Data\Forge.LastKnownIdeas.json'
$script:GenerationProvidersPath = Join-Path $PSScriptRoot 'Data\Forge.GenerationProviders.json'
$script:LocalCheckTemplatePath = Join-Path $PSScriptRoot 'Data\LocalCheckEvidence.template.json'
$script:SalesImportReadmePath = Join-Path $PSScriptRoot 'Data\SalesImport_README.txt'
$script:LocalGenerationProviderMode = ''
$script:LocalCoreRoot = Join-Path $script:StateRoot 'local-core-v1'
$script:LocalCoreStatePath = Join-Path $script:LocalCoreRoot 'state.json'
$script:LocalCoreBackupPath = Join-Path $script:LocalCoreRoot 'state.lastgood.json'
$script:LocalCoreArtworkRoot = Join-Path $script:LocalCoreRoot 'artwork'
$script:LocalCorePackageRoot = Join-Path $script:LocalCoreRoot 'packages'
$script:LocalCoreExportRoot = Join-Path $script:LocalCoreRoot 'exports'
$script:LocalCoreImportRoot = Join-Path $script:LocalCoreRoot 'imports'
$script:GenerationRoot = Join-Path $script:StateRoot 'generation-v1'
$script:GenerationOutboxRoot = Join-Path $script:GenerationRoot 'outbox'
$script:GenerationResultRoot = Join-Path $script:GenerationRoot 'results'
$script:GenerationReceiptRoot = Join-Path $script:GenerationRoot 'receipts'
$script:GenerationAttemptRoot = Join-Path $script:GenerationRoot 'attempts'
$script:GenerationWorkerPath = Join-Path $PSScriptRoot 'MerchForgeGenerationWorker.ps1'
$script:ProviderConfigPath = Join-Path $script:StateRoot 'provider-config.json'
$script:ProviderSecretRoot = Join-Path $script:StateRoot 'provider-secrets'
$script:ProviderSecretPath = Join-Path $script:ProviderSecretRoot 'openai-image.sec'
$script:SupportedLocales = @('en','ru','es')
$script:Locale = 'en'
$script:LocaleChangeInProgress = $false
$script:ModuleRoot = Join-Path $PSScriptRoot 'Modules'
. (Join-Path $script:ModuleRoot 'Forge.DataAdapter.ps1')
. (Join-Path $script:ModuleRoot 'Forge.GenerationProvider.ps1')
. (Join-Path $script:ModuleRoot 'Forge.ImageValidation.ps1')
. (Join-Path $script:ModuleRoot 'Forge.GenerationWorkerBridge.ps1')
. (Join-Path $script:ModuleRoot 'Forge.LocalCore.ps1')
. (Join-Path $script:ModuleRoot 'Forge.ResearchDrafts.ps1')
. (Join-Path $script:ModuleRoot 'Forge.Pipeline.ps1')
. (Join-Path $script:ModuleRoot 'Forge.MessageLocalization.ps1')
. (Join-Path $script:ModuleRoot 'Forge.CheckAttestation.ps1')
. (Join-Path $script:ModuleRoot 'Forge.AmazonProfile.ps1')
. (Join-Path $script:ModuleRoot 'Forge.DataBackup.ps1')
. (Join-Path $script:ModuleRoot 'Forge.ListingHints.ps1')
. (Join-Path $script:ModuleRoot 'Forge.ProductNavigation.ps1')
. (Join-Path $script:ModuleRoot 'Forge.BackendStatus.ps1')
. (Join-Path $script:ModuleRoot 'Forge.Localization.ps1')
. (Join-Path $script:ModuleRoot 'Forge.UI.Layout.ps1')
. (Join-Path $script:ModuleRoot 'Forge.Diagnostics.ps1')
. (Join-Path $script:ModuleRoot 'Forge.Gates.ps1')
. (Join-Path $script:ModuleRoot 'Forge.DataViews.ps1')
. (Join-Path $script:ModuleRoot 'Forge.DomainActions.ps1')
. (Join-Path $script:ModuleRoot 'Forge.Media.ps1')

$script:UiText = @{
    en = @{
        'language.label'='Language'; 'language.en'='English'; 'language.ru'='Russian'; 'language.es'='Spanish';
        'language.status.en'='English'; 'language.status.ru'='Русский'; 'language.status.es'='Español';
        'shell.about'='About'; 'shell.diagnostics'='Diagnostics'; 'shell.refresh'='Refresh'; 'shell.signout'='Sign out'; 'window.title'='Merch Forge · Product Workspace';
        'login.remember'='Remember on this Windows account'; 'login.open'='Open Workbench'; 'login.saved'='Saved access is protected for your Windows account.';
        'backend.unavailable'='Backend unavailable'; 'backend.retry'='Retry'; 'backend.retrying'='Retrying…'; 'backend.offline.status'='Workbench open · waiting for service'; 'backend.offline.body'='Live workspace data is temporarily unavailable. Use Retry in the gold status card.';
        'queue.concepts'='Ideas'; 'queue.search'='Search'; 'queue.status'='Status'; 'queue.sort'='Sort'; 'queue.shown'='{0} shown'; 'queue.cached'='{0} cached ideas'; 'queue.snapshot'='Local snapshot'; 'queue.empty'='No ideas yet'; 'queue.empty.body'='There are no ideas in the local snapshot.'; 'queue.nomatches'='No matches'; 'queue.nomatches.body'='Try another search or choose All statuses.';
        'queue.placeholder'='Title, slogan or profession'; 'queue.all'='All statuses'; 'queue.ready'='Ready to generate'; 'queue.editing'='Editing'; 'queue.requested'='Generation requested'; 'queue.variants'='Has variants'; 'queue.accepted'='Accepted'; 'queue.blocked'='Blocked'; 'sort.score'='Score: high to low'; 'sort.title'='Title: A to Z'; 'sort.workflow'='Workflow status';
        'tab.overview'='Overview'; 'tab.visuals'='Visuals & Generate'; 'tab.history'='History'; 'tab.evidence'='Evidence'; 'tab.delivery'='Delivery'; 'tab.publication'='Publication'; 'tab.edit'='Edit';
        'overview.review'='Review visuals / generation'; 'overview.edit'='Edit concept';
        'locale.dirty'='Save or discard current edits before changing UI language.';
        'nav.home'='Home'; 'nav.discover'='Discover'; 'nav.ideas'='Ideas'; 'nav.artwork'='Artwork'; 'nav.checks'='Checks'; 'nav.publish'='Publish'; 'nav.portfolio'='Portfolio'; 'nav.performance'='Performance';
        'product.workspace'='Product workspace'; 'section.kicker'='PRODUCT WORKSPACE'; 'discover.title'='Discover / Research'; 'discover.body'='Ranked market opportunities backed by Forge research, evidence and concept depth.'; 'discover.niches'='Niches'; 'discover.notes'='Research notes'; 'discover.sources'='Active sources'; 'discover.concepts'='Concepts'; 'discover.rank'='Ranked opportunities'; 'discover.detail'='Opportunity detail'; 'discover.recent'='Recent research'; 'discover.source.list'='Evidence sources'; 'discover.loading'='Loading live research…'; 'discover.ready'='Live research loaded'; 'discover.offline'='Live research is unavailable. No market data is fabricated.'; 'discover.refresh'='Refresh research';
        'home.title'='Business dashboard'; 'home.body'='Ideas, products and results in one place — from first concept to sales.'; 'home.status'='WORKSPACE STATUS'; 'home.ready'='Connected'; 'home.ready.body'='Live workspace data is available.'; 'home.offline'='Offline workspace'; 'home.offline.body'='The app stays usable. Live data will appear when the service reconnects.';
        'metric.published'='Published'; 'metric.sales30'='Sales · 30 days'; 'metric.royalties30'='Royalties · 30 days'; 'metric.attention'='Needs attention'; 'metric.waiting'='Waiting for live data';
        'home.pipeline'='Pipeline'; 'home.pipeline.body'='Move products through clear stages without mixing product work with application internals.'; 'home.alex'='Alex Needed'; 'home.alex.offline'='Reconnect to load decisions that need your attention.'; 'home.performance'='Performance snapshot'; 'home.performance.offline'='Sales and royalties will appear here when live commerce data is connected.';
        'section.ideas.title'='Ideas'; 'section.ideas.body'='Choose an idea from the list to review the concept and decide what deserves artwork.'; 'owner.review.title'='Owner decision'; 'owner.review.body'='Choose what happens to this exact idea revision. Decisions are saved locally in Forge; they do not Generate, Accept or Publish.'; 'owner.review.none'='No decision yet'; 'owner.review.saved'='Current decision'; 'owner.review.progress'='{0} of {1} ideas decided · KEEP {2} · EDIT {3} · REGEN {4} · SKIP {5}'; 'owner.review.keep'='KEEP'; 'owner.review.edit'='EDIT'; 'owner.review.regen'='REGEN'; 'owner.review.skip'='SKIP'; 'owner.review.clear'='Clear decision'; 'section.artwork.title'='Artwork'; 'section.artwork.body'='Choose an idea to generate, compare and review artwork.'; 'section.checks.title'='Checks'; 'section.checks.body'='Choose an idea to review IP, policy, print and readiness evidence.'; 'section.publish.title'='Publish'; 'section.publish.body'='Choose an accepted product to prepare listing metadata and delivery.';
        'portfolio.title'='Portfolio'; 'portfolio.body'='Published products, channels and listing health.'; 'portfolio.empty'='Connect live commerce data to load your published products.'; 'performance.title'='Performance'; 'performance.body'='Sales, royalties and product momentum across 7 / 30 / 90 days.'; 'performance.empty'='Connect live commerce data to load sales and royalty performance.';
        'context.history'='History'; 'context.delivery'='Delivery'; 'context.edit'='Edit'; 'system.connected'='Connected'; 'system.offline'='Offline'; 'system.notconnected'='Not connected'; 'role.readonly'='Read-only for this role'; 'status.unsaved'='Unsaved changes'; 'status.unsavedlisting'='Unsaved listing changes';
        'offline.snapshot.meta'='Local snapshot · live service unavailable'; 'local.brief'='Export generation brief'; 'local.import.art'='Import artwork…'; 'local.accept'='Accept local artwork'; 'local.import.checks'='Import check evidence…'; 'local.package'='Build local Amazon package'; 'local.sales'='Import sales CSV…'; 'local.publication.receipt'='Import publication receipt…'; 'local.fallback'='Local-first fallback'; 'local.checks'='Local check evidence'; 'local.sales.title'='Local sales import'; 'offline.snapshot.warning'='You are viewing the last known idea snapshot. Reconnect for live details.'; 'offline.snapshot.next'='Reconnect to load live evidence, artwork and publication state.';
    };
    ru = @{
        'language.label'='Язык'; 'language.en'='Английский'; 'language.ru'='Русский'; 'language.es'='Испанский';
        'language.status.en'='English'; 'language.status.ru'='Русский'; 'language.status.es'='Español';
        'shell.about'='О программе'; 'shell.diagnostics'='Диагностика'; 'shell.refresh'='Обновить'; 'shell.signout'='Выйти'; 'window.title'='Merch Forge · Рабочая область';
        'login.remember'='Запомнить на этой учётной записи Windows'; 'login.open'='Открыть рабочую панель'; 'login.saved'='Сохранённый доступ защищён для вашей учётной записи Windows.';
        'backend.unavailable'='Сервис недоступен'; 'backend.retry'='Повторить'; 'backend.retrying'='Подключение…'; 'backend.offline.status'='Рабочая панель открыта · ждём сервис'; 'backend.offline.body'='Данные рабочего пространства временно недоступны. Нажмите «Повторить» в золотистой плашке.';
        'queue.concepts'='Идеи'; 'queue.search'='Поиск'; 'queue.status'='Статус'; 'queue.sort'='Сортировка'; 'queue.shown'='Показано: {0}'; 'queue.cached'='Локальных идей: {0}'; 'queue.snapshot'='Локальный снимок'; 'queue.empty'='Идей пока нет'; 'queue.empty.body'='В локальном снимке пока нет идей.'; 'queue.nomatches'='Нет совпадений'; 'queue.nomatches.body'='Попробуйте другой поиск или выберите «Все статусы».';
        'queue.placeholder'='Название, слоган или профессия'; 'queue.all'='Все статусы'; 'queue.ready'='Готово к генерации'; 'queue.editing'='Редактирование'; 'queue.requested'='Генерация запрошена'; 'queue.variants'='Есть варианты'; 'queue.accepted'='Принято'; 'queue.blocked'='Заблокировано'; 'sort.score'='Оценка: по убыванию'; 'sort.title'='Название: А–Я'; 'sort.workflow'='По статусу';
        'tab.overview'='Обзор'; 'tab.visuals'='Макеты и генерация'; 'tab.history'='История'; 'tab.evidence'='Проверки'; 'tab.delivery'='Передача'; 'tab.publication'='Публикация'; 'tab.edit'='Редактирование';
        'overview.review'='Просмотреть макеты / генерацию'; 'overview.edit'='Редактировать идею';
        'locale.dirty'='Сохраните или отмените текущие правки перед сменой языка интерфейса.';
        'nav.home'='Главная'; 'nav.discover'='Поиск'; 'nav.ideas'='Идеи'; 'nav.artwork'='Макеты'; 'nav.checks'='Проверки'; 'nav.publish'='Публикация'; 'nav.portfolio'='Портфолио'; 'nav.performance'='Результаты';
        'product.workspace'='Рабочая область продукта'; 'section.kicker'='РАБОЧАЯ ОБЛАСТЬ ПРОДУКТА'; 'discover.title'='Поиск / Исследование'; 'discover.body'='Рейтинг рыночных возможностей на основе исследований Forge, доказательств и глубины концептов.'; 'discover.niches'='Ниши'; 'discover.notes'='Исследования'; 'discover.sources'='Активные источники'; 'discover.concepts'='Концепты'; 'discover.rank'='Рейтинг возможностей'; 'discover.detail'='Детали возможности'; 'discover.recent'='Последние исследования'; 'discover.source.list'='Источники доказательств'; 'discover.loading'='Загружаю живые исследования…'; 'discover.ready'='Живые исследования загружены'; 'discover.offline'='Живые исследования недоступны. Рыночные данные не выдумываются.'; 'discover.refresh'='Обновить исследование';
        'home.title'='Бизнес-панель'; 'home.body'='Идеи, товары и результаты в одном месте — от первого концепта до продаж.'; 'home.status'='СОСТОЯНИЕ РАБОЧЕЙ ОБЛАСТИ'; 'home.ready'='Подключено'; 'home.ready.body'='Актуальные данные рабочего пространства доступны.'; 'home.offline'='Офлайн-режим'; 'home.offline.body'='Приложение остаётся доступным. Актуальные данные появятся после восстановления сервиса.';
        'metric.published'='Опубликовано'; 'metric.sales30'='Продажи · 30 дней'; 'metric.royalties30'='Вознаграждения · 30 дней'; 'metric.attention'='Требует внимания'; 'metric.waiting'='Ждём актуальные данные';
        'home.pipeline'='Этапы'; 'home.pipeline.body'='Проводите товары по понятным этапам, не смешивая работу над продуктом с внутренностями приложения.'; 'home.alex'='Нужно от Алекса'; 'home.alex.offline'='Подключитесь к сервису, чтобы загрузить решения, требующие вашего внимания.'; 'home.performance'='Сводка результатов'; 'home.performance.offline'='Продажи и вознаграждения появятся здесь после подключения коммерческих данных.';
        'section.ideas.title'='Идеи'; 'section.ideas.body'='Выберите идею слева, чтобы оценить концепт и решить, какой из них заслуживает макета.'; 'owner.review.title'='Решение владельца'; 'owner.review.body'='Выберите, что делать именно с этой ревизией идеи. Решение сохраняется локально в Forge и само не запускает Generate, Accept или Publish.'; 'owner.review.none'='Решения пока нет'; 'owner.review.saved'='Текущее решение'; 'owner.review.progress'='Решено {0} из {1} · ОСТАВИТЬ {2} · ИЗМЕНИТЬ {3} · ЗАНОВО {4} · ПРОПУСТИТЬ {5}'; 'owner.review.keep'='ОСТАВИТЬ'; 'owner.review.edit'='ИЗМЕНИТЬ'; 'owner.review.regen'='ЗАНОВО'; 'owner.review.skip'='ПРОПУСТИТЬ'; 'owner.review.clear'='Сбросить решение'; 'section.artwork.title'='Макеты'; 'section.artwork.body'='Выберите идею, чтобы создавать, сравнивать и оценивать макеты.'; 'section.checks.title'='Проверки'; 'section.checks.body'='Выберите идею, чтобы проверить права, правила площадки, печать и готовность.'; 'section.publish.title'='Публикация'; 'section.publish.body'='Выберите принятый товар, чтобы подготовить карточку и передачу на площадку.';
        'portfolio.title'='Портфолио'; 'portfolio.body'='Опубликованные товары, площадки и состояние карточек.'; 'portfolio.empty'='Подключите коммерческие данные, чтобы загрузить опубликованные товары.'; 'performance.title'='Результаты'; 'performance.body'='Продажи, вознаграждения и динамика товаров за 7 / 30 / 90 дней.'; 'performance.empty'='Подключите коммерческие данные, чтобы загрузить продажи и вознаграждения.';
        'context.history'='История'; 'context.delivery'='Передача'; 'context.edit'='Редактировать'; 'system.connected'='Подключено'; 'system.offline'='Офлайн'; 'system.notconnected'='Нет подключения'; 'role.readonly'='Только просмотр для этой роли'; 'status.unsaved'='Есть несохранённые изменения'; 'status.unsavedlisting'='Есть несохранённые изменения карточки';
        'offline.snapshot.meta'='Локальный снимок · сервис недоступен'; 'local.brief'='Экспортировать бриф генерации'; 'local.import.art'='Импортировать макет…'; 'local.accept'='Принять локальный макет'; 'local.import.checks'='Импортировать проверки…'; 'local.package'='Собрать локальный пакет Amazon'; 'local.sales'='Импортировать CSV продаж…'; 'local.publication.receipt'='Импортировать подтверждение публикации…'; 'local.fallback'='Локальный резервный режим'; 'local.checks'='Локальные проверки'; 'local.sales.title'='Локальный импорт продаж'; 'offline.snapshot.warning'='Показан последний известный снимок идеи. Подключитесь к сервису для актуальных данных.'; 'offline.snapshot.next'='Подключитесь к сервису, чтобы загрузить актуальные проверки, макеты и состояние публикации.';
    };
    es = @{
        'language.label'='Idioma'; 'language.en'='Inglés'; 'language.ru'='Ruso'; 'language.es'='Español';
        'language.status.en'='English'; 'language.status.ru'='Русский'; 'language.status.es'='Español';
        'shell.about'='Acerca de'; 'shell.diagnostics'='Diagnóstico'; 'shell.refresh'='Actualizar'; 'shell.signout'='Cerrar sesión'; 'window.title'='Merch Forge · Espacio de producto';
        'login.remember'='Recordar en esta cuenta de Windows'; 'login.open'='Abrir el panel'; 'login.saved'='El acceso guardado está protegido para tu cuenta de Windows.';
        'backend.unavailable'='Servicio no disponible'; 'backend.retry'='Reintentar'; 'backend.retrying'='Reconectando…'; 'backend.offline.status'='Panel abierto · esperando el servicio'; 'backend.offline.body'='Los datos del espacio de trabajo no están disponibles temporalmente. Pulsa «Reintentar» en el aviso dorado.';
        'queue.concepts'='Ideas'; 'queue.search'='Buscar'; 'queue.status'='Estado'; 'queue.sort'='Ordenar'; 'queue.shown'='Mostradas: {0}'; 'queue.cached'='Ideas locales: {0}'; 'queue.snapshot'='Copia local'; 'queue.empty'='Todavía no hay ideas'; 'queue.empty.body'='La copia local todavía no contiene ideas.'; 'queue.nomatches'='Sin resultados'; 'queue.nomatches.body'='Prueba otra búsqueda o selecciona «Todos los estados».';
        'queue.placeholder'='Título, eslogan o profesión'; 'queue.all'='Todos los estados'; 'queue.ready'='Lista para generar'; 'queue.editing'='En edición'; 'queue.requested'='Generación solicitada'; 'queue.variants'='Tiene variantes'; 'queue.accepted'='Aceptada'; 'queue.blocked'='Bloqueada'; 'sort.score'='Puntuación: de mayor a menor'; 'sort.title'='Título: A–Z'; 'sort.workflow'='Estado del flujo';
        'tab.overview'='Resumen'; 'tab.visuals'='Diseños y generación'; 'tab.history'='Historial'; 'tab.evidence'='Comprobaciones'; 'tab.delivery'='Entrega'; 'tab.publication'='Publicación'; 'tab.edit'='Editar';
        'overview.review'='Revisar diseños / generación'; 'overview.edit'='Editar idea';
        'locale.dirty'='Guarda o descarta los cambios actuales antes de cambiar el idioma de la interfaz.';
        'nav.home'='Inicio'; 'nav.discover'='Descubrir'; 'nav.ideas'='Ideas'; 'nav.artwork'='Diseños'; 'nav.checks'='Comprobaciones'; 'nav.publish'='Publicar'; 'nav.portfolio'='Portafolio'; 'nav.performance'='Rendimiento';
        'product.workspace'='Espacio de producto'; 'section.kicker'='ESPACIO DE PRODUCTO'; 'discover.title'='Descubrir / Investigación'; 'discover.body'='Oportunidades de mercado clasificadas con investigación, evidencia y profundidad conceptual de Forge.'; 'discover.niches'='Nichos'; 'discover.notes'='Notas de investigación'; 'discover.sources'='Fuentes activas'; 'discover.concepts'='Conceptos'; 'discover.rank'='Oportunidades clasificadas'; 'discover.detail'='Detalle de oportunidad'; 'discover.recent'='Investigación reciente'; 'discover.source.list'='Fuentes de evidencia'; 'discover.loading'='Cargando investigación en vivo…'; 'discover.ready'='Investigación en vivo cargada'; 'discover.offline'='La investigación en vivo no está disponible. No se inventan datos de mercado.'; 'discover.refresh'='Actualizar investigación';
        'home.title'='Panel de negocio'; 'home.body'='Ideas, productos y resultados en un solo lugar — desde el primer concepto hasta las ventas.'; 'home.status'='ESTADO DEL ESPACIO'; 'home.ready'='Conectado'; 'home.ready.body'='Los datos actuales del espacio de trabajo están disponibles.'; 'home.offline'='Modo sin conexión'; 'home.offline.body'='La aplicación sigue disponible. Los datos actuales aparecerán cuando se restablezca el servicio.';
        'metric.published'='Publicados'; 'metric.sales30'='Ventas · 30 días'; 'metric.royalties30'='Regalías · 30 días'; 'metric.attention'='Requiere atención'; 'metric.waiting'='Esperando datos actuales';
        'home.pipeline'='Etapas'; 'home.pipeline.body'='Mueve los productos por etapas claras sin mezclar el trabajo del producto con la ingeniería interna.'; 'home.alex'='Pendiente de Alex'; 'home.alex.offline'='Conéctate al servicio para cargar las decisiones que requieren tu atención.'; 'home.performance'='Resumen de rendimiento'; 'home.performance.offline'='Las ventas y regalías aparecerán aquí cuando se conecten los datos comerciales.';
        'section.ideas.title'='Ideas'; 'section.ideas.body'='Selecciona una idea de la lista para revisar el concepto y decidir cuál merece un diseño.'; 'owner.review.title'='Decisión del propietario'; 'owner.review.body'='Elige qué hacer con esta revisión exacta. La decisión se guarda localmente en Forge y no ejecuta Generate, Accept ni Publish.'; 'owner.review.none'='Sin decisión'; 'owner.review.saved'='Decisión actual'; 'owner.review.progress'='{0} de {1} ideas decididas · MANTENER {2} · EDITAR {3} · REGENERAR {4} · OMITIR {5}'; 'owner.review.keep'='MANTENER'; 'owner.review.edit'='EDITAR'; 'owner.review.regen'='REGENERAR'; 'owner.review.skip'='OMITIR'; 'owner.review.clear'='Borrar decisión'; 'section.artwork.title'='Diseños'; 'section.artwork.body'='Selecciona una idea para generar, comparar y revisar diseños.'; 'section.checks.title'='Comprobaciones'; 'section.checks.body'='Selecciona una idea para revisar propiedad intelectual, políticas, impresión y preparación.'; 'section.publish.title'='Publicar'; 'section.publish.body'='Selecciona un producto aceptado para preparar la ficha y la entrega a la plataforma.';
        'portfolio.title'='Portafolio'; 'portfolio.body'='Productos publicados, plataformas y estado de las fichas.'; 'portfolio.empty'='Conecta los datos comerciales para cargar tus productos publicados.'; 'performance.title'='Rendimiento'; 'performance.body'='Ventas, regalías y evolución de los productos durante 7 / 30 / 90 días.'; 'performance.empty'='Conecta los datos comerciales para cargar ventas y regalías.';
        'context.history'='Historial'; 'context.delivery'='Entrega'; 'context.edit'='Editar'; 'system.connected'='Conectado'; 'system.offline'='Sin conexión'; 'system.notconnected'='Sin conexión'; 'role.readonly'='Solo lectura para este rol'; 'status.unsaved'='Cambios sin guardar'; 'status.unsavedlisting'='Cambios de ficha sin guardar';
        'offline.snapshot.meta'='Copia local · servicio no disponible'; 'local.brief'='Exportar brief de generación'; 'local.import.art'='Importar diseño…'; 'local.accept'='Aceptar diseño local'; 'local.import.checks'='Importar comprobaciones…'; 'local.package'='Crear paquete local de Amazon'; 'local.sales'='Importar CSV de ventas…'; 'local.publication.receipt'='Importar comprobante de publicación…'; 'local.fallback'='Modo local de respaldo'; 'local.checks'='Comprobaciones locales'; 'local.sales.title'='Importación local de ventas'; 'offline.snapshot.warning'='Se muestra la última copia conocida de la idea. Conéctate al servicio para obtener datos actuales.'; 'offline.snapshot.next'='Conéctate al servicio para cargar comprobaciones, diseños y estado de publicación actuales.';
    }
}


$script:StaticUiTranslations = @{
    ru = @{
        'Merch Forge'='Merch Forge';
        'Internal Workbench'='Внутренняя рабочая панель';
        'Workspace access'='Доступ к рабочему пространству';
        'Language'='Язык';
        'English'='Английский';
        'Saved access is protected for your Windows account.'='Сохранённый доступ защищён для вашей учётной записи Windows.';
        '010 · reconciled candidate'='010 · согласованный кандидат';
        'Not connected'='Нет подключения';
        'Working…'='Выполняется…';
        'Concepts'='Концепты';
        '0'='0';
        'Search'='Поиск';
        'Title, slogan or profession'='Название, слоган или профессия';
        'Status'='Статус';
        'Sort'='Сортировка';
        'No concepts'='Нет концептов';
        'There are no concepts in this workspace yet.'='В этом рабочем пространстве пока нет концептов.';
        'Select a concept'='Выберите концепт';
        'The idea'='Идея';
        'Select a concept to see its overview.'='Выберите концепт, чтобы увидеть обзор.';
        'Who it is for'='Для кого';
        'Why someone would want it'='Почему это захотят купить';
        'What makes it different'='Чем отличается';
        'Visual direction'='Визуальное направление';
        'Meaning / context'='Смысл / контекст';
        'Current state'='Текущее состояние';
        'Generation brief'='Бриф генерации';
        'Select a concept to see the prepared generation brief.'='Выберите концепт, чтобы увидеть подготовленный бриф генерации.';
        'Prepared automatically from the concept. Edit only if you want to change the creative direction.'='Подготовлено автоматически из концепта. Редактируйте только если хотите изменить творческое направление.';
        'Generation runs'='Запуски генерации';
        'Variants'='Варианты';
        'Variant'='Вариант';
        'Visual preview'='Предпросмотр изображения';
        'Artwork is fitted to the frame so the full design remains visible.'='Изображение вписано в рамку так, чтобы дизайн был виден целиком.';
        'Primary selection'='Основной выбор';
        'Select a variant'='Выберите вариант';
        'Comparison selection'='Выбор для сравнения';
        'Select a second variant to compare'='Выберите второй вариант для сравнения';
        'Compare'='Сравнить';
        'Review note (does not Accept)'='Заметка к просмотру (не означает Accept)';
        'Acceptance'='Принятие';
        'Large image files stay local to this computer. Preview access is handled safely without showing file-system locations.'='Большие файлы изображений остаются на этом компьютере. Предпросмотр работает безопасно без показа путей файловой системы.';
        'Revisions'='Версии';
        'Activity'='Активность';
        'Current'='Текущая';
        'Selected revision'='Выбранная версия';
        'Selected activity evidence'='Данные выбранного события';
        'Why this concept exists'='Почему существует этот концепт';
        'Insider / profession context'='Профессиональный контекст';
        'Meaning / joke'='Смысл / шутка';
        'Evidence & IP readiness'='Доказательства и готовность IP';
        'Score dimensions'='Показатели оценки';
        'Warnings / blockers'='Предупреждения / блокеры';
        'Exact accepted lineage'='Точная цепочка принятой версии';
        'Version-specific gates'='Проверки конкретной версии';
        'Readiness'='Готовность';
        'External action boundary'='Граница внешних действий';
        'Design'='Дизайн';
        'Listing draft'='Черновик листинга';
        'Forge prepares this from the concept automatically. Manual edits are optional.'='Forge готовит это автоматически из концепта. Ручные правки необязательны.';
        'Listing title'='Название листинга';
        'Brand'='Бренд';
        'Bullet 1'='Пункт 1';
        'Bullet 2'='Пункт 2';
        'Description'='Описание';
        'Keywords'='Ключевые слова';
        'Why changed? (optional)'='Почему изменено? (необязательно)';
        'Listing versions'='Версии листинга';
        'No listing versions yet.'='Версий листинга пока нет.';
        'Checks'='Проверки';
        'Economics'='Экономика';
        'Preflight'='Предпроверка';
        'Packages'='Пакеты';
        'Preparation only. Export does not mean saved locally; Social handoff does not mean approval; package preparation does not submit or publish.'='Только подготовка. Export не означает локальное сохранение; передача в Social не означает одобрение; подготовка пакета ничего не отправляет и не публикует.';
        'Submit'='Отправка';
        'Locked external action'='Внешнее действие заблокировано';
        'Title'='Название';
        'Hook / slogan'='Хук / слоган';
        'Concept'='Концепт';
        'Target buyer'='Целевой покупатель';
        'Purchase reason'='Причина покупки';
        'Differentiation'='Отличие';
        'Edit reason (optional)'='Причина правки (необязательно)';
        'Disconnected'='Отключено';
        'About Merch Forge'='О Merch Forge';
        'EN'='EN';
        'RU'='RU';
        'ES'='ES';
        'Remember on this Windows account'='Запомнить на этой учётной записи Windows';
        'Open Workbench'='Открыть Workbench';
        'About'='О программе';
        'Diagnostics'='Диагностика';
        'Refresh'='Обновить';
        'Sign out'='Выйти';
        'All statuses'='Все статусы';
        'Ready to generate'='Готово к генерации';
        'Editing'='Редактирование';
        'Generation requested'='Генерация запрошена';
        'Has variants'='Есть варианты';
        'Accepted'='Принято';
        'Blocked'='Заблокировано';
        'In progress'='В процессе';
        'No current analysis warning.'='Текущих предупреждений анализа нет.';
        'The visual is accepted. Review Delivery and Publication readiness when you are ready.'='Изображение принято. Когда будете готовы, проверьте готовность разделов «Доставка» и «Публикация».';
        'Generated visuals are available. Review them in Visuals & Generate before any Accept decision.'='Сгенерированные изображения готовы. Просмотрите их в разделе «Изображения и генерация» до любого решения Accept.';
        'Generation has been requested. Review the result when it arrives; do not submit anything externally.'='Генерация запрошена. Просмотрите результат, когда он появится; ничего не отправляйте во внешние системы.';
        'An edited brief is current. Review it, then generate only when you choose.'='Сейчас активен отредактированный бриф. Проверьте его и запускайте генерацию только по своему решению.';
        'This concept is blocked. Review the evidence and blocker before generating.'='Этот концепт заблокирован. Перед генерацией проверьте доказательства и причину блокировки.';
        'The brief is ready. Review the idea first; Generate remains a separate explicit action.'='Бриф готов. Сначала проверьте идею; Generate остаётся отдельным явным действием.';
        'Score: high to low'='Оценка: по убыванию';
        'Title: A to Z'='Название: А–Я';
        'Workflow status'='Статус процесса';
        'Save new revision'='Сохранить новую версию';
        'Review visuals / generation'='Просмотреть изображения / генерацию';
        'Edit concept'='Редактировать концепт';
        'Generate variants…'='Сгенерировать варианты…';
        'Accept selected visual'='Принять выбранное изображение';
        'Cancel selected queued request'='Отменить выбранный запрос в очереди';
        'Compare two selected variants'='Сравнить два выбранных варианта';
        'neutral'='нейтрально';
        'favorite'='избранное';
        'reject'='отклонить';
        'Save review event'='Сохранить решение просмотра';
        'Reopen current acceptance'='Отменить текущее принятие';
        'Start new iteration · same brief'='Новая итерация · тот же бриф';
        'Start new iteration · edited brief'='Новая итерация · изменённый бриф';
        'Restore selected as new revision'='Восстановить выбранное как новую версию';
        'Save listing version'='Сохранить версию листинга';
        'Export package'='Подготовить export-пакет';
        'Send to Social'='Передать в Social';
        'Owner export'='Export для владельца';
        'Social source'='Источник для Social';
        'Amazon owner'='Пакет Amazon для владельца';
        'Prepare package'='Подготовить пакет';
        'Close'='Закрыть';
        'Copy diagnostics'='Копировать диагностику';
        'Open log'='Открыть лог';
        'Done'='Готово';
        'Overview'='Обзор';
        'Visuals & Generate'='Изображения и генерация';
        'Technical details'='Технические детали';
        'History'='История';
        'Evidence'='Доказательства';
        'Delivery'='Доставка';
        'Publication'='Публикация';
        'Edit'='Редактирование';
        'Technical details · production spec JSON'='Технические детали · production spec JSON';
        'UI language'='Язык интерфейса';
        'Connect to your Merch Forge workspace and open the workbench'='Подключиться к рабочему пространству Merch Forge и открыть Workbench';
        'Select concept'='Выбрать концепт';
        'UI language. RU/ES use real built-in translations; original creative copy is not translated automatically.'='Язык интерфейса. Русский и испанский используют реальные встроенные переводы; исходный творческий текст не переводится автоматически.';
        'About Merch Forge, this build, and what the workbench does'='О Merch Forge, этой сборке и возможностях Workbench';
        'Open safe in-app connection and runtime diagnostics'='Открыть безопасную диагностику подключения и работы приложения';
        'Reload concepts and current workspace state'='Перезагрузить концепты и текущее состояние рабочего пространства';
        'Sign out and remove saved access from this Windows account'='Выйти и удалить сохранённый доступ с этой учётной записи Windows';
        'Search title, slogan or profession'='Искать по названию, слогану или профессии';
        'Show concepts by workflow status'='Показать концепты по статусу процесса';
        'Sort the concept queue'='Сортировать очередь концептов';
        'Save your edits as a new immutable creative revision'='Сохранить правки как новую неизменяемую творческую версию';
        'Open visual generation and review for this concept'='Открыть генерацию изображений и просмотр для этого концепта';
        'Open the optional creative editor for this concept'='Открыть дополнительный творческий редактор этого концепта';
        'Create a generation request for the exact current revision. This is an explicit owner action.'='Создать запрос генерации для точной текущей версии. Это явное действие владельца.';
        'Accept the exact selected visual after review. This does not publish it.'='Принять точно выбранное изображение после просмотра. Это не публикует его.';
        'Cancel a queued generation request before provider dispatch'='Отменить запрос генерации в очереди до отправки провайдеру';
        'Compare two selected visual variants side by side'='Сравнить два выбранных визуальных варианта рядом';
        'Reject requires a structured reason. Favorite/neutral reason is optional.'='Для отклонения нужна структурированная причина. Для избранного/нейтрального решения причина необязательна.';
        'Optional review note'='Необязательная заметка к просмотру';
        'Save this review decision as a new immutable review event'='Сохранить решение как новое неизменяемое событие просмотра';
        'Required reason when reopening an accepted revision'='Обязательная причина при отмене принятия версии';
        'Revoke the current acceptance and return this concept to review'='Отменить текущее принятие и вернуть концепт на просмотр';
        'Create a new revision using the same brief; generation remains separate'='Создать новую версию с тем же брифом; генерация остаётся отдельным действием';
        'Create a new editable revision; generation remains separate'='Создать новую редактируемую версию; генерация остаётся отдельным действием';
        'Copy the selected historical revision into a new current revision; history is preserved'='Скопировать выбранную историческую версию в новую текущую; история сохраняется';
        'Human-readable actor/action/version timeline; technical events hidden by default'='Понятная история действий и версий; технические события по умолчанию скрыты';
        'Separate keywords with commas or semicolons'='Разделяйте ключевые слова запятыми или точками с запятой';
        'Save listing metadata as a new immutable version; this does not publish'='Сохранить метаданные листинга как новую неизменяемую версию; это не публикует';
        'Prepare exact delivery manifest. Local ZIP is a separate verified step.'='Подготовить точный manifest доставки. Локальный ZIP — отдельный проверяемый шаг.';
        'Prepare minimized outbound Social source envelope. This does not approve or publish anything.'='Подготовить минимизированный исходный пакет для Social. Это ничего не одобряет и не публикует.';
        'Prepare an owner package only. This does not submit or publish anything.'='Подготовить только пакет владельца. Это ничего не отправляет и не публикует.';
        'Close this panel'='Закрыть эту панель';
        'Copy the current diagnostics text to the clipboard'='Скопировать текущий текст диагностики в буфер обмена';
        'Open the local runtime log in Notepad'='Открыть локальный runtime-лог в Блокноте';
        'Listing locale'='Локаль листинга';
        'English (United States)'='Английский (США)';
        'Russian (Russia)'='Русский (Россия)';
        'Spanish (Spain)'='Испанский (Испания)';
        'Local-first fallback'='Локальный рабочий режим';
        'Local check evidence'='Локальные проверки';
        'Local sales import'='Локальный импорт продаж';
        'Local core ready.'='Локальный рабочий контур готов.';
        'No local check evidence imported.'='Локальные данные проверок ещё не импортированы.';
        'No local sales data imported.'='Локальные данные о продажах ещё не импортированы.';
        'Sales · 7 days'='Продажи · 7 дней';
        'Sales · 30 days'='Продажи · 30 дней';
        'Royalties · 30 days'='Роялти · 30 дней';
        'Sales · 90 days'='Продажи · 90 дней';
        'Sales, royalties and product momentum across 7 / 30 / 90 days.'='Продажи, роялти и динамика товаров за 7 / 30 / 90 дней.';
        'Winners'='Лидеры';
        'Needs attention'='Требует внимания';
        'No synthetic performance data is shown.'='Синтетические показатели не отображаются.';
        'Connect live commerce data to load sales and royalty performance.'='Подключите реальные данные продаж, чтобы загрузить продажи и роялти.';
        'Create a local ZIP for manual upload. Merch Forge does not submit it.'='Создать локальный ZIP для ручной загрузки. Merch Forge его не отправляет.';
        'Imported publication receipts'='Импортированные подтверждения публикации';
        'Requires live or imported evidence'='Требует реальных или импортированных данных';
        'Local publication receipts'='Локальные подтверждения публикации';
        'No local publication receipt imported.'='Подтверждение публикации ещё не импортировано.';
    };
    es = @{
        'Merch Forge'='Merch Forge';
        'Internal Workbench'='Panel interno';
        'Workspace access'='Acceso al espacio de trabajo';
        'Language'='Idioma';
        'English'='Inglés';
        'Saved access is protected for your Windows account.'='El acceso guardado está protegido para tu cuenta de Windows.';
        '010 · reconciled candidate'='010 · candidato reconciliado';
        'Not connected'='Sin conexión';
        'Working…'='Trabajando…';
        'Concepts'='Conceptos';
        '0'='0';
        'Search'='Buscar';
        'Title, slogan or profession'='Título, eslogan o profesión';
        'Status'='Estado';
        'Sort'='Ordenar';
        'No concepts'='Sin conceptos';
        'There are no concepts in this workspace yet.'='Todavía no hay conceptos en este espacio de trabajo.';
        'Select a concept'='Selecciona un concepto';
        'The idea'='La idea';
        'Select a concept to see its overview.'='Selecciona un concepto para ver su resumen.';
        'Who it is for'='Para quién es';
        'Why someone would want it'='Por qué alguien lo querría';
        'What makes it different'='Qué lo hace diferente';
        'Visual direction'='Dirección visual';
        'Meaning / context'='Significado / contexto';
        'Current state'='Estado actual';
        'Generation brief'='Brief de generación';
        'Select a concept to see the prepared generation brief.'='Selecciona un concepto para ver el brief de generación preparado.';
        'Prepared automatically from the concept. Edit only if you want to change the creative direction.'='Preparado automáticamente a partir del concepto. Edita solo si quieres cambiar la dirección creativa.';
        'Generation runs'='Ejecuciones de generación';
        'Variants'='Variantes';
        'Variant'='Variante';
        'Visual preview'='Vista previa visual';
        'Artwork is fitted to the frame so the full design remains visible.'='La ilustración se ajusta al marco para que el diseño completo permanezca visible.';
        'Primary selection'='Selección principal';
        'Select a variant'='Selecciona una variante';
        'Comparison selection'='Selección para comparar';
        'Select a second variant to compare'='Selecciona una segunda variante para comparar';
        'Compare'='Comparar';
        'Review note (does not Accept)'='Nota de revisión (no implica Accept)';
        'Acceptance'='Aceptación';
        'Large image files stay local to this computer. Preview access is handled safely without showing file-system locations.'='Los archivos de imagen grandes permanecen en este equipo. La vista previa se gestiona de forma segura sin mostrar rutas del sistema de archivos.';
        'Revisions'='Versiones';
        'Activity'='Actividad';
        'Current'='Actual';
        'Selected revision'='Versión seleccionada';
        'Selected activity evidence'='Evidencia de la actividad seleccionada';
        'Why this concept exists'='Por qué existe este concepto';
        'Insider / profession context'='Contexto profesional';
        'Meaning / joke'='Significado / broma';
        'Evidence & IP readiness'='Evidencia y preparación de PI';
        'Score dimensions'='Dimensiones de puntuación';
        'Warnings / blockers'='Advertencias / bloqueos';
        'Exact accepted lineage'='Linaje exacto aceptado';
        'Version-specific gates'='Controles específicos de la versión';
        'Readiness'='Preparación';
        'External action boundary'='Límite de acciones externas';
        'Design'='Diseño';
        'Listing draft'='Borrador del listing';
        'Forge prepares this from the concept automatically. Manual edits are optional.'='Forge prepara esto automáticamente a partir del concepto. Las ediciones manuales son opcionales.';
        'Listing title'='Título del listing';
        'Brand'='Marca';
        'Bullet 1'='Punto 1';
        'Bullet 2'='Punto 2';
        'Description'='Descripción';
        'Keywords'='Palabras clave';
        'Why changed? (optional)'='¿Por qué cambió? (opcional)';
        'Listing versions'='Versiones del listing';
        'No listing versions yet.'='Aún no hay versiones del listing.';
        'Checks'='Comprobaciones';
        'Economics'='Economía';
        'Preflight'='Preflight';
        'Packages'='Paquetes';
        'Preparation only. Export does not mean saved locally; Social handoff does not mean approval; package preparation does not submit or publish.'='Solo preparación. Exportar no significa guardar localmente; enviar a Social no significa aprobar; preparar un paquete no envía ni publica nada.';
        'Submit'='Enviar';
        'Locked external action'='Acción externa bloqueada';
        'Title'='Título';
        'Hook / slogan'='Gancho / eslogan';
        'Concept'='Concepto';
        'Target buyer'='Comprador objetivo';
        'Purchase reason'='Motivo de compra';
        'Differentiation'='Diferenciación';
        'Edit reason (optional)'='Motivo de edición (opcional)';
        'Disconnected'='Desconectado';
        'About Merch Forge'='Acerca de Merch Forge';
        'EN'='EN';
        'RU'='RU';
        'ES'='ES';
        'Remember on this Windows account'='Recordar en esta cuenta de Windows';
        'Open Workbench'='Abrir Workbench';
        'About'='Acerca de';
        'Diagnostics'='Diagnóstico';
        'Refresh'='Actualizar';
        'Sign out'='Cerrar sesión';
        'All statuses'='Todos los estados';
        'Ready to generate'='Listo para generar';
        'Editing'='Editando';
        'Generation requested'='Generación solicitada';
        'Has variants'='Tiene variantes';
        'Accepted'='Aceptado';
        'Blocked'='Bloqueado';
        'In progress'='En curso';
        'No current analysis warning.'='No hay advertencias de análisis actuales.';
        'The visual is accepted. Review Delivery and Publication readiness when you are ready.'='La imagen está aceptada. Cuando estés listo, revisa la preparación de Entrega y Publicación.';
        'Generated visuals are available. Review them in Visuals & Generate before any Accept decision.'='Hay imágenes generadas disponibles. Revísalas en Imágenes y generación antes de cualquier decisión de Accept.';
        'Generation has been requested. Review the result when it arrives; do not submit anything externally.'='La generación fue solicitada. Revisa el resultado cuando llegue; no envíes nada a sistemas externos.';
        'An edited brief is current. Review it, then generate only when you choose.'='El brief editado es el actual. Revísalo y genera solo cuando tú lo decidas.';
        'This concept is blocked. Review the evidence and blocker before generating.'='Este concepto está bloqueado. Revisa la evidencia y el bloqueo antes de generar.';
        'The brief is ready. Review the idea first; Generate remains a separate explicit action.'='El brief está listo. Revisa primero la idea; Generate sigue siendo una acción explícita y separada.';
        'Score: high to low'='Puntuación: de mayor a menor';
        'Title: A to Z'='Título: A a Z';
        'Workflow status'='Estado del flujo';
        'Save new revision'='Guardar nueva versión';
        'Review visuals / generation'='Revisar imágenes / generación';
        'Edit concept'='Editar concepto';
        'Generate variants…'='Generar variantes…';
        'Accept selected visual'='Aceptar imagen seleccionada';
        'Cancel selected queued request'='Cancelar solicitud en cola seleccionada';
        'Compare two selected variants'='Comparar dos variantes seleccionadas';
        'neutral'='neutral';
        'favorite'='favorito';
        'reject'='rechazar';
        'Save review event'='Guardar decisión de revisión';
        'Reopen current acceptance'='Reabrir aceptación actual';
        'Start new iteration · same brief'='Nueva iteración · mismo brief';
        'Start new iteration · edited brief'='Nueva iteración · brief editado';
        'Restore selected as new revision'='Restaurar selección como nueva versión';
        'Save listing version'='Guardar versión del listing';
        'Export package'='Preparar paquete de exportación';
        'Send to Social'='Enviar a Social';
        'Owner export'='Exportación del propietario';
        'Social source'='Fuente para Social';
        'Amazon owner'='Amazon propietario';
        'Prepare package'='Preparar paquete';
        'Close'='Cerrar';
        'Copy diagnostics'='Copiar diagnóstico';
        'Open log'='Abrir log';
        'Done'='Hecho';
        'Overview'='Resumen';
        'Visuals & Generate'='Imágenes y generación';
        'Technical details'='Detalles técnicos';
        'History'='Historial';
        'Evidence'='Evidencia';
        'Delivery'='Entrega';
        'Publication'='Publicación';
        'Edit'='Editar';
        'Technical details · production spec JSON'='Detalles técnicos · production spec JSON';
        'UI language'='Idioma de la interfaz';
        'Connect to your Merch Forge workspace and open the workbench'='Conecta con tu espacio de trabajo de Merch Forge y abre Workbench';
        'Select concept'='Seleccionar concepto';
        'UI language. RU/ES use real built-in translations; original creative copy is not translated automatically.'='Idioma de la interfaz. Ruso y español usan traducciones reales integradas; el texto creativo original no se traduce automáticamente.';
        'About Merch Forge, this build, and what the workbench does'='Acerca de Merch Forge, esta compilación y lo que hace Workbench';
        'Open safe in-app connection and runtime diagnostics'='Abrir diagnóstico seguro de conexión y ejecución dentro de la aplicación';
        'Reload concepts and current workspace state'='Recargar conceptos y el estado actual del espacio de trabajo';
        'Sign out and remove saved access from this Windows account'='Cerrar sesión y eliminar el acceso guardado de esta cuenta de Windows';
        'Search title, slogan or profession'='Buscar por título, eslogan o profesión';
        'Show concepts by workflow status'='Mostrar conceptos por estado del flujo';
        'Sort the concept queue'='Ordenar la cola de conceptos';
        'Save your edits as a new immutable creative revision'='Guardar tus cambios como una nueva versión creativa inmutable';
        'Open visual generation and review for this concept'='Abrir generación visual y revisión para este concepto';
        'Open the optional creative editor for this concept'='Abrir el editor creativo opcional para este concepto';
        'Create a generation request for the exact current revision. This is an explicit owner action.'='Crear una solicitud de generación para la versión actual exacta. Es una acción explícita del propietario.';
        'Accept the exact selected visual after review. This does not publish it.'='Aceptar la imagen exacta seleccionada después de revisarla. Esto no la publica.';
        'Cancel a queued generation request before provider dispatch'='Cancelar una solicitud de generación en cola antes de enviarla al proveedor';
        'Compare two selected visual variants side by side'='Comparar dos variantes visuales seleccionadas lado a lado';
        'Reject requires a structured reason. Favorite/neutral reason is optional.'='Rechazar requiere un motivo estructurado. El motivo para favorito/neutral es opcional.';
        'Optional review note'='Nota de revisión opcional';
        'Save this review decision as a new immutable review event'='Guardar esta decisión como un nuevo evento de revisión inmutable';
        'Required reason when reopening an accepted revision'='Motivo obligatorio al reabrir una versión aceptada';
        'Revoke the current acceptance and return this concept to review'='Revocar la aceptación actual y devolver este concepto a revisión';
        'Create a new revision using the same brief; generation remains separate'='Crear una nueva versión con el mismo brief; la generación sigue siendo una acción separada';
        'Create a new editable revision; generation remains separate'='Crear una nueva versión editable; la generación sigue siendo una acción separada';
        'Copy the selected historical revision into a new current revision; history is preserved'='Copiar la versión histórica seleccionada a una nueva versión actual; se conserva el historial';
        'Human-readable actor/action/version timeline; technical events hidden by default'='Cronología legible de actor/acción/versión; los eventos técnicos están ocultos por defecto';
        'Separate keywords with commas or semicolons'='Separa las palabras clave con comas o punto y coma';
        'Save listing metadata as a new immutable version; this does not publish'='Guardar los metadatos del listing como una nueva versión inmutable; esto no publica';
        'Prepare exact delivery manifest. Local ZIP is a separate verified step.'='Preparar el manifiesto exacto de entrega. El ZIP local es un paso verificado independiente.';
        'Prepare minimized outbound Social source envelope. This does not approve or publish anything.'='Preparar un paquete fuente minimizado para Social. Esto no aprueba ni publica nada.';
        'Prepare an owner package only. This does not submit or publish anything.'='Preparar solo un paquete para el propietario. Esto no envía ni publica nada.';
        'Close this panel'='Cerrar este panel';
        'Copy the current diagnostics text to the clipboard'='Copiar el texto de diagnóstico actual al portapapeles';
        'Open the local runtime log in Notepad'='Abrir el log local de ejecución en el Bloc de notas';
        'Listing locale'='Configuración regional del listing';
        'English (United States)'='Inglés (Estados Unidos)';
        'Russian (Russia)'='Ruso (Rusia)';
        'Spanish (Spain)'='Español (España)';
        'Local-first fallback'='Modo de trabajo local';
        'Local check evidence'='Comprobaciones locales';
        'Local sales import'='Importación local de ventas';
        'Local core ready.'='El flujo local está listo.';
        'No local check evidence imported.'='Aún no se han importado comprobaciones locales.';
        'No local sales data imported.'='Aún no se han importado datos locales de ventas.';
        'Sales · 7 days'='Ventas · 7 días';
        'Sales · 30 days'='Ventas · 30 días';
        'Royalties · 30 days'='Regalías · 30 días';
        'Sales · 90 days'='Ventas · 90 días';
        'Sales, royalties and product momentum across 7 / 30 / 90 days.'='Ventas, regalías y evolución de productos en 7 / 30 / 90 días.';
        'Winners'='Mejores resultados';
        'Needs attention'='Requiere atención';
        'No synthetic performance data is shown.'='No se muestran métricas sintéticas.';
        'Connect live commerce data to load sales and royalty performance.'='Conecta datos reales de ventas para cargar ventas y regalías.';
        'Create a local ZIP for manual upload. Merch Forge does not submit it.'='Crear un ZIP local para carga manual. Merch Forge no lo envía.';
        'Imported publication receipts'='Comprobantes de publicación importados';
        'Requires live or imported evidence'='Requiere datos reales o importados';
        'Local publication receipts'='Comprobantes locales de publicación';
        'No local publication receipt imported.'='Aún no se ha importado ningún comprobante de publicación.';
    }
}
$script:StaticLocaleRegistry = New-Object System.Collections.ArrayList

$script:OwnerExplanationTranslations = @{
    '3b5796a5-a76c-431c-8d07-a3f34cbc5724' = @{
        ru = @{
            profession_context='Техники подстанционной автоматики и релейной защиты испытывают и обслуживают системы защиты, которые обнаруживают электрические повреждения и могут давать команду выключателям на отключение. Работа имеет высокую цену ошибки: небольшая ошибка в настройке или переключении может повлиять на крупное оборудование и работу энергосистемы.';
            line_meaning='Фраза говорит о том, что один маленький щелчок может вызвать последствия, достаточно серьёзные для разбора инцидента или большой комнаты людей, которые хотят понять, что произошло.';
            joke_explanation='Юмор строится на абсурдной разнице между масштабом действия и масштабом организационных последствий. Техники РЗА сразу понимают, почему кажущееся маленьким действие может очень быстро привлечь внимание всех вокруг.';
        };
        es = @{
            profession_context='Los técnicos de subestaciones y relés prueban y mantienen sistemas de protección que detectan fallas eléctricas y pueden ordenar la apertura de interruptores. Es un trabajo de altas consecuencias: un pequeño error de configuración o maniobra puede afectar equipos importantes y la operación.';
            line_meaning='La frase dice que un clic diminuto puede crear consecuencias lo bastante grandes como para provocar una revisión seria del incidente o una sala llena de gente preguntando qué ocurrió.';
            joke_explanation='El humor está en la diferencia absurda entre el tamaño de la acción y el tamaño de las consecuencias organizativas. Los técnicos de relés entienden de inmediato por qué una acción aparentemente pequeña puede hacer que todos se interesen muy rápido.';
        };
    };
    '1b58bfa8-5fcc-4e3f-a178-af87e67c7275' = @{
        ru = @{
            profession_context='Техники полупроводникового производства работают в чистых помещениях, где необходимо контролировать загрязнение частицами. Вход часто требует капюшона, чистого костюма, перчаток и других этапов переодевания; при выходе процесс идёт в обратном порядке.';
            line_meaning='Кофе рано или поздно означает поход в туалет. В чистом помещении это может означать выход из контролируемой зоны, снятие чистой одежды и повторение всей процедуры при возвращении.';
            joke_explanation='Шутка в том, что совершенно обычный выбор — выпить кофе — запускает раздражающе длинную цепочку действий. Работники fab сразу узнают ежедневный расчёт: стоит ли кофе того, чтобы потом снова проходить всё это?';
        };
        es = @{
            profession_context='Los técnicos de fabricación de semiconductores trabajan en salas limpias donde debe controlarse la contaminación por partículas. Entrar suele exigir capucha, traje de sala limpia, guantes y otros pasos de vestimenta; al salir se hace el proceso inverso.';
            line_meaning='El café tarde o temprano implica ir al baño. En una sala limpia eso puede significar salir del área controlada, quitarse la ropa de sala limpia y repetir todo el proceso al volver.';
            joke_explanation='La broma es que una decisión totalmente normal —tomar café— crea una cadena de trabajo exageradamente molesta. Quien trabaja en una fab reconoce enseguida el cálculo diario: ¿vale el café tener que hacer todo eso otra vez?';
        };
    };
    '24a48dfc-bca1-452e-96f6-af3b85f802bc' = @{
        ru = @{
            profession_context='Техники КИПиА работают с датчиками, преобразователями, контурами регулирования и промышленными сигналами. Один из распространённых стандартов аналогового сигнала — 4–20 мА.';
            line_meaning='Посторонний слышит «instrument technician» и думает о музыкальном инструменте. Техник отвечает «4–20 мА», словно промышленный токовый сигнал — это инструмент, на котором он играет.';
            joke_explanation='Это игра на двойном значении слова instrument: для обычного человека оно означает одно, а в управлении технологическими процессами — другое. Люди из КИПиА мгновенно узнают 4–20 мА, поэтому концовка одновременно служит знаком «свой человек».';
        };
        es = @{
            profession_context='Los técnicos de instrumentación y control trabajan con sensores, transmisores, lazos de control y señales de procesos industriales. Un estándar analógico muy común es 4–20 mA.';
            line_meaning='Una persona ajena oye “técnico de instrumentos” y piensa en un instrumento musical. El técnico responde “4–20 mA”, tratando una señal industrial de corriente como si fuera el instrumento que toca.';
            joke_explanation='Es una broma de doble significado: “instrumento” significa una cosa para el público y otra en control de procesos. La gente de I&C reconoce 4–20 mA al instante, así que el remate también funciona como señal de pertenencia.';
        };
    };
    'bc45b397-7727-4285-a175-7dcf7f383a80' = @{
        ru = @{
            profession_context='Сотрудники стерилизационного отделения очищают, осматривают, упаковывают и стерилизуют многоразовые медицинские инструменты, чтобы они были безопасны для следующего пациента.';
            line_meaning='Если что-то в наборе остаётся загрязнённым или не проходит контроль, нельзя просто отправить весь набор дальше так, будто всё в порядке.';
            joke_explanation='Фраза превращает инструментальный набор в школьный класс: одного «грязного» поймали — и всех отправляют назад. Работники SPD узнают знакомое раздражение, когда одна проблема сбрасывает работу по целому набору.';
        };
        es = @{
            profession_context='El personal de procesamiento estéril limpia, inspecciona, empaqueta y esteriliza instrumentos médicos reutilizables para que sean seguros para el siguiente paciente.';
            line_meaning='Si algo del conjunto sigue contaminado o no supera la inspección, el conjunto no puede seguir adelante como si todo estuviera bien.';
            joke_explanation='La frase trata la bandeja de instrumentos como una clase escolar: atrapan a un miembro “sucio” y todos vuelven atrás. Quien trabaja en SPD reconoce la frustración de que un solo problema reinicie el trabajo de todo un conjunto.';
        };
    };
    '47485853-cba4-431f-848a-de5fc995b41d' = @{
        ru = @{
            profession_context='Работа в полупроводниковой чистой комнате определяется контролем загрязнений, потому что даже крошечные частицы могут повредить чувствительные процессы производства.';
            line_meaning='Техник шутит, что микроскопическая пылинка имеет больше власти, чем он сам, потому что правила чистоты диктуют, к чему можно прикасаться, что носить и что делать.';
            joke_explanation='Абсурд — в иерархии власти: почти невидимая частица «выше по должности» человека. Строгая дисциплина чистой комнаты превращается в образ крошечного начальника.';
        };
        es = @{
            profession_context='El trabajo en salas limpias de semiconductores está dominado por el control de contaminación, porque partículas diminutas pueden dañar procesos de fabricación muy sensibles.';
            line_meaning='El técnico bromea con que una mota microscópica de polvo tiene más autoridad que él, porque las reglas de contaminación determinan qué puede tocarse, qué debe llevarse y qué puede hacerse.';
            joke_explanation='Lo absurdo está en la jerarquía de poder: una partícula casi invisible “manda más” que una persona. La estricta disciplina de la sala limpia se convierte en un diminuto personaje de jefe.';
        };
    };
    'c8c1237e-3f8d-411a-ac8f-5fe2404dbe57' = @{
        ru = @{
            profession_context='Цитотехнологи исследуют подготовленные препараты клеток организма под микроскопом и ищут отклонения, которые могут указывать на заболевание, включая злокачественные изменения.';
            line_meaning='Фраза сравнивает внимательное микроскопическое исследование с допросом детектива: смотри достаточно долго — и одна подозрительная клетка наконец «признается».';
            joke_explanation='Терпеливая, детальная диагностическая работа превращается в нуарную сцену расследования. Профессиональная гордость в том, что именно цитотехнолог замечает одну аномальную клетку среди множества нормальных.';
        };
        es = @{
            profession_context='Los citotecnólogos examinan al microscopio preparaciones de células del cuerpo y buscan anomalías que puedan indicar enfermedad, incluidos cambios cancerosos.';
            line_meaning='La frase compara el examen microscópico cuidadoso con un interrogatorio detectivesco: mira el tiempo suficiente y una célula sospechosa finalmente “confiesa”.';
            joke_explanation='Convierte un trabajo diagnóstico paciente y detallista en una escena de detective noir. El orgullo profesional está en ser quien detecta una célula anormal escondida entre muchas normales.';
        };
    };
    '6c484c8d-7746-4e6d-8485-02c9bcb472ac' = @{
        ru = @{
            profession_context='Техники по медицинскому оборудованию устанавливают, обслуживают, калибруют и ремонтируют медицинскую технику по всему госпиталю и другим клиническим объектам.';
            line_meaning='Техник может потратить гораздо больше времени на дорогу через большой госпиталь к заявке, чем на сам ремонт после прибытия.';
            joke_explanation='Свойская узнаваемость — в соотношении времени: долгая прогулка по зданию ради крошечного ремонта. Смешно потому, что логистика иногда занимает больше времени, чем техническая проблема.';
        };
        es = @{
            profession_context='Los técnicos de equipos biomédicos instalan, mantienen, calibran y reparan equipos médicos en hospitales y otras instalaciones clínicas.';
            line_meaning='El técnico puede tardar mucho más caminando por un hospital grande hasta la llamada de servicio que realizando la reparación cuando llega.';
            joke_explanation='El reconocimiento interno está en la proporción: un viaje largo por el edificio para una reparación diminuta. Es gracioso porque la logística puede consumir más tiempo que el problema técnico.';
        };
    };
    'a675c85e-fd62-4fe0-855d-c84c59b70b7e' = @{
        ru = @{
            profession_context='Техники релейной защиты испытывают электрические схемы защиты, предназначенные для выдачи команд на отключение при повреждениях. Испытания проводят осторожно, потому что эти системы взаимодействуют с выключателями и критически важным силовым оборудованием.';
            line_meaning='Проверка на отключение для техника — обычная профессиональная работа, но все рядом понимают, что «trip» связано с отключением выключателей и выводом оборудования из работы.';
            joke_explanation='Техник спокоен, потому что для него это рутина; наблюдатели напряжены, потому что понимают последствия, если что-то произойдёт неожиданно. Юмор в том, чтобы профессионально отвечать за то, что вся комната нервничает.';
        };
        es = @{
            profession_context='Los técnicos de protección y relés prueban esquemas eléctricos diseñados para emitir órdenes de disparo cuando ocurre una falla. Las pruebas se realizan con cuidado porque estos sistemas interactúan con interruptores y equipos eléctricos críticos.';
            line_meaning='Una prueba de disparo es trabajo rutinario para el técnico, pero todos alrededor saben que “trip” está relacionado con abrir interruptores y sacar equipos de servicio.';
            joke_explanation='El técnico está tranquilo porque es trabajo normal; los observadores están tensos porque entienden las consecuencias si algo ocurre de forma inesperada. El humor está en ser profesionalmente responsable de poner nerviosa a toda la sala.';
        };
    };
    'a9396362-1fde-4d87-ad58-49ab4421f91e' = @{
        ru = @{
            profession_context='Техники по электротехнике и электронике диагностируют цепи, платы и системы: измеряют сигналы, отслеживают неисправности и проверяют возможные причины.';
            line_meaning='Схема не умеет разговаривать. «Спорить» с ней — значит снова и снова проверять гипотезы, пока измерения наконец не покажут настоящую неисправность.';
            joke_explanation='Любой, кто диагностировал упрямую электронику, знает ощущение переговоров с машиной, которая отказывается сказать, что с ней не так. Фраза превращает настойчивую диагностику в человеческий спор.';
        };
        es = @{
            profession_context='Los técnicos eléctricos y electrónicos diagnostican circuitos, placas y sistemas midiendo señales, siguiendo fallas y probando posibles causas.';
            line_meaning='El circuito no puede hablar. “Discutir” significa probar hipótesis una y otra vez hasta que las mediciones revelan por fin la falla real.';
            joke_explanation='Quien haya diagnosticado electrónica obstinada conoce la sensación de negociar con una máquina que se niega a decir qué está mal. La frase convierte la persistencia del diagnóstico en una discusión humana.';
        };
    };
    '30563cf9-0722-4622-b845-f43fbdc4872b' = @{
        ru = @{
            profession_context='Техники по авионике осматривают и диагностируют электрические, электронные и компьютерные системы самолёта, часто прослеживая сложные неисправности через взаимосвязанное оборудование и проводку.';
            line_meaning='Техник исследует одну проблему и обнаруживает более глубокую неисправность, которая существовала раньше. Со стороны может показаться, что новую проблему вызвал техник просто потому, что её обнаружили во время его работы.';
            joke_explanation='Это защитный техничный юмор: «Я это не сломал; я показал то, что уже было сломано». Он про человека, который постоянно находит скрытые неисправности, а потом вынужден объяснять, почему проблема теперь стала видимой.';
        };
        es = @{
            profession_context='Los técnicos de aviónica inspeccionan y diagnostican sistemas eléctricos, electrónicos e informáticos de aeronaves, siguiendo a menudo fallas complejas a través de equipos y cableado interconectados.';
            line_meaning='El técnico investiga un trabajo y descubre un problema previo más profundo. Desde fuera puede parecer que el técnico causó el nuevo problema simplemente porque se descubrió mientras trabajaba.';
            joke_explanation='Es humor defensivo de técnico: “Yo no lo rompí; dejé al descubierto lo que ya estaba roto”. Celebra a quien sigue encontrando fallas ocultas y luego tiene que explicar por qué el problema ahora es visible.';
        };
    };
}

function Ensure-Dir([string]$Path) { if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null } }
# R2O module function: Get-UiText
# R2O module function: Get-StaticUiText
# R2O module function: Add-StaticLocaleBinding
# R2O module function: Register-StaticLocaleTree
# R2O module function: Apply-StaticLocaleUi
# R2O module function: Get-PublicationLocaleDefault
# R2O module function: Get-PublicationLocale
# R2O module function: Set-PublicationLocaleSelection
# R2O module function: Get-LocalizedOwnerExplanation
# R2O module function: Load-UiLocale
# R2O module function: Save-UiLocale
function Write-AppLog([string]$Level,[string]$Message) { try { Ensure-Dir $script:LogRoot; "[$([DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))] [$Level] $Message" | Add-Content -LiteralPath $script:RuntimeLogPath -Encoding UTF8 } catch {} }
function Set-LastDiagnostic([string]$Category,[int]$HttpStatus,[string]$Action,[string]$Technical,[string]$UserMessage) {
    $script:LastDiagnostic=[ordered]@{ when=[DateTimeOffset]::Now.ToString('o'); category=$Category; http_status=$HttpStatus; action=$Action; technical=$Technical; user_message=$UserMessage }
$script:GenerationIdempotencyKey=$null; $script:GenerationIdempotencyConceptKey=$null; $script:GenerationIdempotencyRevisionId=$null
}
function Get-HumanErrorMessage([string]$Message) {
    $m=([string]$Message).Trim(); $l=$m.ToLowerInvariant()
    if($l -match 'http 401|invalid or expired|unauthorized'){return 'Your saved access is no longer valid. Sign in again.'}
    if($l -match 'http 403|forbidden|permission denied'){return 'You do not have permission to do that in this workspace.'}
    if($l -match 'http 404|not found'){return 'This item is no longer available. Refresh the workspace.'}
    if($l -match 'http 409|changed in another client|accepted creative lineage changed|stale version|refresh before saving'){return 'This changed somewhere else. Refresh before saving again.'}
    if($l -match 'http 429|too many requests|rate limit'){return 'Merch Forge is busy right now. Try again shortly.'}
    if($l -match 'client_too_old|backend .*too old|needs an update'){return 'This Workbench needs an update before it can connect.'}
    if($l -match 'session_context|session context|workspace session'){return 'Merch Forge could not verify this workspace session. Sign in again.'}
    if($l -match 'empty_response|empty response|incomplete response'){return 'Merch Forge returned an incomplete response. Try again.'}
    if($l -match 'provider_unavailable|provider.*unavailable|generation.*not available|subsystem not ready'){return 'Image generation is not available right now. Your design was not sent.'}
    if($l -match 'timed out|timeout|name resolution|unable to connect|connection.*failed|network|offline|no such host'){return 'Merch Forge could not be reached. Check your connection and try again.'}
    if($l -match 'http 5[0-9][0-9]|database|internal server|server error'){return 'Merch Forge hit an internal problem. Nothing was assumed saved. Try again.'}
    if($l -match 'http 400'){return 'This request needs a correction. Review the fields and try again.'}
    if([string]::IsNullOrWhiteSpace($m)){return 'Merch Forge could not complete that action. Try again.'}
    return 'Merch Forge could not complete that action. Try again.'
}
function Show-FatalError([string]$Message) {
    $human='Merch Forge could not start. Technical details were saved for diagnostics.'
    Write-AppLog 'FATAL' $Message; Set-LastDiagnostic 'fatal' 0 'restart' $Message $human
    [System.Windows.MessageBox]::Show($human,'Merch Forge — Error',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Error) | Out-Null
}
function Save-EncryptedOwnerKey([string]$Key) { Ensure-Dir $script:StateRoot; $bytes=[Text.Encoding]::UTF8.GetBytes($Key); $protected=[Security.Cryptography.ProtectedData]::Protect($bytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser); [Convert]::ToBase64String($protected) | Set-Content -LiteralPath $script:KeyPath -Encoding ASCII -Force }
function Load-EncryptedOwnerKey { if (-not (Test-Path -LiteralPath $script:KeyPath)) { return $null }; try { $encoded=(Get-Content -LiteralPath $script:KeyPath -Raw).Trim(); if ([string]::IsNullOrWhiteSpace($encoded)) { return $null }; $protected=[Convert]::FromBase64String($encoded); $bytes=[Security.Cryptography.ProtectedData]::Unprotect($protected,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser); return [Text.Encoding]::UTF8.GetString($bytes) } catch { return $null } }
function Remove-EncryptedOwnerKey { if (Test-Path -LiteralPath $script:KeyPath) { Remove-Item -LiteralPath $script:KeyPath -Force -ErrorAction SilentlyContinue } }
function Get-HttpStatusCode($Exception) { try { if ($Exception.Response -and $Exception.Response.StatusCode) { return [int]$Exception.Response.StatusCode } } catch {}; return 0 }
# R2O module: Forge.DataAdapter.ps1
function Confirm([string]$Message,[string]$Title='Merch Forge') { try{$Message=Translate-UiMessage $Message;$Title=Translate-UiMessage $Title}catch{}; return ([System.Windows.MessageBox]::Show($Window,$Message,$Title,[System.Windows.MessageBoxButton]::YesNo,[System.Windows.MessageBoxImage]::Question) -eq [System.Windows.MessageBoxResult]::Yes) }
function Get-OwnerActionIdempotencyKey([string]$PayloadKey) {
    if(-not $script:PendingOwnerActionKeys.ContainsKey($PayloadKey)){ $script:PendingOwnerActionKeys[$PayloadKey]=([guid]::NewGuid().ToString('N')) }
    return [string]$script:PendingOwnerActionKeys[$PayloadKey]
}
function Clear-OwnerActionIdempotencyKey([string]$PayloadKey) { if($script:PendingOwnerActionKeys.ContainsKey($PayloadKey)){ $script:PendingOwnerActionKeys.Remove($PayloadKey) } }
function Get-PropertyValue($Object,[string]$Name) {
    if($null -eq $Object){return $null}
    $p=$Object.PSObject.Properties[$Name]; if($null -eq $p){return $null}; return $p.Value
}
function Get-NestedPropertyValue($Object,[string[]]$Path) {
    $value=$Object
    foreach($name in $Path){ if($null -eq $value){return $null}; $value=Get-PropertyValue $value $name }
    return $value
}
function Get-ProductionSpecDirtyValues($Base,$Edited) {
    $dirty=@{}
    $top=@('ink_palette','shirt_targets','composition','type_style','hierarchy','illustration','avoid','variants','generation_notes')
    foreach($k in $top){
        $a=Get-PropertyValue $Base $k; $b=Get-PropertyValue $Edited $k
        $ja=if($null -eq $a){'null'}else{$a|ConvertTo-Json -Depth 20 -Compress}
        $jb=if($null -eq $b){'null'}else{$b|ConvertTo-Json -Depth 20 -Compress}
        if($ja -ne $jb){$dirty[$k]=$b}
    }
    $bp=Get-PropertyValue $Base 'print_constraints'; $ep=Get-PropertyValue $Edited 'print_constraints'
    foreach($k in @('max_inks','min_stroke_pt','safe_margin_in','min_text_height_in','halftone_lpi_target')){
        $a=Get-PropertyValue $bp $k; $b=Get-PropertyValue $ep $k
        $ja=if($null -eq $a){'null'}else{$a|ConvertTo-Json -Depth 4 -Compress}
        $jb=if($null -eq $b){'null'}else{$b|ConvertTo-Json -Depth 4 -Compress}
        if($ja -ne $jb){$dirty[('print_constraints.'+$k)]=$b}
    }
    return $dirty
}
function Show-Error([string]$Message) {
    if((Test-BackendUnavailableMessage $Message) -and $null -ne $AppGrid -and $AppGrid.Visibility -eq 'Visible'){Enter-OfflineWorkbench $Message;return}
    $known=$false; try{$known=Test-KnownUiMessage $Message}catch{}; $human=if($known){$Message}else{Get-HumanErrorMessage $Message}; $code=0; if($Message -match 'HTTP ([0-9]{3})'){try{$code=[int]$Matches[1]}catch{$code=0}}
    Write-AppLog 'ERROR' $Message; Set-LastDiagnostic 'error' $code 'review_and_retry' $Message $human
    $dialogText=("{0}`n`nTechnical details are available in Diagnostics." -f $human); try{$dialogText=Translate-UiMessage $dialogText}catch{}
    [System.Windows.MessageBox]::Show($Window,$dialogText,'Merch Forge — Error',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Error)|Out-Null
}
function Get-RoleLabel([string]$Role) {
    switch(([string]$Role).ToLowerInvariant()){'owner'{return 'Owner'}'editor'{return 'Editor'}'reviewer'{return 'Reviewer'}'viewer'{return 'Viewer'}default{return 'Workspace member'}}
}
# R2O module function: Get-AboutText
# R2O module function: Get-DiagnosticSummary
# R2O module function: Get-DiagnosticHumanSummary
# R2O module function: Hide-UtilityPanel
# R2O module function: Show-UtilityPanel
# R2O module function: Show-About
# R2O module function: Show-Diagnostics
# R2O module function: Open-DiagnosticLogSafe
function New-IdempotencyKey { return ('forge-ui-' + [Guid]::NewGuid().ToString('N')) }
function Get-GenerationIdempotencyKey([string]$ConceptKey,[string]$RevisionId) {
    if([string]::IsNullOrWhiteSpace([string]$script:GenerationIdempotencyKey) -or [string]$script:GenerationIdempotencyConceptKey -ne $ConceptKey -or [string]$script:GenerationIdempotencyRevisionId -ne $RevisionId){
        $script:GenerationIdempotencyKey=New-IdempotencyKey; $script:GenerationIdempotencyConceptKey=$ConceptKey; $script:GenerationIdempotencyRevisionId=$RevisionId
    }
    return [string]$script:GenerationIdempotencyKey
}
function Clear-GenerationIdempotencyKey { $script:GenerationIdempotencyKey=$null; $script:GenerationIdempotencyConceptKey=$null; $script:GenerationIdempotencyRevisionId=$null }

[xml]$xaml=@'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  Title="Merch Forge · Product Workspace" Width="1540" Height="940" MinWidth="320" MinHeight="480" WindowState="Maximized"
  WindowStartupLocation="CenterScreen" Background="#0B1118" FontFamily="Segoe UI" FontSize="15.5" UseLayoutRounding="True" SnapsToDevicePixels="True">
  <Window.Resources>
    <SolidColorBrush x:Key="Bg" Color="#0B1118"/><SolidColorBrush x:Key="Panel" Color="#111922"/>
    <SolidColorBrush x:Key="Panel2" Color="#18222D"/><SolidColorBrush x:Key="PanelElevated" Color="#151E28"/><SolidColorBrush x:Key="Line" Color="#25313D"/><SolidColorBrush x:Key="LineStrong" Color="#45586A"/>
    <SolidColorBrush x:Key="Text" Color="#F3F4F6"/><SolidColorBrush x:Key="Secondary" Color="#B8BEC7"/>
    <SolidColorBrush x:Key="Muted" Color="#8D99A8"/><SolidColorBrush x:Key="Accent" Color="#F18A45"/><SolidColorBrush x:Key="AccentHover" Color="#FFA365"/><SolidColorBrush x:Key="AccentPressed" Color="#D96F32"/><SolidColorBrush x:Key="AccentSoft" Color="#352015"/><SolidColorBrush x:Key="AccentStroke" Color="#C96832"/><SolidColorBrush x:Key="Success" Color="#6FD29A"/><SolidColorBrush x:Key="SuccessSoft" Color="#173128"/><SolidColorBrush x:Key="Warning" Color="#F0BF5A"/><SolidColorBrush x:Key="WarningSoft" Color="#352A15"/><SolidColorBrush x:Key="Danger" Color="#F07878"/><SolidColorBrush x:Key="DangerSoft" Color="#381D22"/><SolidColorBrush x:Key="Info" Color="#78B7EA"/><SolidColorBrush x:Key="InfoSoft" Color="#172A3B"/>
    <SolidColorBrush x:Key="CardSurface" Color="#141E28"/><SolidColorBrush x:Key="CardHover" Color="#1A2733"/><SolidColorBrush x:Key="CardSelected" Color="#202E3A"/><SolidColorBrush x:Key="CardStroke" Color="#2B3946"/>
    <SolidColorBrush x:Key="MediaSurface" Color="#0D131A"/><SolidColorBrush x:Key="MediaSurfaceInner" Color="#111922"/><SolidColorBrush x:Key="MediaStroke" Color="#344454"/><SolidColorBrush x:Key="MediaStatus" Color="#9BA6B3"/>
    <SolidColorBrush x:Key="ChromeSurface" Color="#0E151D"/><SolidColorBrush x:Key="ChromeSurface2" Color="#121B24"/><SolidColorBrush x:Key="ChromeStroke" Color="#22303B"/>
    <SolidColorBrush x:Key="TabIdle" Color="#101821"/><SolidColorBrush x:Key="TabHover" Color="#18242E"/><SolidColorBrush x:Key="TabSelected" Color="#1D2A35"/>
    <DropShadowEffect x:Key="SurfaceShadow" BlurRadius="20" ShadowDepth="3" Direction="270" Opacity="0.28" Color="#000000"/>
    <DropShadowEffect x:Key="MediaShadow" BlurRadius="15" ShadowDepth="2" Direction="270" Opacity="0.22" Color="#000000"/>
    <DropShadowEffect x:Key="ChromeShadow" BlurRadius="14" ShadowDepth="2" Direction="270" Opacity="0.18" Color="#000000"/>
    <DropShadowEffect x:Key="AccentGlow" BlurRadius="14" ShadowDepth="0" Direction="270" Opacity="0.16" Color="#F28C52"/>
    <Style x:Key="KeyboardFocusStyle"><Setter Property="Control.Template"><Setter.Value><ControlTemplate><Border BorderBrush="{StaticResource Accent}" BorderThickness="2" CornerRadius="3" Margin="-2"/></ControlTemplate></Setter.Value></Setter></Style>
    <Style TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/></Style>
    <Style x:Key="DisplayTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="32"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="38"/></Style>
    <Style x:Key="AppTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="24"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="30"/></Style>
    <Style x:Key="ConceptTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="26"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="32"/></Style>
    <Style x:Key="SectionTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="18"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="24"/><Setter Property="Margin" Value="0,0,0,4"/></Style>
    <Style x:Key="SubsectionTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="13"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="TextOptions.TextFormattingMode" Value="Display"/></Style>
    <Style x:Key="FieldLabelText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="FontSize" Value="12.5"/><Setter Property="FontWeight" Value="SemiBold"/></Style>
    <Style x:Key="SubtitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="15"/><Setter Property="LineHeight" Value="21"/></Style>
    <Style x:Key="BodyText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="15"/><Setter Property="LineHeight" Value="22"/></Style>
    <Style x:Key="HeroHookText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="23"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="29"/></Style>
    <Style x:Key="MetricValueText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Accent}"/><Setter Property="FontSize" Value="18"/><Setter Property="FontWeight" Value="SemiBold"/></Style>
    <Style x:Key="MetricLabelText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="FontSize" Value="11.5"/><Setter Property="FontWeight" Value="SemiBold"/></Style>
    <Style x:Key="MetaText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="13"/><Setter Property="LineHeight" Value="19"/></Style>
    <Style x:Key="MutedCaptionText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="FontSize" Value="12"/><Setter Property="LineHeight" Value="17"/></Style>
    <Style x:Key="QueueTitleText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FontSize" Value="15"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="LineHeight" Value="20"/></Style>
    <Style x:Key="QueueBodyText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="13.5"/><Setter Property="LineHeight" Value="19"/></Style>
    <Style x:Key="QueueMetaText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="FontSize" Value="12"/></Style>

    <Style TargetType="ListBox"><Setter Property="FontSize" Value="14.5"/><Setter Property="Background" Value="Transparent"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="BorderBrush" Value="{StaticResource Line}"/><Setter Property="BorderThickness" Value="0"/><Setter Property="ScrollViewer.HorizontalScrollBarVisibility" Value="Disabled"/><Setter Property="ScrollViewer.VerticalScrollBarVisibility" Value="Auto"/><Setter Property="HorizontalContentAlignment" Value="Stretch"/></Style>
    <Style TargetType="TextBox"><Setter Property="Padding" Value="11,9"/><Setter Property="FontSize" Value="14.5"/><Setter Property="MinHeight" Value="40"/><Setter Property="BorderBrush" Value="{StaticResource Line}"/><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="CaretBrush" Value="{StaticResource Text}"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type TextBox}"><Border x:Name="TextBoxChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" CornerRadius="7" Padding="{TemplateBinding Padding}"><ScrollViewer x:Name="PART_ContentHost"/></Border><ControlTemplate.Triggers><Trigger Property="IsKeyboardFocusWithin" Value="True"><Setter TargetName="TextBoxChrome" Property="BorderBrush" Value="{StaticResource AccentStroke}"/></Trigger><Trigger Property="IsReadOnly" Value="True"><Setter TargetName="TextBoxChrome" Property="Background" Value="{StaticResource ChromeSurface2}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="TextBoxChrome" Property="Opacity" Value="0.56"/><Setter Property="Foreground" Value="{StaticResource Muted}"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style>
    <Style TargetType="Button">
      <Setter Property="Padding" Value="14,9"/><Setter Property="FontSize" Value="14.5"/><Setter Property="Margin" Value="0,0,8,0"/><Setter Property="MinHeight" Value="40"/><Setter Property="MinWidth" Value="40"/><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="BorderBrush" Value="{StaticResource Line}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type Button}"><Border x:Name="ButtonChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" CornerRadius="8" Padding="{TemplateBinding Padding}" SnapsToDevicePixels="True"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" RecognizesAccessKey="True"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="ButtonChrome" Property="Background" Value="{StaticResource CardHover}"/><Setter TargetName="ButtonChrome" Property="BorderBrush" Value="{StaticResource LineStrong}"/></Trigger><Trigger Property="IsPressed" Value="True"><Setter TargetName="ButtonChrome" Property="Background" Value="{StaticResource ChromeSurface2}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="ButtonChrome" Property="Background" Value="{StaticResource ChromeSurface2}"/><Setter TargetName="ButtonChrome" Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter TargetName="ButtonChrome" Property="Opacity" Value="0.62"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="PrimaryButton" TargetType="Button"><Setter Property="Padding" Value="15,9"/><Setter Property="FontSize" Value="14.5"/><Setter Property="Margin" Value="0,0,8,0"/><Setter Property="MinHeight" Value="40"/><Setter Property="MinWidth" Value="40"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/><Setter Property="Background" Value="{StaticResource Accent}"/><Setter Property="Foreground" Value="{StaticResource Bg}"/><Setter Property="BorderBrush" Value="{StaticResource AccentStroke}"/><Setter Property="BorderThickness" Value="1"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Effect" Value="{StaticResource AccentGlow}"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type Button}"><Border x:Name="PrimaryChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="8" Padding="{TemplateBinding Padding}" SnapsToDevicePixels="True"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" RecognizesAccessKey="True"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="PrimaryChrome" Property="Background" Value="{StaticResource AccentHover}"/><Setter TargetName="PrimaryChrome" Property="BorderBrush" Value="{StaticResource AccentHover}"/></Trigger><Trigger Property="IsPressed" Value="True"><Setter TargetName="PrimaryChrome" Property="Background" Value="{StaticResource AccentPressed}"/><Setter TargetName="PrimaryChrome" Property="BorderBrush" Value="{StaticResource AccentPressed}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="PrimaryChrome" Property="Opacity" Value="0.42"/><Setter Property="Effect" Value="{x:Null}"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style>
    <Style x:Key="LanguageSegmentButton" TargetType="{x:Type RadioButton}">
      <Setter Property="Foreground" Value="{StaticResource Secondary}"/>
      <Setter Property="Background" Value="{StaticResource Panel2}"/>
      <Setter Property="BorderBrush" Value="{StaticResource Line}"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="13,7"/>
      <Setter Property="MinWidth" Value="52"/>
      <Setter Property="MinHeight" Value="34"/>
      <Setter Property="Margin" Value="0,0,6,0"/>
      <Setter Property="FontSize" Value="13"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="HorizontalContentAlignment" Value="Center"/>
      <Setter Property="VerticalContentAlignment" Value="Center"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type RadioButton}">
        <Border x:Name="SegmentChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="8" Padding="{TemplateBinding Padding}" SnapsToDevicePixels="True">
          <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" RecognizesAccessKey="True"/>
        </Border>
        <ControlTemplate.Triggers>
          <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="SegmentChrome" Property="Background" Value="{StaticResource CardHover}"/><Setter TargetName="SegmentChrome" Property="BorderBrush" Value="#435160"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger>
          <Trigger Property="IsChecked" Value="True"><Setter TargetName="SegmentChrome" Property="Background" Value="{StaticResource AccentSoft}"/><Setter TargetName="SegmentChrome" Property="BorderBrush" Value="{StaticResource AccentStroke}"/><Setter Property="Foreground" Value="{StaticResource Accent}"/></Trigger>
          <Trigger Property="IsEnabled" Value="False"><Setter TargetName="SegmentChrome" Property="Opacity" Value="0.45"/></Trigger>
        </ControlTemplate.Triggers>
      </ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="ModernRememberToggle" TargetType="{x:Type CheckBox}">
      <Setter Property="Foreground" Value="{StaticResource Secondary}"/>
      <Setter Property="FontSize" Value="13.5"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type CheckBox}">
        <Grid Background="Transparent"><Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
          <Border x:Name="ToggleTrack" Width="38" Height="22" CornerRadius="11" Background="{StaticResource Panel2}" BorderBrush="{StaticResource Line}" BorderThickness="1" VerticalAlignment="Center">
            <Grid><Ellipse x:Name="ToggleThumb" Width="14" Height="14" Fill="{StaticResource Secondary}" HorizontalAlignment="Left" Margin="3,0,0,0" VerticalAlignment="Center"/></Grid>
          </Border>
          <ContentPresenter Grid.Column="1" Margin="10,0,0,0" VerticalAlignment="Center" RecognizesAccessKey="True"/>
        </Grid>
        <ControlTemplate.Triggers>
          <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="ToggleTrack" Property="BorderBrush" Value="#526170"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger>
          <Trigger Property="IsChecked" Value="True"><Setter TargetName="ToggleTrack" Property="Background" Value="{StaticResource AccentSoft}"/><Setter TargetName="ToggleTrack" Property="BorderBrush" Value="{StaticResource AccentStroke}"/><Setter TargetName="ToggleThumb" Property="Fill" Value="{StaticResource Accent}"/><Setter TargetName="ToggleThumb" Property="HorizontalAlignment" Value="Right"/><Setter TargetName="ToggleThumb" Property="Margin" Value="0,0,3,0"/></Trigger>
          <Trigger Property="IsEnabled" Value="False"><Setter Property="Opacity" Value="0.45"/></Trigger>
        </ControlTemplate.Triggers>
      </ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="BackendRetryButton" TargetType="{x:Type Button}">
      <Setter Property="Foreground" Value="{StaticResource Warning}"/>
      <Setter Property="Background" Value="#241D10"/>
      <Setter Property="BorderBrush" Value="#9E7930"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="11,5"/>
      <Setter Property="MinHeight" Value="30"/>
      <Setter Property="MinWidth" Value="58"/>
      <Setter Property="Margin" Value="0"/>
      <Setter Property="FontSize" Value="12.5"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type Button}">
        <Border x:Name="RetryChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="7" Padding="{TemplateBinding Padding}">
          <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" RecognizesAccessKey="True"/>
        </Border>
        <ControlTemplate.Triggers>
          <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="RetryChrome" Property="Background" Value="#352A15"/><Setter TargetName="RetryChrome" Property="BorderBrush" Value="{StaticResource Warning}"/></Trigger>
          <Trigger Property="IsPressed" Value="True"><Setter TargetName="RetryChrome" Property="Opacity" Value="0.82"/></Trigger>
          <Trigger Property="IsEnabled" Value="False"><Setter TargetName="RetryChrome" Property="Opacity" Value="0.45"/></Trigger>
        </ControlTemplate.Triggers>
      </ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="ProductTabItem" TargetType="{x:Type TabItem}">
      <Setter Property="Padding" Value="14,9"/><Setter Property="Margin" Value="0,0,7,0"/><Setter Property="MinHeight" Value="40"/><Setter Property="FontSize" Value="14"/><Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="Background" Value="{StaticResource TabIdle}"/><Setter Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="BorderThickness" Value="1"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type TabItem}"><Grid><Border x:Name="TabChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="8" Padding="{TemplateBinding Padding}" SnapsToDevicePixels="True"><ContentPresenter ContentSource="Header" HorizontalAlignment="Center" VerticalAlignment="Center" RecognizesAccessKey="True"/></Border><Border x:Name="ActiveLine" Height="2" Margin="10,0,10,-1" VerticalAlignment="Bottom" Background="{StaticResource Accent}" CornerRadius="1" Visibility="Collapsed"/></Grid><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="TabChrome" Property="Background" Value="{StaticResource TabHover}"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger><Trigger Property="IsSelected" Value="True"><Setter TargetName="TabChrome" Property="Background" Value="{StaticResource TabSelected}"/><Setter TargetName="TabChrome" Property="BorderBrush" Value="{StaticResource CardStroke}"/><Setter TargetName="ActiveLine" Property="Visibility" Value="Visible"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="TabChrome" Property="Opacity" Value="0.45"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="ProductTabControl" TargetType="{x:Type TabControl}"><Setter Property="Background" Value="Transparent"/><Setter Property="BorderBrush" Value="Transparent"/><Setter Property="BorderThickness" Value="0"/><Setter Property="Padding" Value="0"/></Style>
    <Style x:Key="ChromeHeaderBorder" TargetType="Border"><Setter Property="Background" Value="{StaticResource ChromeSurface}"/><Setter Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="BorderThickness" Value="0,0,0,1"/><Setter Property="Effect" Value="{StaticResource ChromeShadow}"/></Style>
    <Style x:Key="ChromeSubheaderBorder" TargetType="Border"><Setter Property="Background" Value="{StaticResource ChromeSurface2}"/><Setter Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="BorderThickness" Value="0,0,0,1"/></Style>
    <Style x:Key="ChromeStatusBorder" TargetType="Border"><Setter Property="Background" Value="{StaticResource ChromeSurface}"/><Setter Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="BorderThickness" Value="0,1,0,0"/></Style>
    <Style TargetType="PasswordBox"><Setter Property="Padding" Value="11,9"/><Setter Property="FontSize" Value="14.5"/><Setter Property="MinHeight" Value="40"/><Setter Property="BorderBrush" Value="{StaticResource Line}"/><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="CaretBrush" Value="{StaticResource Text}"/></Style>
    <Style TargetType="ComboBox">
      <Setter Property="Padding" Value="10,8"/><Setter Property="FontSize" Value="14"/><Setter Property="MinHeight" Value="40"/><Setter Property="BorderBrush" Value="{StaticResource Line}"/><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type ComboBox}"><Grid><Border x:Name="ComboChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" CornerRadius="7"><Grid><ContentPresenter Margin="10,0,34,0" VerticalAlignment="Center" HorizontalAlignment="Left" IsHitTestVisible="False" Content="{TemplateBinding SelectionBoxItem}" ContentTemplate="{TemplateBinding SelectionBoxItemTemplate}" ContentTemplateSelector="{TemplateBinding ItemTemplateSelector}"/><Path Width="8" Height="5" HorizontalAlignment="Right" VerticalAlignment="Center" Margin="0,0,12,0" Fill="{StaticResource Secondary}" Data="M 0 0 L 4 4 L 8 0 Z"/><ToggleButton Focusable="False" Background="Transparent" BorderThickness="0" IsChecked="{Binding IsDropDownOpen, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}" ClickMode="Press"><ToggleButton.Template><ControlTemplate TargetType="{x:Type ToggleButton}"><Border Background="Transparent"/></ControlTemplate></ToggleButton.Template></ToggleButton></Grid></Border><Popup x:Name="PART_Popup" Placement="Bottom" IsOpen="{TemplateBinding IsDropDownOpen}" AllowsTransparency="True" Focusable="False" PopupAnimation="Fade"><Border Background="{StaticResource PanelElevated}" BorderBrush="{StaticResource LineStrong}" BorderThickness="1" CornerRadius="8" Padding="4" Margin="0,4,0,0" Effect="{StaticResource ChromeShadow}"><ScrollViewer MaxHeight="320" VerticalScrollBarVisibility="Auto"><ItemsPresenter/></ScrollViewer></Border></Popup></Grid><ControlTemplate.Triggers><Trigger Property="IsKeyboardFocusWithin" Value="True"><Setter TargetName="ComboChrome" Property="BorderBrush" Value="{StaticResource AccentStroke}"/></Trigger><Trigger Property="IsDropDownOpen" Value="True"><Setter TargetName="ComboChrome" Property="BorderBrush" Value="{StaticResource AccentStroke}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="ComboChrome" Property="Background" Value="{StaticResource ChromeSurface2}"/><Setter TargetName="ComboChrome" Property="Opacity" Value="0.58"/><Setter Property="Foreground" Value="{StaticResource Muted}"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="QueueComboItem" TargetType="{x:Type ComboBoxItem}"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Padding" Value="10,8"/><Setter Property="HorizontalContentAlignment" Value="Stretch"/><Style.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter Property="Background" Value="{StaticResource CardHover}"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger><Trigger Property="IsSelected" Value="True"><Setter Property="Background" Value="{StaticResource AccentSoft}"/><Setter Property="Foreground" Value="{StaticResource Accent}"/><Setter Property="FontWeight" Value="SemiBold"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter Property="Foreground" Value="{StaticResource Muted}"/></Trigger></Style.Triggers></Style>

    <Style x:Key="ProductNavButton" TargetType="{x:Type Button}">
      <Setter Property="Background" Value="Transparent"/><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="BorderBrush" Value="Transparent"/><Setter Property="BorderThickness" Value="1"/><Setter Property="Padding" Value="14,8"/><Setter Property="Margin" Value="0,0,5,0"/><Setter Property="MinHeight" Value="34"/><Setter Property="FontSize" Value="13.5"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type Button}"><Border x:Name="NavChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="8" Padding="{TemplateBinding Padding}"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="NavChrome" Property="Background" Value="{StaticResource CardHover}"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Trigger><Trigger Property="IsPressed" Value="True"><Setter TargetName="NavChrome" Property="Background" Value="{StaticResource AccentSoft}"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="ContextNavButton" TargetType="{x:Type Button}" BasedOn="{StaticResource ProductNavButton}"><Setter Property="Padding" Value="10,6"/><Setter Property="MinHeight" Value="30"/><Setter Property="FontSize" Value="12.5"/><Setter Property="Margin" Value="0,0,6,0"/></Style>
    <Style x:Key="ConceptContentTabItem" TargetType="{x:Type TabItem}"><Setter Property="Width" Value="0"/><Setter Property="Height" Value="0"/><Setter Property="MinWidth" Value="0"/><Setter Property="MinHeight" Value="0"/><Setter Property="Padding" Value="0"/><Setter Property="Margin" Value="0"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type TabItem}"><Border Width="0" Height="0" Background="Transparent"/></ControlTemplate></Setter.Value></Setter></Style>
    <Style x:Key="BrandHomeButton" TargetType="{x:Type Button}">
      <Setter Property="Background" Value="Transparent"/><Setter Property="BorderBrush" Value="Transparent"/><Setter Property="Padding" Value="8,5"/><Setter Property="Margin" Value="-8,-5,0,-5"/><Setter Property="HorizontalContentAlignment" Value="Left"/><Setter Property="Cursor" Value="Hand"/><Setter Property="ToolTip" Value="Home / Overview"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type Button}"><Border x:Name="BrandChrome" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" CornerRadius="9" Padding="{TemplateBinding Padding}"><ContentPresenter HorizontalAlignment="Left" VerticalAlignment="Center"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="BrandChrome" Property="Background" Value="{StaticResource ChromeSurface2}"/><Setter TargetName="BrandChrome" Property="BorderBrush" Value="{StaticResource ChromeStroke}"/></Trigger><Trigger Property="IsPressed" Value="True"><Setter TargetName="BrandChrome" Property="Background" Value="{StaticResource AccentSoft}"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="CardSurfaceBorder" TargetType="Border"><Setter Property="Background" Value="{StaticResource CardSurface}"/><Setter Property="BorderBrush" Value="{StaticResource CardStroke}"/><Setter Property="BorderThickness" Value="1"/><Setter Property="CornerRadius" Value="12"/><Setter Property="Padding" Value="16"/></Style>
    <Style x:Key="KpiCard" TargetType="Border" BasedOn="{StaticResource CardSurfaceBorder}"><Setter Property="Padding" Value="18"/><Setter Property="MinHeight" Value="118"/></Style>
    <Style x:Key="EmptyStateBorder" TargetType="Border" BasedOn="{StaticResource CardSurfaceBorder}"><Setter Property="Background" Value="{StaticResource ChromeSurface2}"/><Setter Property="BorderBrush" Value="{StaticResource ChromeStroke}"/><Setter Property="Padding" Value="18"/><Setter Property="CornerRadius" Value="10"/><Setter Property="MinHeight" Value="88"/></Style>
    <Style x:Key="EmptyStateTitleText" TargetType="TextBlock" BasedOn="{StaticResource SubsectionTitleText}"><Setter Property="Foreground" Value="{StaticResource Secondary}"/></Style>
    <Style x:Key="EmptyStateBodyText" TargetType="TextBlock" BasedOn="{StaticResource QueueBodyText}"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="LineHeight" Value="19"/></Style>
    <Style x:Key="EmptyStateInlineText" TargetType="TextBlock" BasedOn="{StaticResource MetaText}"><Setter Property="Foreground" Value="{StaticResource Muted}"/><Setter Property="FontStyle" Value="Italic"/></Style>
    <Style x:Key="MediaFrameBorder" TargetType="Border"><Setter Property="Background" Value="{StaticResource MediaSurface}"/><Setter Property="BorderBrush" Value="{StaticResource MediaStroke}"/><Setter Property="BorderThickness" Value="1"/><Setter Property="CornerRadius" Value="12"/><Setter Property="Padding" Value="9"/><Setter Property="Effect" Value="{StaticResource MediaShadow}"/><Setter Property="SnapsToDevicePixels" Value="True"/></Style>
    <Style x:Key="MediaPreviewImage" TargetType="Image"><Setter Property="Stretch" Value="Uniform"/><Setter Property="SnapsToDevicePixels" Value="True"/><Setter Property="UseLayoutRounding" Value="True"/><Setter Property="RenderOptions.BitmapScalingMode" Value="HighQuality"/><Setter Property="HorizontalAlignment" Value="Stretch"/><Setter Property="VerticalAlignment" Value="Stretch"/></Style>
    <Style x:Key="MediaPlaceholderText" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource MediaStatus}"/><Setter Property="FontSize" Value="12.5"/><Setter Property="TextAlignment" Value="Center"/><Setter Property="TextWrapping" Value="Wrap"/><Setter Property="HorizontalAlignment" Value="Center"/><Setter Property="VerticalAlignment" Value="Center"/><Setter Property="Margin" Value="18"/></Style>
    <Style x:Key="MediaFrameLabel" TargetType="TextBlock"><Setter Property="Foreground" Value="{StaticResource Secondary}"/><Setter Property="FontSize" Value="12.5"/><Setter Property="FontWeight" Value="SemiBold"/></Style>
    <Style x:Key="StatusInfoText" TargetType="TextBlock" BasedOn="{StaticResource MetaText}"><Setter Property="Foreground" Value="{StaticResource Info}"/></Style>
    <Style x:Key="StatusWarningText" TargetType="TextBlock" BasedOn="{StaticResource MetaText}"><Setter Property="Foreground" Value="{StaticResource Warning}"/></Style>
    <Style x:Key="StatusDangerText" TargetType="TextBlock" BasedOn="{StaticResource MetaText}"><Setter Property="Foreground" Value="{StaticResource Danger}"/></Style>
    <Style x:Key="StatusSuccessText" TargetType="TextBlock" BasedOn="{StaticResource MetaText}"><Setter Property="Foreground" Value="{StaticResource Success}"/></Style>
    <Style x:Key="CardListBoxItem" TargetType="{x:Type ListBoxItem}">
      <Setter Property="Margin" Value="0,0,0,10"/><Setter Property="Padding" Value="14,13"/><Setter Property="Background" Value="{StaticResource CardSurface}"/><Setter Property="BorderBrush" Value="{StaticResource CardStroke}"/><Setter Property="BorderThickness" Value="1"/><Setter Property="HorizontalContentAlignment" Value="Stretch"/><Setter Property="VerticalContentAlignment" Value="Center"/><Setter Property="FocusVisualStyle" Value="{StaticResource KeyboardFocusStyle}"/>
      <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="{x:Type ListBoxItem}"><Border x:Name="Card" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="10" Padding="{TemplateBinding Padding}" SnapsToDevicePixels="True"><ContentPresenter HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="{TemplateBinding VerticalContentAlignment}"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Card" Property="Background" Value="{StaticResource CardHover}"/><Setter TargetName="Card" Property="BorderBrush" Value="#435160"/></Trigger><Trigger Property="IsSelected" Value="True"><Setter TargetName="Card" Property="Background" Value="{StaticResource CardSelected}"/><Setter TargetName="Card" Property="BorderBrush" Value="{StaticResource AccentStroke}"/><Setter TargetName="Card" Property="BorderThickness" Value="1.5"/><Setter TargetName="Card" Property="Effect" Value="{StaticResource AccentGlow}"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="Card" Property="Opacity" Value="0.52"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
    </Style>
    <Style x:Key="ConceptCardListBoxItem" TargetType="{x:Type ListBoxItem}" BasedOn="{StaticResource CardListBoxItem}"><Setter Property="Padding" Value="15,14"/><Setter Property="MinHeight" Value="112"/></Style>
    <Style TargetType="TabControl"><Setter Property="Background" Value="{StaticResource Panel}"/><Setter Property="Foreground" Value="{StaticResource Text}"/></Style>
  </Window.Resources>
  <Grid>
    <Grid x:Name="LoginGrid">
      <Border MaxWidth="520" Margin="20" Padding="32" Background="{StaticResource PanelElevated}" BorderBrush="{StaticResource Line}" BorderThickness="1" CornerRadius="12" HorizontalAlignment="Center" VerticalAlignment="Center" Effect="{StaticResource SurfaceShadow}">
        <StackPanel>
          <TextBlock Text="Merch Forge" Style="{StaticResource DisplayTitleText}"/>
          <TextBlock Text="Internal Workbench" Style="{StaticResource SubtitleText}" Margin="0,4,0,20"/>
          <TextBlock Text="Workspace access" Style="{StaticResource FieldLabelText}" Margin="0,0,0,6"/>
          <PasswordBox x:Name="OwnerKeyBox" Padding="10" Height="40" AutomationProperties.Name="Workspace access"/>
          <TextBlock x:Name="LoginLanguageLabel" Text="Language" Style="{StaticResource FieldLabelText}" Margin="0,18,0,8"/>
          <StackPanel Orientation="Horizontal">
            <RadioButton x:Name="LoginLangEn" Content="EN" Tag="en" GroupName="LoginLanguage" Style="{StaticResource LanguageSegmentButton}" IsChecked="True" AutomationProperties.Name="English interface"/>
            <RadioButton x:Name="LoginLangRu" Content="RU" Tag="ru" GroupName="LoginLanguage" Style="{StaticResource LanguageSegmentButton}" AutomationProperties.Name="Русский интерфейс"/>
            <RadioButton x:Name="LoginLangEs" Content="ES" Tag="es" GroupName="LoginLanguage" Style="{StaticResource LanguageSegmentButton}" AutomationProperties.Name="Interfaz en español"/>
          </StackPanel>
          <ComboBox x:Name="LoginLanguageBox" Visibility="Collapsed" SelectedIndex="0"><ComboBoxItem Content="EN" Tag="en"/><ComboBoxItem Content="RU" Tag="ru"/><ComboBoxItem Content="ES" Tag="es"/></ComboBox>
          <TextBlock x:Name="LoginLanguageStatusText" Visibility="Collapsed" Text="English"/>
          <CheckBox x:Name="RememberBox" Content="Remember on this Windows account" Style="{StaticResource ModernRememberToggle}" IsChecked="True" Margin="0,18,0,18" AutomationProperties.Name="Remember workspace access on this Windows account"/>
          <Button x:Name="ConnectButton" Content="Open Workbench" Style="{StaticResource PrimaryButton}" Height="44" ToolTip="Connect to your Merch Forge workspace and open the workbench" AutomationProperties.Name="Open Merch Forge Workbench"/>
          <TextBlock x:Name="SavedAccessText" Text="Saved access is protected for your Windows account." Style="{StaticResource MutedCaptionText}" Margin="0,10,0,0"/>
        </StackPanel>
      </Border>
    </Grid>

    <Grid x:Name="AppGrid" Visibility="Collapsed">
      <Grid.RowDefinitions><RowDefinition Height="64"/><RowDefinition Height="48"/><RowDefinition Height="*"/><RowDefinition Height="34"/></Grid.RowDefinitions>
      <Border Grid.Row="0" Style="{StaticResource ChromeHeaderBorder}" Padding="20,12">
        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
          <Grid><Button x:Name="HomeButton" Style="{StaticResource BrandHomeButton}" AutomationProperties.Name="Merch Forge home"><StackPanel x:Name="HeaderIdentity"><TextBlock Text="Merch Forge" Style="{StaticResource AppTitleText}"/><TextBlock x:Name="HeaderSub" Text="Commerce workspace" Style="{StaticResource MetaText}"/></StackPanel></Button><ComboBox x:Name="CompactConceptBox" Visibility="Collapsed" DisplayMemberPath="title" MinWidth="80" MaxWidth="220" VerticalAlignment="Center" ToolTip="Select concept" AutomationProperties.Name="Select concept"/></Grid>
          <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center">
            <TextBlock x:Name="ActorText" Text="Not connected" Style="{StaticResource MetaText}" VerticalAlignment="Center" Margin="0,0,14,0"/>
            <TextBlock x:Name="LanguageLabel" Text="Language" Style="{StaticResource MetaText}" VerticalAlignment="Center" Margin="0,0,8,0"/>
            <StackPanel x:Name="HeaderLanguageSegment" Orientation="Horizontal" Margin="0,0,10,0">
              <RadioButton x:Name="HeaderLangEn" Content="EN" Tag="en" GroupName="HeaderLanguage" Style="{StaticResource LanguageSegmentButton}" MinWidth="38" MinHeight="30" Padding="8,5" IsChecked="True" AutomationProperties.Name="English interface"/>
              <RadioButton x:Name="HeaderLangRu" Content="RU" Tag="ru" GroupName="HeaderLanguage" Style="{StaticResource LanguageSegmentButton}" MinWidth="38" MinHeight="30" Padding="8,5" AutomationProperties.Name="Русский интерфейс"/>
              <RadioButton x:Name="HeaderLangEs" Content="ES" Tag="es" GroupName="HeaderLanguage" Style="{StaticResource LanguageSegmentButton}" MinWidth="38" MinHeight="30" Padding="8,5" Margin="0" AutomationProperties.Name="Interfaz en español"/>
            </StackPanel>
            <ComboBox x:Name="LanguageBox" Visibility="Collapsed" SelectedIndex="0"><ComboBoxItem Content="EN" Tag="en"/><ComboBoxItem Content="RU" Tag="ru"/><ComboBoxItem Content="ES" Tag="es"/></ComboBox>
            <TextBlock x:Name="LanguageStatusText" Visibility="Collapsed" Text="English"/>
            <Button x:Name="AboutButton" Content="About" ToolTip="About Merch Forge, this build, and what the workbench does" AutomationProperties.Name="About Merch Forge"/><Button x:Name="DiagnosticsButton" Visibility="Collapsed" Content="Diagnostics" ToolTip="Open safe in-app connection and runtime diagnostics" AutomationProperties.Name="Open diagnostics"/><Button x:Name="RefreshButton" Content="Refresh" ToolTip="Reload concepts and current workspace state" AutomationProperties.Name="Refresh Workbench"/><Button x:Name="ForgetButton" Content="Sign out" ToolTip="Sign out and remove saved access from this Windows account" AutomationProperties.Name="Sign out and remove saved access"/>
          </StackPanel>
        </Grid>
      </Border>
      <Border Grid.Row="1" Background="{StaticResource ChromeSurface}" BorderBrush="{StaticResource ChromeStroke}" BorderThickness="0,0,0,1" Padding="18,6">
        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
          <StackPanel x:Name="ProductNav" Orientation="Horizontal">
            <Button x:Name="NavHomeButton" Content="Home" Tag="home" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavDiscoverButton" Content="Discover" Tag="discover" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavIdeasButton" Content="Ideas" Tag="ideas" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavArtworkButton" Content="Artwork" Tag="artwork" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavChecksButton" Content="Checks" Tag="checks" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavPublishButton" Content="Publish" Tag="publish" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavPortfolioButton" Content="Portfolio" Tag="portfolio" Style="{StaticResource ProductNavButton}"/>
            <Button x:Name="NavPerformanceButton" Content="Performance" Tag="performance" Style="{StaticResource ProductNavButton}"/>
          </StackPanel>
          <TextBlock Grid.Column="1" x:Name="ProductNavHint" Text="Product workspace" Style="{StaticResource MutedCaptionText}" VerticalAlignment="Center" Margin="16,0,0,0"/>
        </Grid>
      </Border>

      <Grid Grid.Row="2" x:Name="WorkAreaGrid" Margin="12">
        <Grid.ColumnDefinitions><ColumnDefinition x:Name="QueueColumn" Width="390" MinWidth="340" MaxWidth="420"/><ColumnDefinition x:Name="QueueGapColumn" Width="14"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
        <Border x:Name="BusyBanner" Grid.ColumnSpan="3" Visibility="Collapsed" VerticalAlignment="Top" HorizontalAlignment="Center" Margin="10" Padding="14,8" Background="{StaticResource InfoSoft}" BorderBrush="{StaticResource Info}" BorderThickness="1" CornerRadius="8" Panel.ZIndex="50">
          <TextBlock x:Name="BusyText" Text="Working…" FontWeight="SemiBold" Foreground="{StaticResource Info}"/>
        </Border>
        <Border x:Name="ConceptPane" Grid.Column="0" Background="{StaticResource ChromeSurface}" BorderBrush="{StaticResource ChromeStroke}" BorderThickness="1" CornerRadius="12" Padding="16" Effect="{StaticResource SurfaceShadow}">
          <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
            <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock x:Name="ConceptsLabel" Text="Concepts" Style="{StaticResource SectionTitleText}"/><TextBlock Grid.Column="1" x:Name="QueueCountText" Text="0" Style="{StaticResource MutedCaptionText}" VerticalAlignment="Center" Margin="10,0,0,0"/></Grid>
            <StackPanel Grid.Row="1" Margin="0,12,0,10">
              <TextBlock x:Name="SearchLabel" Text="Search" Style="{StaticResource FieldLabelText}"/>
              <Grid Margin="0,6,0,0"><TextBox x:Name="SearchBox" Padding="10,8" ToolTip="Search title, slogan or profession" AutomationProperties.Name="Search concepts"/><TextBlock x:Name="SearchPlaceholder" Text="Title, slogan or profession" Foreground="{StaticResource Muted}" Margin="12,0,0,0" VerticalAlignment="Center" IsHitTestVisible="False" FontSize="13.5"/></Grid>
            </StackPanel>
            <Grid Grid.Row="2" Margin="0,0,0,12"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="10"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
              <StackPanel><TextBlock x:Name="StatusLabel" Text="Status" Style="{StaticResource FieldLabelText}"/><ComboBox x:Name="FilterBox" SelectedIndex="0" Margin="0,6,0,0" ItemContainerStyle="{StaticResource QueueComboItem}" ToolTip="Show concepts by workflow status" AutomationProperties.Name="Filter concepts by workflow state"><ComboBoxItem Content="All statuses" Tag=""/><ComboBoxItem Content="Ready to generate" Tag="generation_ready"/><ComboBoxItem Content="Editing" Tag="in_edit"/><ComboBoxItem Content="Generation requested" Tag="generation_requested"/><ComboBoxItem Content="Has variants" Tag="has_variants"/><ComboBoxItem Content="Accepted" Tag="accepted"/><ComboBoxItem Content="Blocked" Tag="blocked"/><ComboBoxItem Content="Research draft" Tag="research_draft"/><ComboBoxItem Content="Stage: No decision" Tag="stage:undecided"/><ComboBoxItem Content="Stage: EDIT" Tag="stage:edit"/><ComboBoxItem Content="Stage: REGEN" Tag="stage:regen"/><ComboBoxItem Content="Stage: KEEP · no artwork" Tag="stage:keep_no_artwork"/><ComboBoxItem Content="Stage: Artwork accepted" Tag="stage:artwork_accepted"/><ComboBoxItem Content="Stage: Checks passed" Tag="stage:checks_ready"/><ComboBoxItem Content="Stage: Package ready" Tag="stage:package_ready"/><ComboBoxItem Content="Stage: Published" Tag="stage:published"/><ComboBoxItem Content="Stage: SKIP" Tag="stage:skip"/></ComboBox></StackPanel>
              <StackPanel Grid.Column="2"><TextBlock x:Name="SortLabel" Text="Sort" Style="{StaticResource FieldLabelText}"/><ComboBox x:Name="SortBox" SelectedIndex="0" Margin="0,6,0,0" ItemContainerStyle="{StaticResource QueueComboItem}" ToolTip="Sort the concept queue" AutomationProperties.Name="Sort concepts"><ComboBoxItem Content="Score: high to low" Tag="score"/><ComboBoxItem Content="Title: A to Z" Tag="title"/><ComboBoxItem Content="Workflow status" Tag="workflow"/></ComboBox></StackPanel>
            </Grid>
            <Grid Grid.Row="3">
              <ListBox x:Name="ConceptList" BorderThickness="0" Background="Transparent" ItemContainerStyle="{StaticResource ConceptCardListBoxItem}" Margin="0,2,0,0" ScrollViewer.HorizontalScrollBarVisibility="Disabled" ScrollViewer.VerticalScrollBarVisibility="Auto" HorizontalContentAlignment="Stretch" AutomationProperties.Name="Concept queue">
              <ListBox.ItemTemplate><DataTemplate>
                <Grid ToolTip="{Binding title}"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                  <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock Text="{Binding title}" Style="{StaticResource QueueTitleText}" TextWrapping="NoWrap" TextTrimming="CharacterEllipsis" ToolTip="{Binding title}"/><Border Grid.Column="1" Background="{StaticResource AccentSoft}" BorderBrush="{StaticResource AccentStroke}" BorderThickness="1" CornerRadius="9" Padding="7,2" Margin="10,0,0,0" VerticalAlignment="Top"><TextBlock Text="{Binding score_label}" Style="{StaticResource MetricValueText}"/></Border></Grid>
                  <TextBlock Grid.Row="1" Text="{Binding hook}" Style="{StaticResource QueueBodyText}" TextWrapping="Wrap" TextTrimming="CharacterEllipsis" MaxHeight="42" Margin="0,8,0,10" ToolTip="{Binding hook}"/>
                  <Grid Grid.Row="2"><Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions><Border Background="{Binding workflow_background}" BorderBrush="{Binding workflow_foreground}" BorderThickness="1" CornerRadius="8" Padding="8,3" MaxWidth="156"><TextBlock Text="{Binding workflow_label}" Foreground="{Binding workflow_foreground}" FontSize="12" FontWeight="SemiBold" TextTrimming="CharacterEllipsis"/></Border><TextBlock Grid.Column="1" Text="{Binding niche_name}" Style="{StaticResource QueueMetaText}" Margin="10,0,0,0" VerticalAlignment="Center" HorizontalAlignment="Right" TextAlignment="Right" TextTrimming="CharacterEllipsis" ToolTip="{Binding niche_name}"/></Grid>
                </Grid>
              </DataTemplate></ListBox.ItemTemplate>
              </ListBox>
              <Border x:Name="QueueEmptyPanel" Visibility="Collapsed" Style="{StaticResource EmptyStateBorder}" VerticalAlignment="Top">
                <StackPanel VerticalAlignment="Center"><TextBlock x:Name="QueueEmptyTitle" Text="No concepts" Style="{StaticResource EmptyStateTitleText}"/><TextBlock x:Name="QueueEmptyBody" Text="There are no concepts in this workspace yet." Style="{StaticResource EmptyStateBodyText}" TextWrapping="Wrap" Margin="0,6,0,0"/></StackPanel>
              </Border>
            </Grid>
          </Grid>
        </Border>

        <Border Grid.Column="2" Background="{StaticResource PanelElevated}" BorderBrush="{StaticResource Line}" BorderThickness="1" CornerRadius="12" Effect="{StaticResource SurfaceShadow}">
          <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
            <Border Style="{StaticResource ChromeSubheaderBorder}" Padding="18,13">
              <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <StackPanel><TextBlock x:Name="ConceptTitle" Text="Select a concept" Style="{StaticResource ConceptTitleText}" TextTrimming="CharacterEllipsis"/><TextBlock x:Name="ConceptMeta" Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel>
                <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center">
                  <StackPanel x:Name="ContextNav" Orientation="Horizontal" Visibility="Collapsed" Margin="0,0,8,0">
                    <Button x:Name="ContextHistoryButton" Content="History" Style="{StaticResource ContextNavButton}"/>
                    <Button x:Name="ContextDeliveryButton" Content="Delivery" Style="{StaticResource ContextNavButton}"/>
                    <Button x:Name="ContextEditButton" Content="Edit" Style="{StaticResource ContextNavButton}"/>
                  </StackPanel>
                  <Border x:Name="BackendBanner" Visibility="Collapsed" Padding="11,7" Margin="0,0,10,0" Background="{StaticResource WarningSoft}" BorderBrush="#9E7930" BorderThickness="1" CornerRadius="9" ToolTip="Live workspace data is temporarily unavailable. The Workbench remains open.">
                    <StackPanel Orientation="Horizontal" VerticalAlignment="Center"><Ellipse Width="7" Height="7" Fill="{StaticResource Warning}" Margin="0,0,8,0"/><TextBlock x:Name="BackendBannerText" Text="Backend unavailable" Foreground="{StaticResource Warning}" FontSize="12.5" FontWeight="SemiBold" VerticalAlignment="Center" Margin="0,0,10,0"/><Button x:Name="BackendRetryButton" Content="Retry" Style="{StaticResource BackendRetryButton}" ToolTip="Retry backend connection" AutomationProperties.Name="Retry backend connection"/></StackPanel>
                  </Border>
                  <TextBlock x:Name="DirtyLabel" Text="" Style="{StaticResource StatusWarningText}" Margin="0,0,12,0" Visibility="Collapsed"/><Button x:Name="SaveButton" Content="Save new revision" Style="{StaticResource PrimaryButton}" IsEnabled="False" Visibility="Collapsed" ToolTip="Save your edits as a new immutable creative revision" AutomationProperties.Name="Save creative revision"/>
                </StackPanel>
              </Grid>
            </Border>
            <Grid Grid.Row="1">
              <ScrollViewer x:Name="HomeLandingScroll" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
                <Grid Margin="26">
                <StackPanel x:Name="HomeLandingPanel">
                  <Border Background="{StaticResource ChromeSurface2}" BorderBrush="{StaticResource ChromeStroke}" BorderThickness="1" CornerRadius="14" Padding="24" Effect="{StaticResource SurfaceShadow}">
                    <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="24"/><ColumnDefinition Width="300"/></Grid.ColumnDefinitions>
                      <StackPanel><TextBlock Text="MERCH FORGE" Foreground="{StaticResource Accent}" FontSize="12" FontWeight="Bold"/><TextBlock x:Name="HomeTitle" Visibility="Collapsed" Text="Business dashboard" Style="{StaticResource DisplayTitleText}" Margin="0,8,0,0"/><TextBlock x:Name="HomeBody" Text="Ideas, products and results in one place — from first concept to sales." Style="{StaticResource SubtitleText}" TextWrapping="Wrap" MaxWidth="780" HorizontalAlignment="Left" Margin="0,9,0,0"/></StackPanel>
                      <Border Grid.Column="2" Background="{StaticResource AccentSoft}" BorderBrush="{StaticResource AccentStroke}" BorderThickness="1" CornerRadius="12" Padding="16" VerticalAlignment="Center"><StackPanel><TextBlock x:Name="HomeStatusLabel" Text="WORKSPACE STATUS" Foreground="{StaticResource Accent}" FontSize="11.5" FontWeight="Bold"/><TextBlock x:Name="HomeConnectionText" Text="Offline" Style="{StaticResource SectionTitleText}" Margin="0,7,0,0"/><TextBlock x:Name="HomeConnectionBody" Text="Waiting for live data." Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel></Border>
                    </Grid>
                  </Border>
                  <UniformGrid Columns="4" Margin="0,16,0,0">
                    <Border Style="{StaticResource KpiCard}" Margin="0,0,8,0"><StackPanel><TextBlock x:Name="HomeMetricPublishedLabel" Text="Published" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="HomeMetricPublishedValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock x:Name="HomeMetricPublishedHint" Text="Waiting for live data" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock x:Name="HomeMetricSalesLabel" Text="Sales · 30 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="HomeMetricSalesValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock x:Name="HomeMetricSalesHint" Text="Waiting for live data" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock x:Name="HomeMetricRoyaltiesLabel" Text="Royalties · 30 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="HomeMetricRoyaltiesValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock x:Name="HomeMetricRoyaltiesHint" Text="Waiting for live data" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="8,0,0,0"><StackPanel><TextBlock x:Name="HomeMetricAttentionLabel" Text="Needs attention" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="HomeMetricAttentionValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock x:Name="HomeMetricAttentionHint" Text="Waiting for live data" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border>
                  </UniformGrid>
                  <Grid Margin="0,16,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="1.35*"/><ColumnDefinition Width="14"/><ColumnDefinition Width="0.65*"/></Grid.ColumnDefinitions>
                    <Border Grid.Column="0" Style="{StaticResource CardSurfaceBorder}" Padding="18"><StackPanel><TextBlock x:Name="HomePipelineTitle" Text="Pipeline" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="HomePipelineBody" Text="Move products through clear stages." Style="{StaticResource MetaText}" Margin="0,4,0,14"/><UniformGrid Columns="4"><Border Background="{StaticResource Panel2}" CornerRadius="10" Padding="12" Margin="0,0,6,0"><StackPanel><TextBlock Text="01" Foreground="{StaticResource Accent}" FontWeight="Bold"/><TextBlock x:Name="HomeStageIdeas" Text="Ideas" Style="{StaticResource SubsectionTitleText}" Margin="0,7,0,0"/><TextBlock Text="—" FontSize="22" FontWeight="Bold" Margin="0,5,0,0"/></StackPanel></Border><Border Background="{StaticResource Panel2}" CornerRadius="10" Padding="12" Margin="2,0,4,0"><StackPanel><TextBlock Text="02" Foreground="{StaticResource Accent}" FontWeight="Bold"/><TextBlock x:Name="HomeStageArtwork" Text="Artwork" Style="{StaticResource SubsectionTitleText}" Margin="0,7,0,0"/><TextBlock Text="—" FontSize="22" FontWeight="Bold" Margin="0,5,0,0"/></StackPanel></Border><Border Background="{StaticResource Panel2}" CornerRadius="10" Padding="12" Margin="4,0,2,0"><StackPanel><TextBlock Text="03" Foreground="{StaticResource Accent}" FontWeight="Bold"/><TextBlock x:Name="HomeStageChecks" Text="Checks" Style="{StaticResource SubsectionTitleText}" Margin="0,7,0,0"/><TextBlock Text="—" FontSize="22" FontWeight="Bold" Margin="0,5,0,0"/></StackPanel></Border><Border Background="{StaticResource Panel2}" CornerRadius="10" Padding="12" Margin="6,0,0,0"><StackPanel><TextBlock Text="04" Foreground="{StaticResource Accent}" FontWeight="Bold"/><TextBlock x:Name="HomeStagePublish" Text="Publish" Style="{StaticResource SubsectionTitleText}" Margin="0,7,0,0"/><TextBlock Text="—" FontSize="22" FontWeight="Bold" Margin="0,5,0,0"/></StackPanel></Border></UniformGrid></StackPanel></Border>
                    <StackPanel Grid.Column="2"><Border Style="{StaticResource CardSurfaceBorder}" Padding="18" Margin="0,0,0,12"><StackPanel><TextBlock x:Name="HomeAlexTitle" Text="Alex Needed" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="HomeAlexBody" Text="Reconnect to load decisions that need your attention." Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="18"><StackPanel><TextBlock x:Name="HomePerformanceTitle" Text="Performance snapshot" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="HomePerformanceBody" Text="Sales and royalties will appear here when live commerce data is connected." Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="18" Margin="0,12,0,0"><StackPanel><TextBlock Text="My data" Style="{StaticResource SectionTitleText}"/><TextBlock Text="A copy of your drafts, decisions, artwork, checks, packages and sales in one file. Access keys are not included." Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/><WrapPanel Margin="0,10,0,0"><Button x:Name="DataBackupButton" Content="Save a copy…" Margin="0,0,8,6"/><Button x:Name="DataRestoreButton" Content="Restore from a copy…" Margin="0,0,0,6"/></WrapPanel></StackPanel></Border></StackPanel>
                  </Grid>
                </StackPanel>
                </Grid>
              </ScrollViewer>
              <ScrollViewer x:Name="DiscoverLandingScroll" Visibility="Collapsed" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
                <StackPanel Margin="26">
                  <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                    <StackPanel><TextBlock x:Name="DiscoverTitle" Visibility="Collapsed" Text="Discover / Research" Style="{StaticResource DisplayTitleText}"/><TextBlock x:Name="DiscoverBody" Visibility="Collapsed" Text="Ranked market opportunities backed by Forge research, evidence and concept depth." Style="{StaticResource SubtitleText}" TextWrapping="Wrap" Margin="0,7,0,0"/></StackPanel>
                    <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center"><TextBlock x:Name="DiscoverStatusText" Text="Live research" Style="{StaticResource MetaText}" VerticalAlignment="Center" Margin="0,0,10,0"/><Button x:Name="DiscoverRefreshButton" Content="Refresh research"/></StackPanel>
                  </Grid>
                  <UniformGrid Columns="4" Margin="0,18,0,0">
                    <Border Style="{StaticResource KpiCard}" Margin="0,0,8,0"><StackPanel><TextBlock x:Name="DiscoverNichesLabel" Text="Niches" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverNichesValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock x:Name="DiscoverNotesLabel" Text="Research notes" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverNotesValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock x:Name="DiscoverSourcesLabel" Text="Active sources" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverSourcesValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border>
                    <Border Style="{StaticResource KpiCard}" Margin="8,0,0,0"><StackPanel><TextBlock x:Name="DiscoverConceptsLabel" Text="Concepts" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverConceptsValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border>
                  </UniformGrid>
                  <Grid Margin="0,16,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="0.95*"/><ColumnDefinition Width="14"/><ColumnDefinition Width="1.05*"/></Grid.ColumnDefinitions>
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions><TextBlock x:Name="DiscoverRankTitle" Text="Ranked opportunities" Style="{StaticResource SectionTitleText}"/><ListBox Grid.Row="1" x:Name="DiscoverNicheList" BorderThickness="0" Background="Transparent" Margin="0,10,0,0" MaxHeight="540" ScrollViewer.HorizontalScrollBarVisibility="Disabled"><ListBox.ItemTemplate><DataTemplate><Border Background="{StaticResource Panel2}" BorderBrush="{StaticResource Line}" BorderThickness="1" CornerRadius="9" Padding="12" Margin="0,0,0,8"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock Text="{Binding name}" FontWeight="SemiBold" FontSize="14" TextWrapping="Wrap"/><Border Grid.Column="1" Background="{StaticResource AccentSoft}" BorderBrush="{StaticResource AccentStroke}" BorderThickness="1" CornerRadius="8" Padding="7,2" Margin="10,0,0,0"><TextBlock Text="{Binding score_label}" Foreground="{StaticResource Accent}" FontWeight="Bold"/></Border></Grid><TextBlock Grid.Row="1" Text="{Binding meta_label}" Style="{StaticResource MetaText}" Margin="0,6,0,0" TextWrapping="Wrap"/></Grid></Border></DataTemplate></ListBox.ItemTemplate></ListBox></Grid></Border>
                    <StackPanel Grid.Column="2"><Border Style="{StaticResource CardSurfaceBorder}" Padding="18"><StackPanel><TextBlock x:Name="DiscoverDetailTitle" Text="Opportunity detail" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="DiscoverDetailName" Text="Select a niche" FontSize="20" FontWeight="SemiBold" Margin="0,10,0,0" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverDetailAudience" Style="{StaticResource MetaText}" Margin="0,5,0,0" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverDetailSummary" Style="{StaticResource BodyText}" Margin="0,12,0,0" TextWrapping="Wrap"/><TextBlock x:Name="DiscoverDetailDimensions" Style="{StaticResource MetaText}" Margin="0,12,0,0" TextWrapping="Wrap"/><Button x:Name="DiscoverCreateDraftButton" Content="Create concept draft" Style="{StaticResource PrimaryButton}" IsEnabled="False" HorizontalAlignment="Left" Margin="0,16,0,0" AutomationProperties.Name="Create local concept draft from this niche"/><TextBlock x:Name="DiscoverDraftStatusText" Text="" Style="{StaticResource MetaText}" Margin="0,8,0,0" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="18" Margin="0,14,0,0"><StackPanel><TextBlock x:Name="DiscoverRecentTitle" Text="Recent research" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="DiscoverRecentText" Text="—" Style="{StaticResource BodyText}" Margin="0,8,0,0" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="18" Margin="0,14,0,0"><StackPanel><TextBlock x:Name="DiscoverSourcesTitle" Text="Evidence sources" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="DiscoverSourcesText" Text="—" Style="{StaticResource BodyText}" Margin="0,8,0,0" TextWrapping="Wrap"/></StackPanel></Border></StackPanel>
                  </Grid>
                </StackPanel>
              </ScrollViewer>
              <ScrollViewer x:Name="SectionLandingScroll" Visibility="Collapsed" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><Grid Margin="26"><Border Style="{StaticResource CardSurfaceBorder}" Padding="26" MaxWidth="820" HorizontalAlignment="Left" VerticalAlignment="Top"><StackPanel><TextBlock x:Name="SectionLandingKicker" Text="PRODUCT WORKSPACE" Foreground="{StaticResource Accent}" FontSize="12" FontWeight="Bold"/><TextBlock x:Name="SectionLandingTitle" Text="Ideas" Style="{StaticResource DisplayTitleText}" Margin="0,8,0,0"/><TextBlock x:Name="SectionLandingBody" Text="Choose an idea from the list to continue." Style="{StaticResource SubtitleText}" TextWrapping="Wrap" Margin="0,10,0,0"/><TextBlock x:Name="SectionLandingHint" Text="Live product data is never fabricated when the backend is unavailable." Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,18,0,0"/></StackPanel></Border></Grid></ScrollViewer>
              <ScrollViewer x:Name="PortfolioLandingScroll" Visibility="Collapsed" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><StackPanel Margin="26"><TextBlock x:Name="PortfolioTitle" Visibility="Collapsed" Text="Portfolio" Style="{StaticResource DisplayTitleText}"/><TextBlock x:Name="PortfolioBody" Visibility="Collapsed" Text="Published products, channels and listing health." Style="{StaticResource SubtitleText}" Margin="0,7,0,18"/><UniformGrid Columns="3"><Border Style="{StaticResource KpiCard}" Margin="0,0,8,0"><StackPanel><TextBlock Text="Products" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PortfolioProductsValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock Text="Imported publication receipts" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock Text="Channels" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PortfolioChannelsValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock Text="Imported publication receipts" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="8,0,0,0"><StackPanel><TextBlock Text="Listing health" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PortfolioHealthValue" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/><TextBlock Text="Requires live or imported evidence" Style="{StaticResource MetaText}" TextWrapping="Wrap"/></StackPanel></Border></UniformGrid><Border Style="{StaticResource CardSurfaceBorder}" Padding="20" Margin="0,16,0,0"><StackPanel><TextBlock x:Name="PortfolioPipelineTitle" Text="Pipeline" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PortfolioPipelineSummary" Text="—" Style="{StaticResource MetaText}" Margin="0,6,0,0" TextWrapping="Wrap"/><UniformGrid Columns="3" Margin="0,12,0,0"><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipeUndecidedLabel" Text="No decision" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipeUndecidedValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipeKeepLabel" Text="KEEP" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipeKeepValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipeArtworkLabel" Text="Artwork accepted" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipeArtworkValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipeChecksLabel" Text="Checks passed" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipeChecksValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipePackageLabel" Text="Package ready" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipePackageValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="0,0,8,8"><StackPanel><TextBlock x:Name="PipePublishedLabel" Text="Published" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PipePublishedValue" Text="—" FontSize="26" FontWeight="Bold" Margin="0,6,0,0"/></StackPanel></Border></UniformGrid><TextBlock x:Name="PortfolioNextTitle" Text="Next actions" Style="{StaticResource SectionTitleText}" Margin="0,18,0,0"/><ListBox x:Name="PortfolioPipelineList" BorderThickness="0" Background="Transparent" Margin="0,10,0,0" MaxHeight="460" ScrollViewer.HorizontalScrollBarVisibility="Disabled" AutomationProperties.Name="Pipeline next actions"><ListBox.ItemTemplate><DataTemplate><Border Background="{StaticResource Panel2}" BorderBrush="{StaticResource Line}" BorderThickness="1" CornerRadius="9" Padding="12" Margin="0,0,0,8"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock Text="{Binding title}" FontWeight="SemiBold" FontSize="14" TextWrapping="Wrap"/><Border Grid.Column="1" Background="{StaticResource AccentSoft}" BorderBrush="{StaticResource AccentStroke}" BorderThickness="1" CornerRadius="8" Padding="7,2" Margin="10,0,0,0"><TextBlock Text="{Binding stage_label}" Foreground="{StaticResource Accent}" FontWeight="Bold"/></Border></Grid><TextBlock Grid.Row="1" Text="{Binding next_label}" Style="{StaticResource MetaText}" Margin="0,6,0,0" TextWrapping="Wrap"/></Grid></Border></DataTemplate></ListBox.ItemTemplate></ListBox><TextBlock x:Name="PortfolioNicheTitle" Text="Decisions by niche" Style="{StaticResource SectionTitleText}" Margin="0,16,0,0"/><TextBlock x:Name="PortfolioNicheText" Text="—" Style="{StaticResource BodyText}" Margin="0,8,0,0" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="22" Margin="0,16,0,0"><StackPanel><TextBlock x:Name="PortfolioEmpty" Text="Connect live commerce data to load your published products." Style="{StaticResource BodyText}" TextWrapping="Wrap"/><TextBlock Text="Local publication receipts" Style="{StaticResource SectionTitleText}" Margin="0,16,0,0"/><WrapPanel Margin="0,8,0,0"><Button x:Name="LocalImportPublicationReceiptButton" Content="Import publication receipt…" Style="{StaticResource PrimaryButton}"/><TextBlock x:Name="LocalPublicationStatusText" Text="No local publication receipt imported." Style="{StaticResource MetaText}" VerticalAlignment="Center" Margin="10,0,0,0"/></WrapPanel></StackPanel></Border></StackPanel></ScrollViewer>
              <ScrollViewer x:Name="PerformanceLandingScroll" Visibility="Collapsed" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><StackPanel Margin="26"><TextBlock x:Name="PerformanceTitle" Visibility="Collapsed" Text="Performance" Style="{StaticResource DisplayTitleText}"/><TextBlock x:Name="PerformanceBody" Visibility="Collapsed" Text="Sales, royalties and product momentum across 7 / 30 / 90 days." Style="{StaticResource SubtitleText}" Margin="0,7,0,18"/><UniformGrid Columns="4"><Border Style="{StaticResource KpiCard}" Margin="0,0,8,0"><StackPanel><TextBlock Text="Sales · 7 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PerfSales7Value" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock Text="Sales · 30 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PerfSales30Value" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="4,0"><StackPanel><TextBlock Text="Royalties · 30 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PerfRoyalties30Value" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border><Border Style="{StaticResource KpiCard}" Margin="8,0,0,0"><StackPanel><TextBlock Text="Sales · 90 days" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap"/><TextBlock x:Name="PerfSales90Value" Text="—" FontSize="30" FontWeight="Bold" Margin="0,8,0,2"/></StackPanel></Border></UniformGrid><Grid Margin="0,16,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="14"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions><Border Style="{StaticResource CardSurfaceBorder}" Padding="20"><StackPanel><TextBlock Text="Winners" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PerformanceEmpty" Text="Connect live commerce data to load sales and royalty performance." Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,8,0,0"/><TextBlock x:Name="PerformanceLeadersText" Text="—" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,10,0,0"/></StackPanel></Border><Border Grid.Column="2" Style="{StaticResource CardSurfaceBorder}" Padding="20"><StackPanel><TextBlock Text="Needs attention" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PerformanceAttentionText" Text="—" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border></Grid><Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,16,0,0"><StackPanel><TextBlock Text="Local sales import" Style="{StaticResource SectionTitleText}"/><WrapPanel Margin="0,8,0,0"><Button x:Name="LocalImportSalesButton" Content="Import sales CSV…" Style="{StaticResource PrimaryButton}"/><TextBlock x:Name="LocalSalesStatusText" Text="No local sales data imported." Style="{StaticResource MetaText}" VerticalAlignment="Center" Margin="10,0,0,0"/></WrapPanel></StackPanel></Border></StackPanel></ScrollViewer>
              <TabControl x:Name="MainTabs" Visibility="Collapsed" Margin="12" Style="{StaticResource ProductTabControl}" ItemContainerStyle="{StaticResource ConceptContentTabItem}" AutomationProperties.Name="Concept workbench content">

              <TabItem Tag="overview" Header="Overview"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><StackPanel x:Name="ConceptOverviewPanel" Margin="16">
                <Border Style="{StaticResource CardSurfaceBorder}" Padding="18" Margin="0,0,0,12">
                  <StackPanel>
                    <TextBlock Text="The idea" Style="{StaticResource SectionTitleText}"/>
                    <TextBlock x:Name="OverviewHook" Text="Select a concept to see its overview." Style="{StaticResource HeroHookText}" TextWrapping="Wrap" Margin="0,10,0,9"/>
                    <TextBlock x:Name="OverviewConcept" Style="{StaticResource BodyText}" TextWrapping="Wrap"/>
                  </StackPanel>
                </Border>
                <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12">
                  <StackPanel>
                    <TextBlock x:Name="OwnerDecisionTitle" Text="Owner decision" Style="{StaticResource SectionTitleText}"/>
                    <TextBlock x:Name="OwnerDecisionBody" Text="Choose what happens to this exact idea revision. Decisions are saved locally in Forge; they do not Generate, Accept or Publish." Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,7,0,10"/>
                    <WrapPanel>
                      <Button x:Name="OwnerKeepButton" Content="KEEP" Style="{StaticResource PrimaryButton}" Margin="0,0,8,8" ToolTip="Keep this exact revision and move it toward artwork when the next product gate is available"/>
                      <Button x:Name="OwnerEditDecisionButton" Content="EDIT" Margin="0,0,8,8" ToolTip="Route this exact revision to an edit pass"/>
                      <Button x:Name="OwnerRegenButton" Content="REGEN" Margin="0,0,8,8" ToolTip="Request a new creative direction later; this button does not generate artwork"/>
                      <Button x:Name="OwnerSkipButton" Content="SKIP" Margin="0,0,8,8" ToolTip="Park this idea"/>
                      <Button x:Name="OwnerClearDecisionButton" Content="Clear decision" Margin="0,0,8,8" ToolTip="Return this idea to undecided"/>
                    </WrapPanel>
                    <TextBlock x:Name="OwnerDecisionStatusText" Text="No decision yet" Style="{StaticResource StatusInfoText}" TextWrapping="Wrap" Margin="0,4,0,0"/>
                    <TextBlock x:Name="OwnerDecisionProgressText" Text="0 of 0 ideas decided" Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,5,0,0"/>
                  </StackPanel>
                </Border>
                <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="14"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                  <StackPanel Grid.Column="0">
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Who it is for" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewBuyer" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border>
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Why someone would want it" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewWhy" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border>
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="What makes it different" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewDifferent" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border>
                  </StackPanel>
                  <StackPanel Grid.Column="2">
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Visual direction" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewVisual" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border>
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Meaning / context" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewMeaning" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/></StackPanel></Border>
                    <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Current state" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="OverviewStatus" Style="{StaticResource StatusInfoText}" TextWrapping="Wrap" Margin="0,7,0,0"/><TextBlock x:Name="OverviewWarnings" Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,7,0,0"/><TextBlock x:Name="OverviewNext" Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,10,0,0"/></StackPanel></Border>
                  </StackPanel>
                </Grid>
                <WrapPanel Margin="0,4,0,0">
                  <Button x:Name="OverviewVisualButton" Content="Review visuals / generation" Style="{StaticResource PrimaryButton}" Margin="0,0,8,8" IsEnabled="False" ToolTip="Open visual generation and review for this concept" AutomationProperties.Name="Review visuals and generation"/>
                  <Button x:Name="OverviewEditButton" Content="Edit concept" Margin="0,0,8,8" IsEnabled="False" ToolTip="Open the optional creative editor for this concept" AutomationProperties.Name="Edit concept"/>
                </WrapPanel>
              </StackPanel></ScrollViewer></TabItem>

<TabItem Tag="visuals" Header="Visuals &amp; Generate"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><Grid Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,0,0,12"><StackPanel><TextBlock Text="Generation brief" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="GenerationBriefText" Text="Select a concept to see the prepared generation brief." Style="{StaticResource BodyText}" TextWrapping="Wrap" Margin="0,8,0,0"/><TextBlock Text="Prepared automatically from the concept. Edit only if you want to change the creative direction." Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap" Margin="0,7,0,0"/></StackPanel></Border>
                <StackPanel Grid.Row="1"><WrapPanel><Button x:Name="GenerateButton" Content="Generate variants…" Style="{StaticResource PrimaryButton}" IsEnabled="False" ToolTip="Create a generation request for the exact current revision. This is an explicit owner action." AutomationProperties.Name="Generate variants"/><Button x:Name="AcceptButton" Content="Accept selected visual" IsEnabled="False" ToolTip="Accept the exact selected visual after review. This does not publish it." AutomationProperties.Name="Accept selected visual"/><TextBlock x:Name="GenerationStatus" Style="{StaticResource StatusInfoText}" VerticalAlignment="Center" Margin="8,8,0,0"/></WrapPanel><Border Style="{StaticResource CardSurfaceBorder}" Padding="12" Margin="0,10,0,0"><StackPanel><TextBlock Text="Local-first fallback" Style="{StaticResource SubsectionTitleText}"/><WrapPanel Margin="0,8,0,0"><Button x:Name="LocalExportBriefButton" Content="Export generation brief"/><Button x:Name="LocalImportArtworkButton" Content="Import artwork…" Style="{StaticResource PrimaryButton}"/><Button x:Name="LocalAcceptButton" Content="Accept local artwork" IsEnabled="False"/></WrapPanel><TextBlock x:Name="LocalCoreStatusText" Text="Local core ready." Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,6,0,0"/></StackPanel></Border></StackPanel>
                <Grid x:Name="VariantsLayoutGrid" Grid.Row="2" Margin="0,14,0,0"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="1*"/><ColumnDefinition x:Name="VariantsGapColumn" Width="12"/><ColumnDefinition x:Name="VariantsRightColumn" Width="2*"/></Grid.ColumnDefinitions>
                  <StackPanel>
                    <TextBlock Text="Generation runs" Style="{StaticResource SubsectionTitleText}"/>
                    <ListBox x:Name="GenerationRequestList" ItemContainerStyle="{StaticResource CardListBoxItem}" DisplayMemberPath="display" Margin="0,8,0,6" MaxHeight="170" AutomationProperties.Name="Generation request history"/>
                    <Button x:Name="CancelGenerationButton" Content="Cancel selected queued request" IsEnabled="False" Margin="0,0,0,12" ToolTip="Cancel a queued generation request before provider dispatch" AutomationProperties.Name="Cancel selected generation request"/>
                    <TextBlock Text="Variants" Style="{StaticResource SubsectionTitleText}"/>
                    <ListBox x:Name="VariantList" ItemContainerStyle="{StaticResource CardListBoxItem}" DisplayMemberPath="display" SelectionMode="Extended" Margin="0,8,0,6" AutomationProperties.Name="Generated variants"/><Button x:Name="CompareVariantsButton" Content="Compare two selected variants" IsEnabled="False" ToolTip="Compare two selected visual variants side by side" AutomationProperties.Name="Compare selected variants"/>
                  </StackPanel>
                  <StackPanel x:Name="VariantsRightPane" Grid.Column="2">
                    <TextBlock Text="Variant" Style="{StaticResource SubsectionTitleText}"/><TextBox x:Name="VariantPreview" Margin="0,8,0,6" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="90" VerticalScrollBarVisibility="Auto"/><Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False" Margin="0,0,0,10"><TextBox x:Name="VariantAdvanced" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11" MinHeight="100"/></Expander>
                    <TextBlock Text="Visual preview" Style="{StaticResource SectionTitleText}"/>
                    <TextBlock Text="Artwork is fitted to the frame so the full design remains visible." Style="{StaticResource MutedCaptionText}" Margin="0,4,0,0"/>
                    <Grid x:Name="VariantMediaGrid" Margin="0,10,0,14">
                      <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                      <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition x:Name="VariantMediaGapColumn" Width="12"/><ColumnDefinition x:Name="VariantMediaRightColumn" Width="*"/></Grid.ColumnDefinitions>
                      <StackPanel>
                        <TextBlock Text="Primary selection" Style="{StaticResource MediaFrameLabel}" Margin="2,0,0,6"/>
                        <Border Style="{StaticResource MediaFrameBorder}" MinHeight="270">
                          <Grid Background="{StaticResource MediaSurfaceInner}" ClipToBounds="True">
                            <Image x:Name="VariantImageA" Style="{StaticResource MediaPreviewImage}" Margin="6"/>
                            <TextBlock x:Name="VariantImageStatusA" Text="Select a variant" Style="{StaticResource MediaPlaceholderText}"/>
                          </Grid>
                        </Border>
                      </StackPanel>
                      <StackPanel x:Name="VariantMediaRightPane" Grid.Column="2">
                        <TextBlock Text="Comparison selection" Style="{StaticResource MediaFrameLabel}" Margin="2,0,0,6"/>
                        <Border Style="{StaticResource MediaFrameBorder}" MinHeight="270">
                          <Grid Background="{StaticResource MediaSurfaceInner}" ClipToBounds="True">
                            <Image x:Name="VariantImageB" Style="{StaticResource MediaPreviewImage}" Margin="6"/>
                            <TextBlock x:Name="VariantImageStatusB" Text="Select a second variant to compare" Style="{StaticResource MediaPlaceholderText}"/>
                          </Grid>
                        </Border>
                      </StackPanel>
                    </Grid>
                    <TextBlock Text="Compare" Style="{StaticResource SubsectionTitleText}"/>
                    <Grid x:Name="VariantCompareGrid" Margin="0,8,0,10"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="10"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                      <TextBox x:Name="VariantCompareA" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="125" VerticalScrollBarVisibility="Auto"/>
                      <TextBox Grid.Column="2" x:Name="VariantCompareB" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="125" VerticalScrollBarVisibility="Auto"/>
                    </Grid>
                    <TextBlock Text="Review note (does not Accept)" Style="{StaticResource SubsectionTitleText}"/>
                    <Grid x:Name="VariantReviewGrid" Margin="0,8,0,8"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="135"/><ColumnDefinition Width="8"/><ColumnDefinition Width="210"/><ColumnDefinition Width="8"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                      <ComboBox x:Name="VariantReviewState" SelectedIndex="0" AutomationProperties.Name="Variant review state"><ComboBoxItem Content="neutral"/><ComboBoxItem Content="favorite"/><ComboBoxItem Content="reject"/></ComboBox>
                      <ComboBox Grid.Column="2" x:Name="VariantReviewReason" AutomationProperties.Name="Structured review reason" ToolTip="Reject requires a structured reason. Favorite/neutral reason is optional."/>
                      <TextBox Grid.Column="4" x:Name="VariantReviewNote" ToolTip="Optional review note" AutomationProperties.Name="Variant review note"/>
                    </Grid>
                    <Button x:Name="SaveVariantReviewButton" Content="Save review event" IsEnabled="False" ToolTip="Save this review decision as a new immutable review event" AutomationProperties.Name="Save variant review"/>
                    <TextBlock Text="Acceptance" Style="{StaticResource SubsectionTitleText}" Margin="0,16,0,0"/>
                    <TextBlock x:Name="AcceptanceStatus" Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,6,0,6"/>
                    <TextBox x:Name="ReopenReasonBox" ToolTip="Required reason when reopening an accepted revision" Margin="0,0,0,6" AutomationProperties.Name="Reason to reopen acceptance"/>
                    <WrapPanel>
                      <Button x:Name="ReopenAcceptanceButton" Content="Reopen current acceptance" IsEnabled="False" ToolTip="Revoke the current acceptance and return this concept to review" AutomationProperties.Name="Reopen current acceptance"/>
                      <Button x:Name="StartIterationSameButton" Content="Start new iteration · same brief" IsEnabled="False" ToolTip="Create a new revision using the same brief; generation remains separate" AutomationProperties.Name="Start new iteration with same brief"/>
                      <Button x:Name="StartIterationEditButton" Content="Start new iteration · edited brief" IsEnabled="False" ToolTip="Create a new editable revision; generation remains separate" AutomationProperties.Name="Start new iteration with edited brief"/>
                    </WrapPanel>
                    <TextBlock Text="Large image files stay local to this computer. Preview access is handled safely without showing file-system locations." Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap" Margin="0,14,0,0"/>
                  </StackPanel>
                </Grid>
              </Grid></ScrollViewer></TabItem>

<TabItem Tag="history" Header="History"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><Grid x:Name="HistoryLayoutGrid" Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="1*"/><ColumnDefinition x:Name="HistoryGapColumn" Width="12"/><ColumnDefinition x:Name="HistoryRightColumn" Width="2*"/></Grid.ColumnDefinitions>
                <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="2*"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="3*"/></Grid.RowDefinitions>
                  <TextBlock Text="Revisions" Style="{StaticResource SectionTitleText}"/>
                  <ListBox Grid.Row="1" x:Name="RevisionList" ItemContainerStyle="{StaticResource CardListBoxItem}" Margin="0,8,0,12" DisplayMemberPath="display" AutomationProperties.Name="Creative revision history"/>
                  <Button Grid.Row="2" x:Name="RestoreRevisionButton" Content="Restore selected as new revision" IsEnabled="False" ToolTip="Copy the selected historical revision into a new current revision; history is preserved" AutomationProperties.Name="Restore selected revision as new revision"/>
                  <TextBlock Grid.Row="3" Text="Activity" Style="{StaticResource SectionTitleText}" Margin="0,14,0,0"/>
                  <ListBox Grid.Row="4" x:Name="AuditList" ItemContainerStyle="{StaticResource CardListBoxItem}" Margin="0,8,0,0" DisplayMemberPath="display" ToolTip="Human-readable actor/action/version timeline; technical events hidden by default" AutomationProperties.Name="Activity history"/>
                </Grid>
                <Grid x:Name="HistoryRightPane" Grid.Column="2"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition x:Name="HistoryDetailGapColumn" Width="12"/><ColumnDefinition x:Name="HistoryDetailRightColumn" Width="*"/></Grid.ColumnDefinitions>
                  <StackPanel><TextBlock Text="Current" Style="{StaticResource SubsectionTitleText}"/><TextBox x:Name="CurrentRevisionPreview" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto"/></StackPanel>
                  <StackPanel x:Name="HistoryDetailRightPane" Grid.Column="2"><TextBlock Text="Selected revision" Style="{StaticResource SubsectionTitleText}"/><TextBox x:Name="SelectedRevisionPreview" Margin="0,8,0,8" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto"/><Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False" Margin="0,0,0,12"><TextBox x:Name="RevisionAdvanced" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11"/></Expander><TextBlock Text="Selected activity evidence" Style="{StaticResource SubsectionTitleText}"/><TextBox x:Name="AuditDetail" Margin="0,8,0,8" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="110" VerticalScrollBarVisibility="Auto"/><Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False"><TextBox x:Name="AuditAdvanced" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11" MinHeight="100"/></Expander></StackPanel>
                </Grid>
              </Grid></ScrollViewer></TabItem>

<TabItem Tag="evidence" Header="Evidence"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><StackPanel Margin="16">
                <TextBlock Text="Why this concept exists" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="AnalysisPurchase" TextWrapping="Wrap" Margin="0,8,0,14"/>
                <TextBlock Text="Insider / profession context" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="AnalysisContext" TextWrapping="Wrap" Margin="0,8,0,14"/>
                <TextBlock Text="Meaning / joke" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="AnalysisMeaning" TextWrapping="Wrap" Margin="0,8,0,14"/>
                <TextBlock Text="Evidence &amp; IP readiness" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="AnalysisEvidence" TextWrapping="Wrap" Margin="0,8,0,14"/>
                <TextBlock Text="Score dimensions" Style="{StaticResource SectionTitleText}"/><TextBox x:Name="AnalysisScores" Margin="0,8,0,12" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" BorderThickness="0" Background="Transparent"/>
                <Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False" Margin="0,0,0,14"><TextBox x:Name="AnalysisAdvanced" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11" MinHeight="100"/></Expander>
                <TextBlock Text="Warnings / blockers" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="AnalysisWarnings" TextWrapping="Wrap" Margin="0,8,0,14"/><Border Style="{StaticResource CardSurfaceBorder}" Padding="12" Margin="0,4,0,10"><StackPanel><TextBlock Text="Amazon print profile" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="AmazonProfileStatusText" Text="—" TextWrapping="Wrap" Margin="0,6,0,0"/><WrapPanel Margin="0,8,0,0"><Button x:Name="AmazonProfileFormButton" Content="Fill Amazon profile…" Margin="0,0,8,6"/><Button x:Name="AmazonProfileImportButton" Content="Import profile file…" Margin="0,0,0,6"/></WrapPanel></StackPanel></Border><Border Style="{StaticResource CardSurfaceBorder}" Padding="12" Margin="0,4,0,0"><StackPanel><TextBlock Text="Local check evidence" Style="{StaticResource SubsectionTitleText}"/><WrapPanel Margin="0,8,0,0"><Button x:Name="LocalConfirmChecksButton" Content="Confirm checks…" Margin="0,0,8,6"/><Button x:Name="LocalImportCheckEvidenceButton" Content="Import check evidence…" Margin="0,0,8,6"/><Button x:Name="LocalOpenChecksFolderButton" Content="Open checks folder" Margin="0,0,0,6"/></WrapPanel><TextBlock x:Name="LocalCheckStatusText" Text="No local check evidence imported." Style="{StaticResource MetaText}" TextWrapping="Wrap" Margin="0,6,0,0"/></StackPanel></Border>
              </StackPanel></ScrollViewer></TabItem>

<TabItem Tag="delivery" Header="Delivery"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><StackPanel Margin="16">
                <TextBlock Text="Exact accepted lineage" Style="{StaticResource SectionTitleText}"/>
                <TextBlock x:Name="DownstreamLineage" TextWrapping="Wrap" Margin="0,8,0,16"/>
                <TextBlock Text="Version-specific gates" Style="{StaticResource SectionTitleText}"/>
                <TextBlock x:Name="DownstreamIp" TextWrapping="Wrap" Margin="0,8,0,6"/>
                <TextBlock x:Name="DownstreamVisualQa" TextWrapping="Wrap" Margin="0,0,0,6"/>
                <TextBlock x:Name="DownstreamPrintQa" TextWrapping="Wrap" Margin="0,0,0,6"/>
                <TextBlock x:Name="DownstreamPolicy" TextWrapping="Wrap" Margin="0,0,0,16"/>
                <TextBlock Text="Readiness" Style="{StaticResource SectionTitleText}"/>
                <TextBlock x:Name="DownstreamEligibility" TextWrapping="Wrap" Margin="0,8,0,8"/>
                <TextBlock x:Name="DownstreamBlocker" TextWrapping="Wrap" Style="{StaticResource StatusWarningText}" Margin="0,0,0,16"/><Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False" Margin="0,0,0,16"><TextBox x:Name="DownstreamAdvanced" Margin="0,8,0,0" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11" MinHeight="90"/></Expander>
                <Border Style="{StaticResource CardSurfaceBorder}" Padding="14">
                  <StackPanel><TextBlock Text="External action boundary" Style="{StaticResource SubsectionTitleText}"/><TextBlock x:Name="DownstreamExternal" TextWrapping="Wrap" Margin="0,5,0,0"/></StackPanel>
                </Border>
              </StackPanel></ScrollViewer></TabItem>

<TabItem Tag="publication" Header="Publication"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><Grid x:Name="PublicationLayoutGrid" Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition x:Name="PublicationGapColumn" Width="18"/><ColumnDefinition x:Name="PublicationRightColumn" Width="*"/></Grid.ColumnDefinitions>
                <StackPanel Grid.Column="0">
                  <TextBlock Text="Design" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PublicationCreativeStatus" TextWrapping="Wrap" Margin="0,8,0,16"/>
                  <TextBlock Text="Listing draft" Style="{StaticResource SectionTitleText}" Margin="0,0,0,4"/>
                  <TextBlock x:Name="PublicationDraftNote" Text="Forge prepares this from the concept automatically. Manual edits are optional." Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap" Margin="0,0,0,12"/>
                  <TextBlock Text="Listing title" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationTitleBox" Margin="0,6,0,12" AutomationProperties.Name="Listing title"/>
                  <TextBlock Text="Brand" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationBrandBox" Margin="0,6,0,4" AutomationProperties.Name="Listing brand"/><TextBlock x:Name="PublicationBrandHint" Text="" Style="{StaticResource MutedCaptionText}" TextWrapping="Wrap" Margin="0,0,0,12"/>
                  <TextBlock Text="Bullet 1" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationBullet1Box" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="55" AutomationProperties.Name="Listing bullet one"/>
                  <TextBlock Text="Bullet 2" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationBullet2Box" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="55" AutomationProperties.Name="Listing bullet two"/>
                  <TextBlock Text="Description" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationDescriptionBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="90" AutomationProperties.Name="Listing description"/>
                  <TextBlock Text="Keywords" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationKeywordsBox" ToolTip="Separate keywords with commas or semicolons" Margin="0,6,0,12" AutomationProperties.Name="Listing keywords"/>
                  <TextBlock x:Name="PublicationLocaleLabel" Text="Listing locale" Style="{StaticResource FieldLabelText}"/><ComboBox x:Name="PublicationLocaleBox" Margin="0,6,0,12" Width="220" HorizontalAlignment="Left" AutomationProperties.Name="Listing locale"><ComboBoxItem Content="English (United States)" Tag="en-US" IsSelected="True"/><ComboBoxItem Content="Russian (Russia)" Tag="ru-RU"/><ComboBoxItem Content="Spanish (Spain)" Tag="es-ES"/></ComboBox>
                  <TextBlock Text="Why changed? (optional)" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PublicationReasonBox" Margin="0,6,0,12" AutomationProperties.Name="Reason for listing revision"/>
                  <TextBlock x:Name="PublicationListingHints" Visibility="Collapsed" Style="{StaticResource StatusWarningText}" TextWrapping="Wrap" Margin="0,0,0,12"/>
                  <DockPanel><TextBlock x:Name="PublicationDirtyLabel" Style="{StaticResource StatusWarningText}" VerticalAlignment="Center"/><Button x:Name="SavePublicationButton" Content="Save listing version" Style="{StaticResource PrimaryButton}" DockPanel.Dock="Right" IsEnabled="False" ToolTip="Save listing metadata as a new immutable version; this does not publish" AutomationProperties.Name="Save listing version"/></DockPanel>
                  <TextBlock Text="Listing versions" Style="{StaticResource SectionTitleText}" Margin="0,16,0,0"/><TextBlock x:Name="PublicationHistoryEmpty" Text="No listing versions yet." Style="{StaticResource EmptyStateInlineText}" Margin="0,8,0,0"/><ListBox x:Name="PublicationHistoryList" ItemContainerStyle="{StaticResource CardListBoxItem}" DisplayMemberPath="display" Margin="0,8,0,0" MaxHeight="180" IsHitTestVisible="False" Focusable="False" AutomationProperties.Name="Listing version history"/>
                </StackPanel>
                <StackPanel x:Name="PublicationRightPane" Grid.Column="2">
                  <TextBlock Text="Checks" Style="{StaticResource SectionTitleText}"/>
                  <TextBlock x:Name="PublicationCheckIp" TextWrapping="Wrap" Margin="0,8,0,5"/>
                  <TextBlock x:Name="PublicationCheckVisual" TextWrapping="Wrap" Margin="0,0,0,5"/>
                  <TextBlock x:Name="PublicationCheckPrint" TextWrapping="Wrap" Margin="0,0,0,5"/>
                  <TextBlock x:Name="PublicationCheckPolicy" TextWrapping="Wrap" Margin="0,0,0,16"/>
                  <TextBlock Text="Economics" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PublicationEconomics" TextWrapping="Wrap" Margin="0,8,0,16"/>
                  <TextBlock Text="Preflight" Style="{StaticResource SectionTitleText}"/><TextBlock x:Name="PublicationPreflight" TextWrapping="Wrap" Margin="0,8,0,12"/>
                  <TextBlock Text="Packages" Style="{StaticResource SectionTitleText}" Margin="0,4,0,0"/>
                  <TextBlock x:Name="DeliveryStatus" TextWrapping="Wrap" Margin="0,8,0,8"/>
                  <WrapPanel Margin="0,2,0,8">
                    <Button x:Name="ExportPackageButton" Content="Export package" Margin="0,0,8,8" IsEnabled="False" AutomationProperties.Name="Export package" ToolTip="Prepare exact delivery manifest. Local ZIP is a separate verified step."/>
                    <Button x:Name="SendToSocialButton" Content="Send to Social" Margin="0,0,8,8" IsEnabled="False" AutomationProperties.Name="Send to Social" ToolTip="Prepare minimized outbound Social source envelope. This does not approve or publish anything."/>
                  </WrapPanel>
                  <WrapPanel Margin="0,0,0,8">
                    <ComboBox x:Name="PackageTargetBox" Width="170" Margin="0,0,8,8" AutomationProperties.Name="Package target">
                      <ComboBoxItem Content="Owner export" Tag="generic_owner_export" IsSelected="True"/>
                      <ComboBoxItem Content="Social source" Tag="social_source_package"/>
                      <ComboBoxItem Content="Amazon owner" Tag="amazon_owner_package"/>
                    </ComboBox>
                    <Button x:Name="PreparePackageButton" Content="Prepare package" Style="{StaticResource PrimaryButton}" IsEnabled="False" Margin="0,0,8,8" ToolTip="Prepare an owner package only. This does not submit or publish anything." AutomationProperties.Name="Prepare package"/><Button x:Name="LocalBuildPackageButton" Content="Build local Amazon package" IsEnabled="False" Margin="0,0,8,8" ToolTip="Create a local ZIP for manual upload. Merch Forge does not submit it."/>
                  </WrapPanel>
                  <TextBlock x:Name="PackageBoundaryText" Text="Preparation only. Export does not mean saved locally; Social handoff does not mean approval; package preparation does not submit or publish." TextWrapping="Wrap" Style="{StaticResource MetaText}" Margin="0,2,0,14"/>
                  <Border Style="{StaticResource CardSurfaceBorder}" Padding="14"><StackPanel><TextBlock Text="Submit" Style="{StaticResource SubsectionTitleText}"/><TextBlock Text="Locked external action" Style="{StaticResource StatusWarningText}" Margin="0,5,0,0"/><TextBlock x:Name="PublicationExternal" TextWrapping="Wrap" Margin="0,5,0,0"/></StackPanel></Border>
                  <Expander Foreground="{StaticResource Secondary}" Header="Technical details" IsExpanded="False" Margin="0,16,0,0"><Border Style="{StaticResource CardSurfaceBorder}" Padding="11" Margin="0,8,0,0"><TextBlock x:Name="PublicationAdvanced" FontFamily="Consolas" FontSize="11" TextWrapping="Wrap"/></Border></Expander>
                </StackPanel>
              </Grid></ScrollViewer></TabItem>

<TabItem Tag="edit" Header="Edit"><ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><Grid x:Name="EditLayoutGrid" Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition x:Name="EditGapColumn" Width="18"/><ColumnDefinition x:Name="EditRightColumn" Width="*"/></Grid.ColumnDefinitions>
                <StackPanel Grid.Column="0">
                  <TextBlock Text="Title" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="TitleBox" Margin="0,6,0,12" AutomationProperties.Name="Design title"/>
                  <TextBlock Text="Hook / slogan" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="HookBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="64" AutomationProperties.Name="Hook or slogan"/>
                  <TextBlock Text="Concept" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="ConceptTextBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="90" AutomationProperties.Name="Concept description"/>
                  <TextBlock Text="Target buyer" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="BuyerBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" AutomationProperties.Name="Target buyer"/>
                  <TextBlock Text="Purchase reason" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="PurchaseBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="70" AutomationProperties.Name="Purchase reason"/>
                </StackPanel>
                <StackPanel x:Name="EditRightPane" Grid.Column="2">
                  <TextBlock Text="Differentiation" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="DifferentiationBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="80" AutomationProperties.Name="Differentiation"/>
                  <TextBlock Text="Visual direction" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="VisualBox" Margin="0,6,0,12" AcceptsReturn="True" TextWrapping="Wrap" MinHeight="100" AutomationProperties.Name="Visual direction"/>
                  <Expander Foreground="{StaticResource Secondary}" Header="Technical details · production spec JSON" IsExpanded="False" Margin="0,0,0,12"><TextBox x:Name="SpecBox" Margin="0,8,0,0" AcceptsReturn="True" AcceptsTab="True" TextWrapping="NoWrap" FontFamily="Consolas" FontSize="12" MinHeight="190" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto" AutomationProperties.Name="Advanced production specification JSON"/></Expander>
                  <TextBlock Text="Edit reason (optional)" Style="{StaticResource FieldLabelText}"/><TextBox x:Name="ReasonBox" Margin="0,6,0,12" AutomationProperties.Name="Reason for creative revision"/>
                </StackPanel>
              </Grid></ScrollViewer></TabItem>
            </TabControl>
            </Grid>
          </Grid>
        </Border>
      </Grid>
      <Border Grid.Row="3" Style="{StaticResource ChromeStatusBorder}" Padding="16,7"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock x:Name="StatusText" Text="Disconnected" Style="{StaticResource StatusInfoText}" TextTrimming="CharacterEllipsis"/><TextBlock Grid.Column="1" x:Name="BackendText" Text="Not connected" Style="{StaticResource MutedCaptionText}" TextTrimming="CharacterEllipsis" HorizontalAlignment="Right" Margin="12,0,0,0"/></Grid></Border>


      <Grid x:Name="UtilityOverlay" Grid.RowSpan="3" Visibility="Collapsed" Background="#B8000000" Panel.ZIndex="300">
        <Border Width="760" MaxHeight="680" Margin="28" Padding="24" HorizontalAlignment="Center" VerticalAlignment="Center" Background="{StaticResource PanelElevated}" BorderBrush="{StaticResource LineStrong}" BorderThickness="1" CornerRadius="14" Effect="{StaticResource SurfaceShadow}">
          <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
            <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
              <StackPanel><TextBlock x:Name="UtilityKicker" Text="MERCH FORGE" Style="{StaticResource MetaText}"/><TextBlock x:Name="UtilityTitle" Text="About Merch Forge" Style="{StaticResource DisplayTitleText}" Margin="0,4,0,0"/></StackPanel>
              <Button x:Name="UtilityCloseTopButton" Grid.Column="1" Content="Close" ToolTip="Close this panel" AutomationProperties.Name="Close information panel" VerticalAlignment="Top" MinWidth="76"/>
            </Grid>
            <ScrollViewer Grid.Row="1" Margin="0,18,0,16" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
              <StackPanel>
                <TextBlock x:Name="UtilitySummaryText" Style="{StaticResource SubtitleText}" TextWrapping="Wrap"/>
                <Border Style="{StaticResource CardSurfaceBorder}" Padding="16" Margin="0,16,0,0"><TextBlock x:Name="UtilityBodyText" Style="{StaticResource BodyText}" TextWrapping="Wrap" LineHeight="22"/></Border>
                <Expander Foreground="{StaticResource Secondary}" x:Name="UtilityTechnicalExpander" Header="Technical details" IsExpanded="False" Margin="0,16,0,0">
                  <Border Style="{StaticResource CardSurfaceBorder}" Padding="12" Margin="0,8,0,0"><TextBox x:Name="UtilityTechnicalText" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" FontFamily="Consolas" FontSize="11.5" MinHeight="130" MaxHeight="250" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"/></Border>
                </Expander>
              </StackPanel>
            </ScrollViewer>
            <WrapPanel Grid.Row="2" HorizontalAlignment="Right">
              <Button x:Name="UtilityCopyButton" Content="Copy diagnostics" Margin="0,0,8,0" ToolTip="Copy the current diagnostics text to the clipboard" AutomationProperties.Name="Copy diagnostics"/>
              <Button x:Name="UtilityOpenLogButton" Content="Open log" Margin="0,0,8,0" ToolTip="Open the local runtime log in Notepad" AutomationProperties.Name="Open runtime log"/>
              <Button x:Name="UtilityCloseButton" Content="Done" Style="{StaticResource PrimaryButton}" ToolTip="Close this panel" AutomationProperties.Name="Close information panel"/>
            </WrapPanel>
          </Grid>
        </Border>
      </Grid>
    </Grid>
  </Grid>
</Window>
'@

$reader=New-Object System.Xml.XmlNodeReader $xaml
$Window=[Windows.Markup.XamlReader]::Load($reader)
Register-ResearchDraftUiText
Register-PipelineUiText
Register-CheckAttestationUiText
Register-AmazonProfileUiText
Register-DataBackupUiText
Register-ListingHintsUiText
function X([string]$Name){return $Window.FindName($Name)}
$LoginGrid=X 'LoginGrid'; $AppGrid=X 'AppGrid'; $OwnerKeyBox=X 'OwnerKeyBox'; $RememberBox=X 'RememberBox'; $LoginLanguageLabel=X 'LoginLanguageLabel'; $LoginLanguageBox=X 'LoginLanguageBox'; $LoginLanguageStatusText=X 'LoginLanguageStatusText'; $LoginLangEn=X 'LoginLangEn'; $LoginLangRu=X 'LoginLangRu'; $LoginLangEs=X 'LoginLangEs'; $ConnectButton=X 'ConnectButton'; $ActorText=X 'ActorText'; $HeaderIdentity=X 'HeaderIdentity'; $CompactConceptBox=X 'CompactConceptBox'; $WorkAreaGrid=X 'WorkAreaGrid'; $QueueColumn=X 'QueueColumn'; $QueueGapColumn=X 'QueueGapColumn'; $ConceptPane=X 'ConceptPane';
$AboutButton=X 'AboutButton'; $DiagnosticsButton=X 'DiagnosticsButton'; $RefreshButton=X 'RefreshButton'; $ForgetButton=X 'ForgetButton'; $BackendBanner=X 'BackendBanner'; $BackendBannerText=X 'BackendBannerText'; $BackendRetryButton=X 'BackendRetryButton'; $LanguageLabel=X 'LanguageLabel'; $LanguageBox=X 'LanguageBox'; $LanguageStatusText=X 'LanguageStatusText'; $HeaderLanguageSegment=X 'HeaderLanguageSegment'; $HeaderLangEn=X 'HeaderLangEn'; $HeaderLangRu=X 'HeaderLangRu'; $HeaderLangEs=X 'HeaderLangEs'; $SavedAccessText=X 'SavedAccessText'; $ConceptsLabel=X 'ConceptsLabel'; $SearchLabel=X 'SearchLabel'; $StatusLabel=X 'StatusLabel'; $SortLabel=X 'SortLabel'; $UtilityOverlay=X 'UtilityOverlay'; $UtilityKicker=X 'UtilityKicker'; $UtilityTitle=X 'UtilityTitle'; $UtilitySummaryText=X 'UtilitySummaryText'; $UtilityBodyText=X 'UtilityBodyText'; $UtilityTechnicalExpander=X 'UtilityTechnicalExpander'; $UtilityTechnicalText=X 'UtilityTechnicalText'; $UtilityCopyButton=X 'UtilityCopyButton'; $UtilityOpenLogButton=X 'UtilityOpenLogButton'; $UtilityCloseButton=X 'UtilityCloseButton'; $UtilityCloseTopButton=X 'UtilityCloseTopButton'; $SearchBox=X 'SearchBox'; $SearchPlaceholder=X 'SearchPlaceholder'; $QueueCountText=X 'QueueCountText'; $FilterBox=X 'FilterBox'; $SortBox=X 'SortBox'; $ConceptList=X 'ConceptList'; $ConceptTitle=X 'ConceptTitle'; $ConceptMeta=X 'ConceptMeta'; $DirtyLabel=X 'DirtyLabel'; $SaveButton=X 'SaveButton';
$QueueEmptyPanel=X 'QueueEmptyPanel'; $QueueEmptyTitle=X 'QueueEmptyTitle'; $QueueEmptyBody=X 'QueueEmptyBody'; $BusyBanner=X 'BusyBanner'; $BusyText=X 'BusyText'; $EditLayoutGrid=X 'EditLayoutGrid'; $EditGapColumn=X 'EditGapColumn'; $EditRightColumn=X 'EditRightColumn'; $EditRightPane=X 'EditRightPane'; $HistoryLayoutGrid=X 'HistoryLayoutGrid'; $HistoryGapColumn=X 'HistoryGapColumn'; $HistoryRightColumn=X 'HistoryRightColumn'; $HistoryRightPane=X 'HistoryRightPane'; $HistoryDetailGapColumn=X 'HistoryDetailGapColumn'; $HistoryDetailRightColumn=X 'HistoryDetailRightColumn'; $HistoryDetailRightPane=X 'HistoryDetailRightPane'; $VariantsLayoutGrid=X 'VariantsLayoutGrid'; $VariantsGapColumn=X 'VariantsGapColumn'; $VariantsRightColumn=X 'VariantsRightColumn'; $VariantsRightPane=X 'VariantsRightPane'; $VariantMediaGrid=X 'VariantMediaGrid'; $VariantMediaGapColumn=X 'VariantMediaGapColumn'; $VariantMediaRightColumn=X 'VariantMediaRightColumn'; $VariantMediaRightPane=X 'VariantMediaRightPane'; $VariantCompareGrid=X 'VariantCompareGrid'; $VariantReviewGrid=X 'VariantReviewGrid'; $PublicationLayoutGrid=X 'PublicationLayoutGrid'; $PublicationGapColumn=X 'PublicationGapColumn'; $PublicationRightColumn=X 'PublicationRightColumn'; $PublicationRightPane=X 'PublicationRightPane';
$TitleBox=X 'TitleBox'; $HookBox=X 'HookBox'; $ConceptTextBox=X 'ConceptTextBox'; $BuyerBox=X 'BuyerBox'; $PurchaseBox=X 'PurchaseBox'; $DifferentiationBox=X 'DifferentiationBox'; $VisualBox=X 'VisualBox'; $SpecBox=X 'SpecBox'; $ReasonBox=X 'ReasonBox';
$AnalysisPurchase=X 'AnalysisPurchase'; $AnalysisContext=X 'AnalysisContext'; $AnalysisMeaning=X 'AnalysisMeaning'; $AnalysisEvidence=X 'AnalysisEvidence'; $AnalysisScores=X 'AnalysisScores'; $AnalysisAdvanced=X 'AnalysisAdvanced'; $AnalysisWarnings=X 'AnalysisWarnings';
$RevisionList=X 'RevisionList'; $RestoreRevisionButton=X 'RestoreRevisionButton'; $CurrentRevisionPreview=X 'CurrentRevisionPreview'; $SelectedRevisionPreview=X 'SelectedRevisionPreview'; $RevisionAdvanced=X 'RevisionAdvanced'; $AuditList=X 'AuditList'; $AuditDetail=X 'AuditDetail'; $AuditAdvanced=X 'AuditAdvanced';
$GenerationBriefText=X 'GenerationBriefText'; $GenerateButton=X 'GenerateButton'; $AcceptButton=X 'AcceptButton'; $GenerationStatus=X 'GenerationStatus'; $GenerationRequestList=X 'GenerationRequestList'; $CancelGenerationButton=X 'CancelGenerationButton'; $VariantList=X 'VariantList'; $CompareVariantsButton=X 'CompareVariantsButton'; $VariantPreview=X 'VariantPreview'; $VariantAdvanced=X 'VariantAdvanced'; $VariantCompareA=X 'VariantCompareA'; $VariantCompareB=X 'VariantCompareB'; $VariantImageA=X 'VariantImageA'; $VariantImageB=X 'VariantImageB'; $VariantImageStatusA=X 'VariantImageStatusA'; $VariantImageStatusB=X 'VariantImageStatusB'; $VariantReviewState=X 'VariantReviewState'; $VariantReviewReason=X 'VariantReviewReason'; $VariantReviewNote=X 'VariantReviewNote'; $SaveVariantReviewButton=X 'SaveVariantReviewButton'; $AcceptanceStatus=X 'AcceptanceStatus'; $ReopenReasonBox=X 'ReopenReasonBox'; $ReopenAcceptanceButton=X 'ReopenAcceptanceButton'; $StartIterationSameButton=X 'StartIterationSameButton'; $StartIterationEditButton=X 'StartIterationEditButton'; $StatusText=X 'StatusText'; $BackendText=X 'BackendText';
$OwnerDecisionTitle=X 'OwnerDecisionTitle'; $OwnerDecisionBody=X 'OwnerDecisionBody'; $OwnerKeepButton=X 'OwnerKeepButton'; $OwnerEditDecisionButton=X 'OwnerEditDecisionButton'; $OwnerRegenButton=X 'OwnerRegenButton'; $OwnerSkipButton=X 'OwnerSkipButton'; $OwnerClearDecisionButton=X 'OwnerClearDecisionButton'; $OwnerDecisionStatusText=X 'OwnerDecisionStatusText'; $OwnerDecisionProgressText=X 'OwnerDecisionProgressText';
$HomeButton=X 'HomeButton'; $ProductNav=X 'ProductNav'; $NavHomeButton=X 'NavHomeButton'; $NavDiscoverButton=X 'NavDiscoverButton'; $NavIdeasButton=X 'NavIdeasButton'; $NavArtworkButton=X 'NavArtworkButton'; $NavChecksButton=X 'NavChecksButton'; $NavPublishButton=X 'NavPublishButton'; $NavPortfolioButton=X 'NavPortfolioButton'; $NavPerformanceButton=X 'NavPerformanceButton'; $ProductNavHint=X 'ProductNavHint'; $ContextNav=X 'ContextNav'; $ContextHistoryButton=X 'ContextHistoryButton'; $ContextDeliveryButton=X 'ContextDeliveryButton'; $ContextEditButton=X 'ContextEditButton'; $DiscoverLandingScroll=X 'DiscoverLandingScroll'; $DiscoverTitle=X 'DiscoverTitle'; $DiscoverBody=X 'DiscoverBody'; $DiscoverStatusText=X 'DiscoverStatusText'; $DiscoverRefreshButton=X 'DiscoverRefreshButton'; $DiscoverNichesLabel=X 'DiscoverNichesLabel'; $DiscoverNotesLabel=X 'DiscoverNotesLabel'; $DiscoverSourcesLabel=X 'DiscoverSourcesLabel'; $DiscoverConceptsLabel=X 'DiscoverConceptsLabel'; $DiscoverNichesValue=X 'DiscoverNichesValue'; $DiscoverNotesValue=X 'DiscoverNotesValue'; $DiscoverSourcesValue=X 'DiscoverSourcesValue'; $DiscoverConceptsValue=X 'DiscoverConceptsValue'; $DiscoverRankTitle=X 'DiscoverRankTitle'; $DiscoverNicheList=X 'DiscoverNicheList'; $DiscoverDetailTitle=X 'DiscoverDetailTitle'; $DiscoverDetailName=X 'DiscoverDetailName'; $DiscoverDetailAudience=X 'DiscoverDetailAudience'; $DiscoverDetailSummary=X 'DiscoverDetailSummary'; $DiscoverDetailDimensions=X 'DiscoverDetailDimensions'; $DiscoverRecentTitle=X 'DiscoverRecentTitle'; $DiscoverRecentText=X 'DiscoverRecentText'; $DiscoverSourcesTitle=X 'DiscoverSourcesTitle'; $DiscoverSourcesText=X 'DiscoverSourcesText'; $SectionLandingScroll=X 'SectionLandingScroll'; $SectionLandingKicker=X 'SectionLandingKicker'; $SectionLandingTitle=X 'SectionLandingTitle'; $SectionLandingBody=X 'SectionLandingBody'; $SectionLandingHint=X 'SectionLandingHint'; $PortfolioLandingScroll=X 'PortfolioLandingScroll'; $PortfolioTitle=X 'PortfolioTitle'; $PortfolioBody=X 'PortfolioBody'; $PortfolioEmpty=X 'PortfolioEmpty'; $PortfolioProductsValue=X 'PortfolioProductsValue'; $PortfolioChannelsValue=X 'PortfolioChannelsValue'; $PortfolioHealthValue=X 'PortfolioHealthValue'; $LocalImportPublicationReceiptButton=X 'LocalImportPublicationReceiptButton'; $LocalPublicationStatusText=X 'LocalPublicationStatusText'; $PerformanceLandingScroll=X 'PerformanceLandingScroll'; $PerformanceTitle=X 'PerformanceTitle'; $PerformanceBody=X 'PerformanceBody'; $PerformanceEmpty=X 'PerformanceEmpty'; $HomeLandingScroll=X 'HomeLandingScroll'; $HomeLandingPanel=X 'HomeLandingPanel'; $ConceptOverviewPanel=X 'ConceptOverviewPanel'; $HomeTitle=X 'HomeTitle'; $HomeBody=X 'HomeBody'; $HomeStatusLabel=X 'HomeStatusLabel'; $HomeConnectionText=X 'HomeConnectionText'; $HomeConnectionBody=X 'HomeConnectionBody'; $HomeConceptsTitle=X 'HomeConceptsTitle'; $HomeConceptsBody=X 'HomeConceptsBody'; $HomeVisualsTitle=X 'HomeVisualsTitle'; $HomeVisualsBody=X 'HomeVisualsBody'; $HomeDeliveryTitle=X 'HomeDeliveryTitle'; $HomeDeliveryBody=X 'HomeDeliveryBody'; $HomeSafetyTitle=X 'HomeSafetyTitle'; $HomeSafetyBody=X 'HomeSafetyBody'; $HomeMetricPublishedLabel=X 'HomeMetricPublishedLabel'; $HomeMetricPublishedValue=X 'HomeMetricPublishedValue'; $HomeMetricPublishedHint=X 'HomeMetricPublishedHint'; $HomeMetricSalesLabel=X 'HomeMetricSalesLabel'; $HomeMetricSalesValue=X 'HomeMetricSalesValue'; $HomeMetricSalesHint=X 'HomeMetricSalesHint'; $HomeMetricRoyaltiesLabel=X 'HomeMetricRoyaltiesLabel'; $HomeMetricRoyaltiesValue=X 'HomeMetricRoyaltiesValue'; $HomeMetricRoyaltiesHint=X 'HomeMetricRoyaltiesHint'; $HomeMetricAttentionLabel=X 'HomeMetricAttentionLabel'; $HomeMetricAttentionValue=X 'HomeMetricAttentionValue'; $HomeMetricAttentionHint=X 'HomeMetricAttentionHint'; $HomePipelineTitle=X 'HomePipelineTitle'; $HomePipelineBody=X 'HomePipelineBody'; $HomeStageIdeas=X 'HomeStageIdeas'; $HomeStageArtwork=X 'HomeStageArtwork'; $HomeStageChecks=X 'HomeStageChecks'; $HomeStagePublish=X 'HomeStagePublish'; $HomeAlexTitle=X 'HomeAlexTitle'; $HomeAlexBody=X 'HomeAlexBody'; $HomePerformanceTitle=X 'HomePerformanceTitle'; $HomePerformanceBody=X 'HomePerformanceBody';
$LocalExportBriefButton=X 'LocalExportBriefButton'; $LocalImportArtworkButton=X 'LocalImportArtworkButton'; $LocalAcceptButton=X 'LocalAcceptButton'; $LocalCoreStatusText=X 'LocalCoreStatusText'; $LocalImportCheckEvidenceButton=X 'LocalImportCheckEvidenceButton'; $LocalCheckStatusText=X 'LocalCheckStatusText'; $LocalBuildPackageButton=X 'LocalBuildPackageButton'; $LocalImportSalesButton=X 'LocalImportSalesButton'; $LocalSalesStatusText=X 'LocalSalesStatusText'; $PerfSales7Value=X 'PerfSales7Value'; $PerfSales30Value=X 'PerfSales30Value'; $PerfRoyalties30Value=X 'PerfRoyalties30Value'; $PerfSales90Value=X 'PerfSales90Value'
$MainTabs=X 'MainTabs'; $OverviewHook=X 'OverviewHook'; $OverviewConcept=X 'OverviewConcept'; $OverviewBuyer=X 'OverviewBuyer'; $OverviewWhy=X 'OverviewWhy'; $OverviewDifferent=X 'OverviewDifferent'; $OverviewVisual=X 'OverviewVisual'; $OverviewMeaning=X 'OverviewMeaning'; $OverviewStatus=X 'OverviewStatus'; $OverviewWarnings=X 'OverviewWarnings'; $OverviewNext=X 'OverviewNext'; $OverviewVisualButton=X 'OverviewVisualButton'; $OverviewEditButton=X 'OverviewEditButton'; $PublicationHistoryEmpty=X 'PublicationHistoryEmpty'; $DeliveryStatus=X 'DeliveryStatus'; $ExportPackageButton=X 'ExportPackageButton'; $SendToSocialButton=X 'SendToSocialButton'; $PackageTargetBox=X 'PackageTargetBox'; $PreparePackageButton=X 'PreparePackageButton'; $PackageBoundaryText=X 'PackageBoundaryText'; $DownstreamLineage=X 'DownstreamLineage'; $DownstreamIp=X 'DownstreamIp'; $DownstreamVisualQa=X 'DownstreamVisualQa'; $DownstreamPrintQa=X 'DownstreamPrintQa'; $DownstreamPolicy=X 'DownstreamPolicy'; $DownstreamEligibility=X 'DownstreamEligibility'; $DownstreamBlocker=X 'DownstreamBlocker'; $DownstreamAdvanced=X 'DownstreamAdvanced'; $DownstreamExternal=X 'DownstreamExternal'; $PublicationCreativeStatus=X 'PublicationCreativeStatus'; $PublicationDraftNote=X 'PublicationDraftNote'; $PublicationBrandHint=X 'PublicationBrandHint'; $PublicationTitleBox=X 'PublicationTitleBox'; $PublicationBrandBox=X 'PublicationBrandBox'; $PublicationBullet1Box=X 'PublicationBullet1Box'; $PublicationBullet2Box=X 'PublicationBullet2Box'; $PublicationDescriptionBox=X 'PublicationDescriptionBox'; $PublicationKeywordsBox=X 'PublicationKeywordsBox'; $PublicationLocaleLabel=X 'PublicationLocaleLabel'; $PublicationLocaleBox=X 'PublicationLocaleBox'; $PublicationReasonBox=X 'PublicationReasonBox'; $PublicationDirtyLabel=X 'PublicationDirtyLabel'; $SavePublicationButton=X 'SavePublicationButton'; $PublicationHistoryList=X 'PublicationHistoryList'; $PublicationCheckIp=X 'PublicationCheckIp'; $PublicationCheckVisual=X 'PublicationCheckVisual'; $PublicationCheckPrint=X 'PublicationCheckPrint'; $PublicationCheckPolicy=X 'PublicationCheckPolicy'; $PublicationEconomics=X 'PublicationEconomics'; $PublicationPreflight=X 'PublicationPreflight'; $PublicationExternal=X 'PublicationExternal'; $PublicationAdvanced=X 'PublicationAdvanced'

# R2O module function: Has-Cap
function Get-MainTabKey($Tab) {
    if($null -eq $Tab){return ''}
    $tag=[string]$Tab.Tag; if(-not [string]::IsNullOrWhiteSpace($tag)){return $tag}
    return ([string]$Tab.Header).ToLowerInvariant()
}
# R2O module function: Apply-LocaleUi
# R2O module function: Set-UiLocale
# R2O module function: Sync-LanguageSelector
# R2O module function: Initialize-UiLocale
# R2O module function: Set-Thickness
# R2O module function: Set-GridLength
# R2O module function: New-StarGridLength
# R2O module function: Set-GridPos
# R2O module function: Set-QueueEmptyState
# R2O module function: Set-ResponsivePair
# R2O module function: Update-ResponsiveLayout
# R2O module function: Apply-RoleUi
# R2O module function: Set-PublicationDirty
# R2O module function: Update-AcceptanceControls
# R2O module function: Set-Busy
# R2O module function: Select-MainTab
# R2O module function: Set-ConceptTabsEnabled
# R2O module function: Update-MainTabUi
function Get-OverviewWorkflowState($c) {
    $rw=Get-PropertyValue $script:ReviewWorkspace 'workspace'
    $state=[string](Get-PropertyValue $rw 'review_workflow_state')
    if(-not [string]::IsNullOrWhiteSpace($state)){return $state}
    if(([string](Get-PropertyValue $c 'concept_status')) -in @('paused','rejected')){return 'blocked'}
    if([bool](Get-PropertyValue $c 'current_revision_accepted')){return 'accepted'}
    if([int](Get-PropertyValue $c 'current_variant_count') -gt 0){return 'has_variants'}
    if([int](Get-PropertyValue $c 'current_generation_runs') -gt 0){return 'generation_requested'}
    if([int](Get-PropertyValue $c 'revision_count') -gt 1){return 'in_edit'}
    return 'generation_ready'
}
function Get-OverviewNextAction([string]$State) {
    switch($State.ToLowerInvariant()) {
        'accepted' { return (Get-StaticUiText 'The visual is accepted. Review Delivery and Publication readiness when you are ready.') }
        'has_variants' { return (Get-StaticUiText 'Generated visuals are available. Review them in Visuals & Generate before any Accept decision.') }
        'generation_requested' { return (Get-StaticUiText 'Generation has been requested. Review the result when it arrives; do not submit anything externally.') }
        'in_edit' { return (Get-StaticUiText 'An edited brief is current. Review it, then generate only when you choose.') }
        'blocked' { return (Get-StaticUiText 'This concept is blocked. Review the evidence and blocker before generating.') }
        default { return (Get-StaticUiText 'The brief is ready. Review the idea first; Generate remains a separate explicit action.') }
    }
}
function Get-OwnerDecisionDisplay([string]$Decision) {
    $d=([string]$Decision).Trim().ToUpperInvariant();if($d -in @('KEEP','EDIT','REGEN','SKIP')){return $d};return 'UNDECIDED'
}
function Set-OwnerDecisionButtonState($Button,[bool]$Selected) {
    if($null-eq$Button){return};$Button.FontWeight=if($Selected){'Bold'}else{'Normal'};$Button.BorderBrush=if($Selected){$Window.FindResource('AccentStroke')}else{$Window.FindResource('ChromeStroke')};$Button.Background=if($Selected){$Window.FindResource('AccentSoft')}else{$Window.FindResource('ChromeSurface')};$Button.Foreground=$Window.FindResource('Text')
}
function Update-OwnerDecisionControls {
    if($null-eq$OwnerDecisionStatusText){return}
    if($null-ne$OwnerDecisionTitle){$OwnerDecisionTitle.Text=Get-UiText 'owner.review.title' 'Owner decision'}
    if($null-ne$OwnerDecisionBody){$OwnerDecisionBody.Text=Get-UiText 'owner.review.body' 'Choose what happens to this exact idea revision. Decisions are saved locally in Forge; they do not Generate, Accept or Publish.'}
    if($null-ne$OwnerKeepButton){$OwnerKeepButton.Content=Get-UiText 'owner.review.keep' 'KEEP'}
    if($null-ne$OwnerEditDecisionButton){$OwnerEditDecisionButton.Content=Get-UiText 'owner.review.edit' 'EDIT'}
    if($null-ne$OwnerRegenButton){$OwnerRegenButton.Content=Get-UiText 'owner.review.regen' 'REGEN'}
    if($null-ne$OwnerSkipButton){$OwnerSkipButton.Content=Get-UiText 'owner.review.skip' 'SKIP'}
    if($null-ne$OwnerClearDecisionButton){$OwnerClearDecisionButton.Content=Get-UiText 'owner.review.clear' 'Clear decision'}
    $enabled=($null-ne$script:Current -and -not$script:Busy)
    foreach($b in @($OwnerKeepButton,$OwnerEditDecisionButton,$OwnerRegenButton,$OwnerSkipButton,$OwnerClearDecisionButton)){if($null-ne$b){$b.IsEnabled=$enabled}}
    $decision='UNDECIDED'
    if($enabled){try{$key=[string](Get-PropertyValue $script:Current.concept 'concept_key');$rec=Get-LocalOwnerDecisionRecord $key $script:Current.concept;$decision=Get-OwnerDecisionDisplay ([string]$rec.decision)}catch{$decision='UNDECIDED'}}
    Set-OwnerDecisionButtonState $OwnerKeepButton ($decision-eq'KEEP');Set-OwnerDecisionButtonState $OwnerEditDecisionButton ($decision-eq'EDIT');Set-OwnerDecisionButtonState $OwnerRegenButton ($decision-eq'REGEN');Set-OwnerDecisionButtonState $OwnerSkipButton ($decision-eq'SKIP')
    $OwnerDecisionStatusText.Text=if($decision-eq'UNDECIDED'){Get-UiText 'owner.review.none' 'No decision yet'}else{(Get-UiText 'owner.review.saved' 'Current decision')+': '+$decision+' · '+([string](Get-PropertyValue (Get-LocalOwnerDecisionRecord ([string](Get-PropertyValue $script:Current.concept 'concept_key')) $script:Current.concept) 'decided_at'))}
    try{$p=Get-LocalOwnerDecisionProgress;$OwnerDecisionProgressText.Text=(Get-UiText 'owner.review.progress' '{0} of {1} ideas decided · KEEP {2} · EDIT {3} · REGEN {4} · SKIP {5}') -f $p.decided,$p.total,$p.keep,$p.edit,$p.regen,$p.skip}catch{$OwnerDecisionProgressText.Text=''}
}
function Set-Dirty([bool]$Value) { $script:Dirty=$Value; $draftEdit=(Test-CurrentIsResearchDraft); $DirtyLabel.Text=if(-not ((Has-Cap 'edit') -or $draftEdit)){Get-UiText 'role.readonly' 'Read-only for this role'}elseif($Value){Get-UiText 'status.unsaved' 'Unsaved changes'}else{''}; $curConcept=Get-PropertyValue $script:Current 'concept'; $accepted=($null -ne $curConcept -and [bool](Get-PropertyValue $curConcept 'current_revision_accepted')); $SaveButton.IsEnabled=(-not $script:Busy -and ((Has-Cap 'edit') -or $draftEdit) -and $Value -and $null -ne $script:Current -and -not $accepted); Update-AcceptanceControls }
function Format-Revision($r) {
    if($null -eq $r){return ''}
    return ("Revision {0}`nHook: {1}`nConcept: {2}`nBuyer: {3}`nPurchase: {4}`nDifferentiation: {5}`nVisual: {6}" -f (Get-PropertyValue $r 'revision_no'),(Get-PropertyValue $r 'hook'),(Get-PropertyValue $r 'concept_text'),(Get-PropertyValue $r 'target_buyer'),(Get-PropertyValue $r 'purchase_reason'),(Get-PropertyValue $r 'differentiation'),(Get-PropertyValue $r 'visual_direction_text'))
}
function Format-RevisionAdvanced($r) {
    if($null -eq $r){return ''}
    $actor=Get-PropertyValue $r 'editor_actor'
    if([string]::IsNullOrWhiteSpace([string]$actor)){$actor=Get-PropertyValue $r 'created_by_actor'}
    return ("Revision ID: {0}`nKind: {1}`nContent hash: {2}`nCreated by: {3}`nCreated: {4}" -f $r.id,$r.revision_kind,$r.content_hash,$actor,$r.created_at)
}
function Show-WorkflowState($Value){switch(([string]$Value).ToLowerInvariant()){'generation_ready'{return (Get-StaticUiText 'Ready to generate')}'in_edit'{return (Get-StaticUiText 'Editing')}'generation_requested'{return (Get-StaticUiText 'Generation requested')}'has_variants'{return (Get-StaticUiText 'Has variants')}'accepted'{return (Get-StaticUiText 'Accepted')}'blocked'{return (Get-StaticUiText 'Blocked')}'research_draft'{return (Get-UiText 'draft.state' 'Research draft')}default{return (Get-StaticUiText 'In progress')}}}
function Get-WorkflowForeground($Value){switch(([string]$Value).ToLowerInvariant()){'generation_ready'{return '#F28C52'}'in_edit'{return '#78B7EA'}'generation_requested'{return '#F0BF5A'}'has_variants'{return '#78B7EA'}'accepted'{return '#6FD29A'}'blocked'{return '#F07878'}'research_draft'{return '#C4A4F2'}default{return '#93A0AD'}}}
function Get-WorkflowBackground($Value){switch(([string]$Value).ToLowerInvariant()){'generation_ready'{return '#392419'}'in_edit'{return '#172A3B'}'generation_requested'{return '#352A15'}'has_variants'{return '#172A3B'}'accepted'{return '#173128'}'blocked'{return '#381D22'}'research_draft'{return '#2A2238'}default{return '#1C2630'}}}
function Show-GenerationStatus($Value){switch(([string]$Value).ToLowerInvariant()){'queued'{return 'Queued'}'dispatching'{return 'Starting'}'generating'{return 'In progress'}'succeeded'{return 'Complete'}'complete'{return 'Complete'}'failed'{return 'Needs attention'}'cancelled'{return 'Cancelled'}default{return 'In progress'}}}
function Show-GenerationKind($Value){switch(([string]$Value).ToLowerInvariant()){'initial'{return 'Initial'}'regenerate'{return 'Regeneration'}default{return 'Generation'}}}
# R2O module function: Apply-Filter
# R2O module function: Load-Queue
function Connect-Workbench([bool]$FromRetry=$false) {
    if($script:Busy){return}
    if(-not $FromRetry){
        $script:OwnerKey=$OwnerKeyBox.Password
        if([string]::IsNullOrWhiteSpace($script:OwnerKey)){Show-Error 'Workspace access is required.';return}
    } elseif([string]::IsNullOrWhiteSpace($script:OwnerKey)) {
        $AppGrid.Visibility='Collapsed';$LoginGrid.Visibility='Visible';$OwnerKeyBox.Focus()|Out-Null;return
    }
    if($null -ne $BackendRetryButton){$BackendRetryButton.IsEnabled=$false;$BackendRetryButton.Content=Get-UiText 'backend.retrying' 'Retrying…'}
    if($null -ne $StatusText -and $AppGrid.Visibility -eq 'Visible'){$StatusText.Text=Get-UiText 'backend.retrying' 'Retrying…'}
    try {
        $contract=Invoke-ForgeApi 'workbench_contract'
        $backend=[version]$contract.service_version;$script:BackendVersion=[string]$contract.service_version
        if($backend -lt $script:MinimumBackendVersion){throw "CLIENT_TOO_OLD: backend $backend; minimum $($script:MinimumBackendVersion)"}
        if([version]$contract.contract.version -lt [version]'1.3'){throw 'CLIENT_TOO_OLD: Theme 9 package contract / Workbench contract 1.3 is required.'}
        $session=Invoke-ForgeApi 'session_context'
        if($null -eq $session -or [string]::IsNullOrWhiteSpace([string]$session.actor_key)){throw 'SESSION_CONTEXT: workspace session context is missing.'}
        $script:Session=$session
        if($RememberBox.IsChecked){Save-EncryptedOwnerKey $script:OwnerKey}
        $script:ConnectionState='Connected';$script:OfflineMode=$false;$BackendText.Text='Connected';$LoginGrid.Visibility='Collapsed';$AppGrid.Visibility='Visible';Set-BackendBannerState $false
        Apply-RoleUi;Show-HomeLanding $false;Load-Queue
        Set-BackendBannerState $false;$RefreshButton.IsEnabled=$true
    } catch {
        $technical=$_.Exception.Message
        if(Test-BackendUnavailableMessage $technical){
            if($RememberBox.IsChecked -and -not [string]::IsNullOrWhiteSpace($script:OwnerKey)){try{Save-EncryptedOwnerKey $script:OwnerKey}catch{}}
            Enter-OfflineWorkbench $technical
        } else {
            $script:ConnectionState='Not connected';$script:Session=$null;$script:BackendVersion=$null
            if($null -ne $BackendText){$BackendText.Text='Not connected'};Set-BackendBannerState $false
            if([string]::IsNullOrWhiteSpace($script:OwnerKey)){$AppGrid.Visibility='Collapsed';$LoginGrid.Visibility='Visible'}
            Show-Error $technical
        }
    } finally {
        if($null -ne $BackendRetryButton){$BackendRetryButton.IsEnabled=$true;$BackendRetryButton.Content=Get-UiText 'backend.retry' 'Retry'}
    }
}
function Clip-Text([string]$Text,[int]$Max) {
    $t=([string]$Text).Trim(); if($t.Length -le $Max){return $t}; return ($t.Substring(0,[Math]::Max(0,$Max-1)).TrimEnd()+"…")
}
function Get-GenerationBriefSummary($c) {
    $spec=Get-PropertyValue $c 'production_spec'
    $parts=@()
    $composition=[string](Get-PropertyValue $spec 'composition'); if($composition){$parts+=("Composition: "+$composition)}
    $illustration=[string](Get-PropertyValue $spec 'illustration'); if($illustration){$parts+=("Artwork: "+$illustration)}
    $notes=[string](Get-PropertyValue $spec 'generation_notes'); if($notes){$parts+=("Direction: "+$notes)}
    $palette=@(Get-PropertyValue $spec 'ink_palette'); if($palette.Count){$parts+=("Palette: "+($palette -join ', '))}
    $variants=@(Get-PropertyValue $spec 'variants'); if($variants.Count){$parts+=("Planned variants: "+($variants -join ' · '))}
    $avoid=@(Get-PropertyValue $spec 'avoid'); if($avoid.Count){$parts+=("Avoid: "+($avoid -join ' · '))}
    if(-not $parts.Count){$v=[string](Get-PropertyValue $c 'visual_direction_text'); if($v){$parts+=$v}}
    if(-not $parts.Count){return 'Forge has no structured generation brief for this concept yet.'}
    return ($parts -join "`n")
}
function Get-SuggestedKeywords($c) {
    $source=((([string](Get-PropertyValue $c 'niche_name'))+' '+([string](Get-PropertyValue $c 'target_buyer'))+' '+([string](Get-PropertyValue $c 'title'))+' '+([string](Get-PropertyValue $c 'hook'))) -replace '[^A-Za-z0-9&+\- ]',' ')
    $stop=@('the','and','for','with','this','that','from','away','very','large','one','what','you','your','tech','technician','design','shirt','tshirt','t','a','an','to','of','in','on','is','it','i')
    $seen=@{}; $out=@()
    foreach($w in ($source -split '\s+')){$k=$w.Trim().ToLowerInvariant();if($k.Length -lt 3 -or $stop -contains $k -or $seen.ContainsKey($k)){continue};$seen[$k]=$true;$out+=$k;if($out.Count -ge 12){break}}
    return ($out -join ', ')
}
function Get-SuggestedPublicationDraft($c) {
    $title=[string](Get-PropertyValue $c 'title'); if($title -and $title -notmatch '(?i)shirt|t-shirt'){$title += ' T-Shirt'}
    $hook=[string](Get-PropertyValue $c 'hook'); $why=[string](Get-PropertyValue $c 'purchase_reason'); $buyer=[string](Get-PropertyValue $c 'target_buyer'); $diff=[string](Get-PropertyValue $c 'differentiation'); $concept=[string](Get-PropertyValue $c 'concept_text')
    $b1=(@($hook,$why) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }) -join ' '
    $b2=(@($buyer,$diff) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }) -join ' — '
    $desc=(@($concept,$why,$buyer) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }) -join ' '
    return [pscustomobject]@{
        title=(Clip-Text $title 120); bullet1=(Clip-Text $b1 256); bullet2=(Clip-Text $b2 256); description=(Clip-Text $desc 1200); keywords=(Get-SuggestedKeywords $c)
    }
}
function Use-ValueOrSuggestion($Actual,$Suggested) {
    $a=[string]$Actual; if(-not [string]::IsNullOrWhiteSpace($a)){return $a}; return [string]$Suggested
}

# R2O module function: Populate-Detail
# R2O module function: Show-GateState
# R2O module function: Show-PublicationCheckState
# R2O module function: Show-PublicationBlocker
function Format-PublicationEconomics($w) {
    $state=([string]$w.economics_status).Trim().ToLowerInvariant()
    if([string]::IsNullOrWhiteSpace($state) -or $state -eq 'unverified') { return 'Needs live quote. No price or royalty is assumed. Check the live Merch editor before submission.' }
    if($state -eq 'stale') { return ("Stale snapshot · {0} {1} list price · {0} {2} estimated royalty`nValid as of {3}. Refresh from the live Merch editor before submission." -f $w.currency,$w.base_price,$w.royalty_estimate,$w.economics_valid_as_of) }
    if($state -eq 'not_required') { return 'Not required for this publication path.' }
    return ("Current sourced snapshot · {0} {1} list price · {0} {2} estimated royalty`nValid as of {3}. Live Merch editor quote remains binding before submission." -f $w.currency,$w.base_price,$w.royalty_estimate,$w.economics_valid_as_of)
}
function Format-PublicationAdvanced($w,$r) {
    $sources=if($null -ne $w.economics_source_refs){$w.economics_source_refs|ConvertTo-Json -Depth 10 -Compress}else{'[]'}
    return ("Creative acceptance ID: {0}`nCreative revision ID: {1}`nRevision hash: {2}`nVisual candidate ID: {3}`nVariant SHA-256: {4}`nPublication draft ID: {5}`nMetadata revision ID: {6}`nMetadata hash: {7}`nRaw states: ip={8}; visual={9}; print={10}; policy={11}; economics={12}`nPreflight input ready: {13}`nSubmit gate ready: {14}`nExternal submission authorized: false`nEconomics source refs: {15}" -f $w.current_acceptance_id,$w.current_revision_id,$w.accepted_revision_hash,$w.accepted_visual_candidate_id,$w.accepted_variant_sha256,$w.publication_draft_id,$w.current_metadata_revision_id,$w.metadata_content_hash,$w.ip_status,$w.visual_qa_status,$w.print_qa_status,$w.policy_preflight_status,$w.economics_status,$w.preflight_input_ready,$w.submit_gate_ready,$sources)
}
function Format-AuditEvent($e) { if($null -eq $e){return ''}; return ("{0}`n{1}`n`n{2}" -f $e.event_at,$e.title,$e.summary) }
function Format-AuditAdvanced($e) { if($null -eq $e){return ''}; $ev=if($null -ne $e.evidence){$e.evidence|ConvertTo-Json -Depth 12}else{'{}'}; return ("Event type: {0}`nActor: {1}`nRevision ID: {2}`nVariant ID: {3}`nAcceptance ID: {4}`n`nEvidence:`n{5}" -f $e.event_type,$e.actor,$e.revision_id,$e.visual_candidate_id,$e.acceptance_id,$ev) }
function Format-DownstreamAdvanced($d) { if($null -eq $d){return ''}; return ("Revision ID: {0}`nRevision hash: {1}`nAcceptance ID: {2}`nVisual candidate ID: {3}`nVariant hash: {4}`nIP check ID: {5}`nVisual QA check ID: {6}`nPrint QA check ID: {7}`nPolicy check ID: {8}`nRaw blocker: {9}" -f $d.current_revision_id,$d.accepted_revision_hash,$d.current_acceptance_id,$d.accepted_visual_candidate_id,$d.accepted_variant_sha256,$d.ip_check_id,$d.visual_qa_check_id,$d.print_qa_check_id,$d.policy_preflight_check_id,$d.blocking_reason) }
# R2O module function: Load-AuditHistory
# R2O module function: Load-Downstream
# R2O module function: Load-Publication
# R2O module function: Update-PackageButtons
function Format-DeliveryStatus($w) {
    if($null -eq $w){return 'Package readiness is unavailable.'}
    $compile=if([bool]$w.delivery_compile_ready){'Delivery manifest can be prepared.'}else{"Delivery blocked: $($w.blocking_reason)."}
    $bundle=if([bool]$w.export_ready){'Manifest prepared.'}else{'No delivery manifest yet.'}
    $local=if([bool]$w.local_materialized){'Saved locally and verified.'}else{'No verified local ZIP receipt.'}
    $social=if([bool]$w.social_handoff_ready){'Social source envelope prepared.'}else{'No Social handoff envelope.'}
    $owner=@(); if([bool]$w.generic_owner_package_ready){$owner+='owner export'}; if([bool]$w.social_source_package_ready){$owner+='Social source'}; if([bool]$w.amazon_owner_package_ready){$owner+='Amazon owner'}
    $pkg=if($owner.Count){'Ready packages: '+($owner -join ', ')+'.'}else{'No owner package prepared.'}
    return ($compile+"`n"+$bundle+' '+$local+"`n"+$social+"`n"+$pkg)
}
# R2O module function: Load-Delivery
# R2O module function: Prepare-DeliveryPackage
# R2O module function: Prepare-SocialHandoff
# R2O module function: Prepare-OwnerPackage
# R2O module function: Save-PublicationMetadata
# R2O module function: Load-Concept
# R2O module function: Open-ConceptItem
# R2O module function: Open-ConceptFromPointer
function Build-Patch {
    return @{ title=$TitleBox.Text; hook=$HookBox.Text; concept_text=$ConceptTextBox.Text; target_buyer=$BuyerBox.Text; purchase_reason=$PurchaseBox.Text; differentiation=$DifferentiationBox.Text; visual_direction_text=$VisualBox.Text }
}
# R2O module function: Save-Revision
# R2O module function: Update-CancelGenerationState
# R2O module function: Queue-Generation
# R2O module function: Cancel-Generation
function Format-Variant($v) {
    if($null -eq $v){return ''}; $review=if([string]::IsNullOrWhiteSpace([string]$v.review_state)){'Not reviewed'}else{[string]$v.review_state}
    return ("Variant {0}`nState: {1}`nReview: {2}`nNote: {3}`nCreated: {4}" -f $v.variant_index,(Show-GenerationStatus $v.status),$review,$v.review_note,$v.created_at)
}
function Format-VariantAdvanced($v) {
    if($null -eq $v){return ''}; $asset=if($null -ne $v.asset_metadata){$v.asset_metadata|ConvertTo-Json -Depth 8 -Compress}else{'{}'}
    return ("Variant key: {0}`nRaw status: {1}`nRevision ID: {2}`nOlder revision: {3}`nAsset: {4}`nPreview key: {5}`nSHA-256: {6}`nGeneration request ID: {7}" -f $v.variant_key,$v.status,$v.concept_revision_id,$v.stale_revision,$asset,$v.preview_key,$v.asset_sha256,$v.generation_request_id)
}

# R2O module function: Get-ByteSha256Hex
# R2O module function: Get-ObjectTextProperty
# R2O module function: Get-PreviewCachePaths
# R2O module function: Trim-PreviewCache
# R2O module function: Save-VerifiedPreviewCache
# R2O module function: Read-VerifiedPreviewCache
# R2O module function: ConvertTo-FrozenBitmapImage
# R2O module function: Clear-VariantPreviewImage
# R2O module function: Get-VariantPreviewBitmap
# R2O module function: Set-VariantPreviewImage
# R2O module function: Update-VariantVisualPreview
function Update-ReviewReasonOptions {
    if($null -eq $VariantReviewReason -or $null -eq $VariantReviewState.SelectedItem){return}
    $state=[string]$VariantReviewState.SelectedItem.Content
    $items=switch($state){
      'reject' {@('wrong_text','weak_composition','poor_legibility','bad_typography','bad_color_or_contrast','off_brief','artifact_or_quality_issue','too_generic','not_sellable','other')}
      'favorite' {@('','best_composition','best_typography','best_color','best_readability','closest_to_brief','strongest_purchase_trigger','other')}
      default {@('','clear_preference','other')}
    }
    $VariantReviewReason.ItemsSource=$items; $VariantReviewReason.SelectedIndex=0
}
function Update-VariantSelection {
    $selected=@($VariantList.SelectedItems)
    $CompareVariantsButton.IsEnabled=(-not $script:Busy -and $selected.Count -eq 2)
    if($selected.Count -ge 1){
        $v=$selected[0]; $VariantPreview.Text=Format-Variant $v
        $state=[string]$v.review_state
        if($state){for($i=0;$i -lt $VariantReviewState.Items.Count;$i++){if([string]$VariantReviewState.Items[$i].Content -eq $state){$VariantReviewState.SelectedIndex=$i;break}}}
        Update-ReviewReasonOptions
        $reasons=@($v.latest_reason_codes); if($reasons.Count -gt 0){$idx=$VariantReviewReason.Items.IndexOf([string]$reasons[0]);if($idx -ge 0){$VariantReviewReason.SelectedIndex=$idx}}
        $VariantReviewNote.Text=[string]$v.review_note
        $VariantAdvanced.Text=Format-VariantAdvanced $v
    } else {$VariantPreview.Text='Select a variant.';$VariantAdvanced.Text='';$VariantReviewNote.Text='';Update-ReviewReasonOptions}
    Update-AcceptanceControls
    Update-VariantVisualPreview
}
function Compare-Variants {
    $selected=@($VariantList.SelectedItems); if($selected.Count -ne 2){return}
    $VariantCompareA.Text=Format-Variant $selected[0]; $VariantCompareB.Text=Format-Variant $selected[1]
    Update-VariantVisualPreview
}
# R2O module function: Save-VariantReview
# R2O module function: Accept-Current
# R2O module function: Reopen-CurrentAcceptance
# R2O module function: Start-NewIteration
function Refresh-Workbench {
    if($script:ConnectionState -ne 'Connected'){try{if($null -ne $script:Current){Refresh-LocalArtworkUi}}catch{Write-AppLog 'WARN' ('Local generation refresh failed: '+$_.Exception.Message)};Connect-Workbench $true;return}
    if($script:Dirty -or $script:PublicationDirty){if(-not (Confirm 'Refresh Workbench and discard unsaved creative/publication edits?' 'Refresh Workbench')){return}}
    $key=if($null -ne $script:Current){[string]$script:Current.concept.concept_key}else{$null}
    $script:Dirty=$false;$script:PublicationDirty=$false
    try{Load-Queue;if(-not [string]::IsNullOrWhiteSpace($key)){Load-Concept $key $true|Out-Null}}catch{Show-Error $_.Exception.Message}
}
$publicationBoxes=@($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox); foreach($b in $publicationBoxes){$b.Add_TextChanged({ $localPub=($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')); if($null -ne $script:Publication -and -not $script:Busy -and ((Has-Cap 'prepare_publication') -or $localPub) -and -not $b.IsReadOnly){Set-PublicationDirty $true} })}; $SavePublicationButton.Add_Click({Save-PublicationMetadata}); $ExportPackageButton.Add_Click({Prepare-DeliveryPackage}); $SendToSocialButton.Add_Click({Prepare-SocialHandoff}); $PreparePackageButton.Add_Click({Prepare-OwnerPackage}); $LocalBuildPackageButton.Add_Click({Build-LocalAmazonPackage}); $PackageTargetBox.Add_SelectionChanged({Update-PackageButtons})
$editBoxes=@($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox); foreach($b in $editBoxes){$b.Add_TextChanged({ if($null -ne $script:Current -and -not $script:Busy -and ((Has-Cap 'edit') -or (Test-CurrentIsResearchDraft))){Set-Dirty $true} })}
$SearchBox.Add_TextChanged({$SearchPlaceholder.Visibility=if([string]::IsNullOrWhiteSpace([string]$SearchBox.Text)){'Visible'}else{'Collapsed'};Apply-Filter}); $FilterBox.Add_SelectionChanged({Apply-Filter}); $SortBox.Add_SelectionChanged({Apply-Filter})
$ConceptList.Add_SelectionChanged({ if($null -ne $ConceptList.SelectedItem){Open-ConceptItem $ConceptList.SelectedItem} })
$ConceptList.Add_PreviewMouseLeftButtonUp({param($sender,$e);Open-ConceptFromPointer $e.OriginalSource})
$CompactConceptBox.Add_SelectionChanged({if($CompactConceptBox.Visibility -eq 'Visible' -and $null -ne $CompactConceptBox.SelectedItem){Open-ConceptItem $CompactConceptBox.SelectedItem}})
$RevisionList.Add_SelectionChanged({$r=$RevisionList.SelectedItem;if($null -ne $r){$SelectedRevisionPreview.Text=Format-Revision $r;$RevisionAdvanced.Text=Format-RevisionAdvanced $r;$RestoreRevisionButton.IsEnabled=((Has-Cap 'edit') -and [string]$r.id -ne [string]$script:Current.concept.current_revision_id)}})
$AuditList.Add_SelectionChanged({$e=$AuditList.SelectedItem;if($null -ne $e){$AuditDetail.Text=Format-AuditEvent $e;$AuditAdvanced.Text=Format-AuditAdvanced $e}else{$AuditDetail.Text='';$AuditAdvanced.Text=''}})
$RestoreRevisionButton.Add_Click({$r=$RevisionList.SelectedItem;if($null -eq $r -or $null -eq $script:Current){return};if(-not (Confirm ("Restore revision {0} as a NEW revision? History will be preserved." -f $r.revision_no))){return};$TitleBox.Text=$r.title;$HookBox.Text=$r.hook;$ConceptTextBox.Text=$r.concept_text;$BuyerBox.Text=$r.target_buyer;$PurchaseBox.Text=$r.purchase_reason;$DifferentiationBox.Text=$r.differentiation;$VisualBox.Text=$r.visual_direction_text;$SpecBox.Text=($r.production_spec|ConvertTo-Json -Depth 20);$ReasonBox.Text=("Restore from revision {0}" -f $r.revision_no);$script:RestoreSourceRevisionId=[string]$r.id;Set-Dirty $true;$null=Select-MainTab 'Edit'})
$MainTabs.Add_SelectionChanged({Update-MainTabUi})
$OverviewVisualButton.Add_Click({if($script:OfflineMode -or (Test-CurrentIsResearchDraft)){Show-ProductSection 'artwork'}else{Select-MainTab 'Visuals & Generate'}})
$OverviewEditButton.Add_Click({Select-MainTab 'Edit'})
$VariantReviewState.Add_SelectionChanged({Update-ReviewReasonOptions}); Update-ReviewReasonOptions
$VariantList.Add_SelectionChanged({Update-VariantSelection;Update-LocalCoreStatusUi}); $CompareVariantsButton.Add_Click({Compare-Variants}); $SaveVariantReviewButton.Add_Click({Save-VariantReview}); $LocalExportBriefButton.Add_Click({Export-LocalGenerationBrief}); $LocalImportArtworkButton.Add_Click({Import-LocalArtwork}); $LocalAcceptButton.Add_Click({Accept-LocalArtwork}); $LocalImportCheckEvidenceButton.Add_Click({Import-LocalCheckEvidence}); $LocalImportSalesButton.Add_Click({Import-LocalSalesCsv}); $LocalImportPublicationReceiptButton.Add_Click({Import-LocalPublicationReceipt})
$SaveButton.Add_Click({Save-Revision}); $GenerateButton.Add_Click({Queue-Generation}); $CancelGenerationButton.Add_Click({Cancel-Generation}); $GenerationRequestList.Add_SelectionChanged({Update-CancelGenerationState}); $AcceptButton.Add_Click({Accept-Current}); $ReopenAcceptanceButton.Add_Click({Reopen-CurrentAcceptance}); $StartIterationSameButton.Add_Click({Start-NewIteration 'same_brief'}); $StartIterationEditButton.Add_Click({Start-NewIteration 'edit_brief'})
$OwnerKeepButton.Add_Click({[void](Set-LocalOwnerDecision 'KEEP')});$OwnerEditDecisionButton.Add_Click({[void](Set-LocalOwnerDecision 'EDIT')});$OwnerRegenButton.Add_Click({[void](Set-LocalOwnerDecision 'REGEN')});$OwnerSkipButton.Add_Click({[void](Set-LocalOwnerDecision 'SKIP')});$OwnerClearDecisionButton.Add_Click({[void](Set-LocalOwnerDecision 'UNDECIDED')});
$HomeButton.Add_Click({Go-Home}); $NavHomeButton.Add_Click({Show-ProductSection 'home'}); $NavDiscoverButton.Add_Click({Show-ProductSection 'discover'}); $NavIdeasButton.Add_Click({Show-ProductSection 'ideas'}); $NavArtworkButton.Add_Click({Show-ProductSection 'artwork'}); $NavChecksButton.Add_Click({Show-ProductSection 'checks'}); $NavPublishButton.Add_Click({Show-ProductSection 'publish'}); $NavPortfolioButton.Add_Click({Show-ProductSection 'portfolio'}); $NavPerformanceButton.Add_Click({Show-ProductSection 'performance'}); $ContextHistoryButton.Add_Click({if($null -ne $script:Current){$MainTabs.Visibility='Visible';Select-MainTab 'History';Update-MainTabUi}}); $ContextDeliveryButton.Add_Click({if($null -ne $script:Current){$MainTabs.Visibility='Visible';Select-MainTab 'Delivery';Update-MainTabUi}}); $ContextEditButton.Add_Click({if($null -ne $script:Current){$MainTabs.Visibility='Visible';Select-MainTab 'Edit';Update-MainTabUi}}); $AboutButton.Add_Click({Show-About}); $DiagnosticsButton.Add_Click({Show-Diagnostics}); $RefreshButton.Add_Click({Refresh-Workbench}); $BackendRetryButton.Add_Click({Connect-Workbench $true})
$DiscoverCreateDraftButton=X 'DiscoverCreateDraftButton'; $DiscoverDraftStatusText=X 'DiscoverDraftStatusText'
$PortfolioPipelineTitle=X 'PortfolioPipelineTitle'; $PortfolioPipelineSummary=X 'PortfolioPipelineSummary'; $PortfolioNextTitle=X 'PortfolioNextTitle'; $PortfolioPipelineList=X 'PortfolioPipelineList'; $PortfolioNicheTitle=X 'PortfolioNicheTitle'; $PortfolioNicheText=X 'PortfolioNicheText'; $PipeUndecidedLabel=X 'PipeUndecidedLabel'; $PipeUndecidedValue=X 'PipeUndecidedValue'; $PipeKeepLabel=X 'PipeKeepLabel'; $PipeKeepValue=X 'PipeKeepValue'; $PipeArtworkLabel=X 'PipeArtworkLabel'; $PipeArtworkValue=X 'PipeArtworkValue'; $PipeChecksLabel=X 'PipeChecksLabel'; $PipeChecksValue=X 'PipeChecksValue'; $PipePackageLabel=X 'PipePackageLabel'; $PipePackageValue=X 'PipePackageValue'; $PipePublishedLabel=X 'PipePublishedLabel'; $PipePublishedValue=X 'PipePublishedValue'
$LocalConfirmChecksButton=X 'LocalConfirmChecksButton'; $LocalOpenChecksFolderButton=X 'LocalOpenChecksFolderButton'; $LocalConfirmChecksButton.Add_Click({Invoke-ConfirmChecks}); $LocalOpenChecksFolderButton.Add_Click({Open-LocalChecksFolder}); $PublicationListingHints=X 'PublicationListingHints'; foreach($lb in @($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox)){ $lb.Add_TextChanged({ Update-ListingHints }) }; $DataBackupButton=X 'DataBackupButton'; $DataRestoreButton=X 'DataRestoreButton'; $DataBackupButton.Add_Click({Invoke-DataBackupSave}); $DataRestoreButton.Add_Click({Invoke-DataBackupRestore}); $AmazonProfileStatusText=X 'AmazonProfileStatusText'; $AmazonProfileFormButton=X 'AmazonProfileFormButton'; $AmazonProfileImportButton=X 'AmazonProfileImportButton'; $AmazonProfileFormButton.Add_Click({Invoke-AmazonProfileForm}); $AmazonProfileImportButton.Add_Click({Import-AmazonPrintProfileFile}); $PerformanceLeadersText=X 'PerformanceLeadersText'; $PerformanceAttentionText=X 'PerformanceAttentionText'
$PortfolioPipelineList.Add_SelectionChanged({Open-PortfolioPipelineSelection})
try{Initialize-MessageTranslations;Register-MessageLocalizationSinks}catch{Write-AppLog 'WARN' ('Message localization unavailable: '+$_.Exception.Message)}
$DiscoverRefreshButton.Add_Click({Load-DiscoverSnapshot $true})
$DiscoverCreateDraftButton.Add_Click({Invoke-DiscoverCreateDraft})
$DiscoverNicheList.Add_SelectionChanged({Update-DiscoverDetail;Update-DiscoverDraftControls})
$PublicationLocaleBox.Add_SelectionChanged({ if($script:ConceptLoadInProgress -or $script:LocaleChangeInProgress){return}; if($null -ne $script:Publication){Set-PublicationDirty $true} })
$LanguageBox.Add_SelectionChanged({ if($script:LocaleChangeInProgress -or $null -eq $LanguageBox.SelectedItem){return}; $requested=[string]$LanguageBox.SelectedItem.Tag; if(-not (Set-UiLocale $requested $true)){Sync-LanguageSelector}else{Sync-LanguageSelector} })
$LoginLanguageBox.Add_SelectionChanged({ if($script:LocaleChangeInProgress -or $null -eq $LoginLanguageBox.SelectedItem){return}; $requested=[string]$LoginLanguageBox.SelectedItem.Tag; if(-not (Set-UiLocale $requested $true)){Sync-LanguageSelector}else{Sync-LanguageSelector} })
$LoginLangEn.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'en' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}}); $LoginLangRu.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'ru' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}}); $LoginLangEs.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'es' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}})
$HeaderLangEn.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'en' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}}); $HeaderLangRu.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'ru' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}}); $HeaderLangEs.Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale 'es' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}})
$UtilityCloseButton.Add_Click({Hide-UtilityPanel}); $UtilityCloseTopButton.Add_Click({Hide-UtilityPanel}); $UtilityCopyButton.Add_Click({try{[Windows.Clipboard]::SetText([string]$UtilityTechnicalText.Text);$StatusText.Text='Diagnostics copied.'}catch{Write-AppLog 'ERROR' ("Copy diagnostics: "+$_.Exception.Message);$StatusText.Text='Could not copy diagnostics.'}}); $UtilityOpenLogButton.Add_Click({Open-DiagnosticLogSafe})
$ForgetButton.Add_Click({if(Confirm 'Sign out and remove saved access from this Windows account?'){Remove-EncryptedOwnerKey;$script:OwnerKey=$null;$script:Session=$null;$script:BackendVersion=$null;$script:ConnectionState='Not connected';$script:OfflineMode=$false;$script:OfflineSnapshotMode=$false;$BackendText.Text=Get-UiText 'system.notconnected' 'Not connected';$ActorText.Text=Get-UiText 'system.notconnected' 'Not connected';Set-BackendBannerState $false;$AppGrid.Visibility='Collapsed';$LoginGrid.Visibility='Visible'}})
$ConnectButton.Add_Click({Connect-Workbench $false})
$Window.Add_SizeChanged({Update-ResponsiveLayout})
$Window.Add_KeyDown({param($sender,$e);if($e.Key -eq 'Escape' -and $UtilityOverlay.Visibility -eq 'Visible'){Hide-UtilityPanel;$e.Handled=$true}elseif($e.Key -eq 'F5'){Refresh-Workbench;$e.Handled=$true}elseif($e.Key -eq 'S' -and ([Windows.Input.Keyboard]::Modifiers -band [Windows.Input.ModifierKeys]::Control)){if($null -ne $MainTabs.SelectedItem -and (Get-MainTabKey $MainTabs.SelectedItem) -eq 'publication'){if($SavePublicationButton.IsEnabled){Save-PublicationMetadata}}elseif($SaveButton.IsEnabled){Save-Revision};$e.Handled=$true}})
$Window.Add_Closing({param($sender,$e);if($script:Dirty -or $script:PublicationDirty){if(-not (Confirm 'Close Workbench and discard unsaved creative/publication edits?')){$e.Cancel=$true}}})
$Window.Add_ContentRendered({Initialize-LocalCore;Initialize-GenerationWorkerBridge;Show-ProductSection 'home';Update-LocalCoreBusinessSurfaces;Update-OwnerDecisionControls;Update-ResponsiveLayout;Update-MainTabUi;try{if($env:MERCH_FORGE_READY_FILE){Set-Content -LiteralPath $env:MERCH_FORGE_READY_FILE -Value 'ready' -Encoding ASCII -Force}}catch{}; $saved=Load-EncryptedOwnerKey;if(-not [string]::IsNullOrWhiteSpace($saved)){$OwnerKeyBox.Password=$saved}})
Initialize-UiLocale

try { Write-AppLog 'INFO' "Starting Workbench $script:AppVersion"; $null=$Window.ShowDialog(); exit 0 } catch { Show-FatalError $_.Exception.Message; exit 1 }
