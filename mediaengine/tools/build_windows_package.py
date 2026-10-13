"""Assemble a self-contained Windows package of the MediaEngine candidate (run on Windows, CPython 3.11).

  python mediaengine/tools/build_windows_package.py <out_dir> [<evidence_dir>]

Layout (side-by-side with a stable D:\\Archivist install; nothing outside its own folder is touched except
its own desktop shortcut "MediaEngine RC"):

  MediaEngine-<version>-b<build>/
    Start MediaEngine.vbs      one obvious launch (no console)
    README.txt  ПРОЧТИ.txt     short guide (English / Russian)
    BUILD.txt                  exact source commit
    launcher.py  app/  requirements.txt  version.txt  port.txt (8775)  shortcut_name.txt
    .venv/Scripts/             relocatable CPython 3.11 + pinned packages (python.exe / pythonw.exe)
                               + app-local Microsoft VC++ runtime DLLs (OpenCV / onnxruntime need them)

Every build is its own folder with a unique name (contract §16: never extract over an old one). User data
(projects, database, caches, exports, library) lives OUTSIDE the release folder, by default in
"<parent folder>\\MediaEngine Data", remembered in %LOCALAPPDATA%\\MediaEngine\\data_root.txt, so the next
release sees the same projects and the previous release folder is the rollback.

Model weights are NOT included; the app finds FAST_LOCAL in a neighbouring Archivist install or lets the
user choose the folder (exact hashes verified before use).
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys, sysconfig
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # mediaengine/
PORT = 8775
SHORTCUT = "MediaEngine RC"


def make_icon(dst: Path) -> None:
    """MediaEngine's own simple icon (drawn here, no outside artwork): a play mark on a dark tile with a strip
    of frames. Used by the shortcuts and the installer."""
    from PIL import Image, ImageDraw
    big = 512
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((16, 16, big - 16, big - 16), radius=96, fill=(28, 39, 64, 255))
    for i in range(5):                                  # frame strip along the bottom
        x0 = 72 + i * 76
        d.rounded_rectangle((x0, 388, x0 + 56, 436), radius=10, fill=(255, 166, 43, 255))
    d.polygon([(190, 110), (190, 330), (370, 220)], fill=(255, 255, 255, 255))
    im.save(dst, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)], bitmap_format="bmp")


def version() -> str:
    for line in (ROOT / "app" / "archivist" / "config.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("VERSION = "):
            return line.split('"')[1]
    raise SystemExit("VERSION not found")


def main(out_dir: Path, evidence_dir: Path) -> None:
    if os.name != "nt":
        raise SystemExit("Build on Windows (relocatable CPython is copied from the running interpreter)")
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Build with CPython 3.11 (the pinned 3.12.42 environment)")
    ver = version()
    build = os.environ.get("GITHUB_RUN_NUMBER") or "local"
    name = f"MediaEngine-{ver}-b{build}"
    pkg = out_dir / name
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    # 1. relocatable CPython 3.11 at .venv/Scripts (the launcher looks for .venv\Scripts\pythonw.exe)
    base = Path(sys.base_prefix)
    py_dir = pkg / ".venv" / "Scripts"
    shutil.copytree(base, py_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "Doc", "test", "tests", "idlelib", "turtledemo",
                                                                 "tcl", "tkinter", "Tools", "site-packages"))
    # app-local VC++ runtime: a clean Windows PC without the redistributable cannot load cv2 / onnxruntime
    sysdir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    vc = []
    for dll in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "concrt140.dll"):
        if not (py_dir / dll).exists() and (sysdir / dll).exists():
            shutil.copy2(sysdir / dll, py_dir / dll)
        if (py_dir / dll).exists():
            vc.append(dll)
    (py_dir / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    py = py_dir / "python.exe"
    subprocess.run([str(py), "-m", "ensurepip", "--default-pip"], check=True, capture_output=True)
    subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "-q",
                    "-r", str(ROOT / "requirements.txt")], check=True)

    # 2. app + launcher + markers
    shutil.copytree(ROOT / "app", pkg / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "requirements.txt", pkg / "requirements.txt")
    shutil.copy2(ROOT / "app" / "archivist" / "launcher_v2.py", pkg / "launcher.py")
    # compiled once here: faster first start, and Python never has to write into the release folder later
    # everything, the runtime too: MediaEngine runs with -B (never writes bytecode), so what is not compiled here
    # would be compiled again at every start
    # unchecked-hash: valid whatever timestamps the files get (a ZIP keeps them only to 2 s, which would make every
    # timestamp-checked .pyc stale and Python would compile again at each start); release files never change
    subprocess.run([str(py), "-m", "compileall", "-q", "-f", "-j", "0", "--invalidation-mode", "unchecked-hash",
                    str(pkg / "app"), str(pkg / "launcher.py"), str(pkg / ".venv")], check=False)   # runtime: .venv\\Scripts\\Lib
    (pkg / "version.txt").write_text(ver, encoding="utf-8")
    (pkg / "port.txt").write_text(str(PORT), encoding="utf-8")
    (pkg / "shortcut_name.txt").write_text(SHORTCUT, encoding="utf-8")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.platform_adapter import launcher_vbs_text   # the same file the app repairs at start
    (pkg / "Start MediaEngine.vbs").write_bytes(launcher_vbs_text().encode("utf-16"))   # exact CRLF, same bytes the app checks
    sha = os.environ.get("GITHUB_SHA") or subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    make_icon(pkg / "MediaEngine.ico")
    (pkg / "BUILD.txt").write_text(f"MediaEngine {ver}\ncommit {sha}\nbuilt {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
                                   f"run {os.environ.get('GITHUB_RUN_ID', 'local')}\n", encoding="utf-8")
    (pkg / "README.txt").write_text(f"""MediaEngine {ver} (release candidate)

Installer: run "{name}-Setup.exe" (if Windows SmartScreen warns: "More info" -> "Run anyway"). It installs for
this Windows user only (no administrator rights) into D:\\MediaEngine (if D:\\Archivist exists) or your user folder,
adds "MediaEngine" to the Start menu. Settings -> Apps -> MediaEngine removes all builds installed by Setup
(your projects and exports stay).

ZIP instead: before extracting, right-click the downloaded ZIP -> Properties -> tick "Unblock" -> OK (otherwise
Windows asks about every start). Start: double-click "Start MediaEngine.vbs". A MediaEngine window opens; a desktop shortcut
"{SHORTCUT}" is created for next time. No console, no Python install needed. The first start
can take a minute (Windows checks the new files). "Quit" in the top bar stops MediaEngine.

Your projects, settings and exports are kept OUTSIDE this folder, in "MediaEngine Data" next to it
(the exact place is shown under Settings). Newer build: run its Setup (or extract it next to this one, a new
folder) and start it; it opens the same projects, and if this one is still running it asks to switch. If the new
build has a problem, start the old folder again. Old builds can be removed on "Check this PC". The build number
(e.g. b21) is shown next to the version at the top.

Auto Edit: choose a folder with your videos (or single videos), pick Length / Format / Sound, press
"Create reel". Review the result, Accept it, then Export MP4 (to the Exports folder in "MediaEngine Data",
or "Export to another folder..."). Phone and camera files work: MP4/MOV (also HEVC and HDR), camcorder
MTS/M2TS/MOD/TOD, HDV/DV tape captures, DVD VOB/MPG, older WMV/FLV/3GP, screen and browser recordings
(WebM/MKV, also without a length written in the file). "Check this PC" (button on Home, in
Settings and on Auto Edit) shows what is installed and builds a test reel (also with the AI model).
Language: the "Русский" / "English" button at the top right of every page switches the whole program (also under
Settings -> Interface language). It starts in the language chosen in Setup.
A folder with more than 64 videos (a whole phone) shows its shooting days ("Use this day") and a tick list;
a camera card chosen at its root lists the video folders inside (DCIM, AVCHD ...).

AI model: if this folder sits next to an existing Archivist install (for example D:\\Archivist),
the FAST_LOCAL model is found automatically. Otherwise use "Choose model folder" on the Auto Edit page.
Without the model the app offers the clearly labelled "Technical only" mode.

This candidate runs on port {PORT} and keeps its own data, archive and exports in "MediaEngine Data".
It does not change a stable Archivist install. To remove it: installed with Setup -> Settings -> Apps ->
MediaEngine (all Setup builds; keeps "MediaEngine Data"); from the ZIP -> Quit, delete this folder, the "MediaEngine Data" folder
(your exported videos are inside it) and the "{SHORTCUT}" desktop shortcut.
""", encoding="utf-8")

    (pkg / "ПРОЧТИ.txt").write_text(f"""MediaEngine {ver} — кандидат (тестовая версия)

УСТАНОВКА (проще)
  Запусти "{name}-Setup.exe". Если Windows покажет «Windows защитил ваш компьютер» — нажми
  «Подробнее» → «Выполнить в любом случае». Права администратора не нужны. Программа ставится в
  D:\\MediaEngine (если есть D:\\Archivist) или в папку пользователя, в меню Пуск появится «MediaEngine».
  Удалить: Параметры → Приложения → MediaEngine — удаляет все сборки, поставленные Setup'ом
  (проекты и ролики остаются).

ИЛИ ZIP: ПЕРЕД РАСПАКОВКОЙ
  Правый щелчок по скачанному ZIP → Свойства → галочка «Разблокировать» → ОК. Иначе Windows будет
  спрашивать разрешение при каждом запуске. Если всё же спросит — нажми «Открыть» / «Выполнить».

ЗАПУСК
  Дважды щёлкни "Start MediaEngine.vbs". Откроется окно MediaEngine. На рабочем столе появится
  ярлык "{SHORTCUT}" — дальше запускай с него. Первый запуск может занять минуту.
  Python, консоль и браузер отдельно не нужны. Закрыть программу: кнопка «Выход» (Quit) вверху.

РОЛИК ИЗ СВОИХ ВИДЕО (Автомонтаж)
  1. Автомонтаж → «Выбрать папку…» (папка с видео) или «Выбрать видео…» (отдельные файлы).
  2. Выбери длину, формат и звук → «Создать ролик».
  3. Посмотри результат. Можно убрать, заменить, обрезать, переставить моменты — каждая правка
     сохраняется как новая версия, старые не теряются.
  4. «Принять эту версию» → «Экспорт MP4» (или «Экспорт в другую папку…»). Папку с готовыми роликами
     открывает кнопка «Готовые ролики» вверху страницы автомонтажа.
  (В английском интерфейсе: Auto Edit → Choose folder… → Create reel → Accept → Export MP4.)
  Оригиналы только читаются и никогда не меняются.
  Папка, где больше 64 видео (весь телефон): программа покажет дни съёмки — «Взять этот день» —
  или список, где можно отметить нужные видео (до 64 в одном ролике). Карту памяти камеры можно
  выбрать целиком: программа покажет папки с видео внутри (DCIM, AVCHD…).
  Подходят видео с телефона и камер: MP4/MOV (в том числе HEVC и HDR), MTS/M2TS/MOD/TOD с видеокамер,
  оцифровки кассет HDV/DV, DVD (VOB/MPG), старые WMV/FLV/3GP, записи экрана и из браузера (WebM/MKV,
  даже если в файле не записана длина).

ЯЗЫК
  Кнопка "Русский" / "English" справа вверху на любой странице переключает всю программу
  (то же — в Настройках → Язык интерфейса). Язык, выбранный в Setup, сразу становится языком программы.

ПРОВЕРКА КОМПЬЮТЕРА
  Кнопка "Проверка компьютера" (Check this PC) — на главной, в Настройках и на странице автомонтажа:
  видно, найдена ли ИИ-модель, работают ли библиотеки, сколько места на диске, и можно собрать тестовый
  ролик из сгенерированных клипов (твои видео не трогает), в том числе с ИИ-моделью — так видно, что
  ИИ-режим работает на этом компьютере.

ИИ-МОДЕЛЬ
  Если рядом стоит рабочий Archivist (например D:\\Archivist), модель найдётся сама.
  Без модели работает только режим «Только техника» (Technical only: резкость, движение, свет) —
  его надо выбрать явно галочкой.
  ИИ+ (по желанию): модель сильнее (PE-Core L/14), лучше понимает людей, места и события. Скачивается
  один раз на странице «Проверка компьютера» → «Скачать модель ИИ+» (около 650 МБ, бесплатно, каждый
  файл проверяется), дальше работает без интернета. Первый анализ новых видео дольше. При создании
  ролика выбери «ИИ+», сравни с обычным ИИ кнопкой «Сравнить вслепую».

ГДЕ МОИ ДАННЫЕ
  Проекты, настройки и экспорт лежат НЕ в этой папке, а в папке "MediaEngine Data" рядом с ней.
  Точное место видно в Настройках (Settings).

НОВАЯ ВЕРСИЯ / ОТКАТ
  Новую версию поставь её Setup'ом (или распакуй ZIP в новую папку рядом, не поверх старой) и запусти —
  она откроет те же проекты. Если старая ещё запущена, MediaEngine спросит, переключиться ли на новую.
  Если с новой что-то не так: «Выход» и запусти "Start MediaEngine.vbs" из старой папки. Ненужные старые
  версии можно удалить на странице «Проверка компьютера» (проекты и ролики не трогаются).
  Номер сборки (например b21) виден вверху рядом с версией.

РЯДОМ С РАБОЧИМ ARCHIVIST
  Эта версия работает на своём порту ({PORT}), со своим ярлыком и своими данными. Рабочий
  Archivist (D:\\Archivist) она не меняет.

УДАЛИТЬ
  Ставил Setup'ом: Параметры → Приложения → MediaEngine (папка "MediaEngine Data" остаётся).
  Из ZIP: «Выход» (Quit) → удали эту папку, папку "MediaEngine Data" (в ней и экспортированные ролики) и ярлык
  "{SHORTCUT}".
""", encoding="utf-8-sig")

    # 3. manifest (outside the package folder: evidence, not user-facing)
    files = []
    for p in sorted(pkg.rglob("*")):
        if p.is_file() and ".venv" not in p.relative_to(pkg).parts:
            files.append({"path": str(p.relative_to(pkg)).replace("\\", "/"), "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    venv_bytes = sum(p.stat().st_size for p in (pkg / ".venv").rglob("*") if p.is_file())
    frozen = subprocess.run([str(py), "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    manifest = {"product": "MediaEngine", "version": ver, "commit": sha, "port": PORT, "shortcut": SHORTCUT, "python": sys.version.split()[0],
                "python_source": str(base), "vc_runtime_app_local": vc, "packages": frozen, "app_files": files, "venv_bytes": venv_bytes}
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / f"{name}.manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as fh:
            fh.write(f"PKG_NAME={name}\nPKG_VERSION={ver}\n")
    print(json.dumps({"package": str(pkg), "name": name, "version": ver, "app_files": len(files), "venv_mb": round(venv_bytes / 1e6, 1)}))


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve()
    main(out, Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else out.parent / (out.name + "-evidence"))
