"""Hidden Windows launcher for the local studio (not a standalone installer)."""
import argparse
import ctypes
import json
import msvcrt
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.clippa-data' / 'desktop'
URL = 'http://127.0.0.1:4322/'
HIDDEN = subprocess.CREATE_NO_WINDOW


def healthy():
    try:
        with urllib.request.urlopen(URL + 'api/health', timeout=2) as response:
            return json.load(response).get('service') == 'clippa-python'
    except Exception:
        return False


def occupied(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0


def open_studio():
    candidates = [Path(os.environ.get(env, 'C:/')) / suffix
                  for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA')
                  for suffix in ('Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe')]
    browser = next((path for path in candidates if path.is_file()), None)
    if browser:
        subprocess.Popen([str(browser), '--app=' + URL], creationflags=HIDDEN)
    else:
        webbrowser.open(URL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    stop = RUNTIME / 'stop.request'
    if args.stop:
        stop.touch()
        return
    lock = (RUNTIME / 'launcher.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0')
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        for _ in range(90):
            if healthy():
                if not args.no_browser:
                    open_studio()
                return
            time.sleep(1)
        raise RuntimeError('Clippa no ha terminado de arrancar. Revisa .clippa-data/desktop/studio.log.')
    children = []
    stop.unlink(missing_ok=True)
    try:
        if healthy():
            if not args.no_browser:
                open_studio()
            return
        if occupied(4322) or occupied(4323):
            raise RuntimeError('Los puertos 4322 o 4323 están ocupados por otro proceso. Cierra el arranque anterior de Clippa y vuelve a abrir el acceso directo.')
        py = ROOT / '.venv/Scripts/python.exe'
        node = shutil.which('node')
        if not py.is_file() or not node or not (ROOT / 'dist/index.html').is_file():
            raise RuntimeError('Faltan componentes de Clippa. Revisa la instalación y ejecuta npm run build en la carpeta del proyecto.')
        package = json.loads((ROOT / 'node_modules/astro/package.json').read_text(encoding='utf8'))
        binary = package['bin'] if isinstance(package['bin'], str) else package['bin']['astro']
        commands = [
            [str(py), '-m', 'uvicorn', 'engine.api:app', '--host', '127.0.0.1', '--port', '4323'],
            [str(py), '-m', 'engine.worker'],
            [node, str(ROOT / 'node_modules/astro' / binary), 'preview', '--host', '127.0.0.1', '--port', '4322'],
        ]
        with (RUNTIME / 'studio.log').open('ab') as log:
            env = dict(os.environ, ASTRO_TELEMETRY_DISABLED='1', ASTRO_DEV_BACKGROUND='0', ASTRO_PREVIEW_BACKGROUND='0', PYTHONUNBUFFERED='1')
            for command in commands:
                children.append(subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                                  stdout=log, stderr=log, creationflags=HIDDEN))
            for _ in range(90):
                if any(child.poll() is not None for child in children):
                    raise RuntimeError('Un componente no ha podido arrancar. Revisa .clippa-data/desktop/studio.log.')
                if healthy():
                    break
                if stop.exists():
                    return
                time.sleep(1)
            else:
                raise RuntimeError('Clippa tarda demasiado en iniciar. Revisa .clippa-data/desktop/studio.log.')
            if not args.no_browser:
                open_studio()
            while not stop.exists():
                if any(child.poll() is not None for child in children):
                    raise RuntimeError('El motor se ha detenido. Cierra Clippa y vuelve a abrir el acceso directo.')
                time.sleep(1)
    finally:
        # Stop only the process trees started by this launcher.
        for child in reversed(children):
            if child.poll() is None:
                subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=HIDDEN)
                child.wait(timeout=15)
        stop.unlink(missing_ok=True)
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        (RUNTIME / 'last-error.txt').write_text(str(exc), encoding='utf8')
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'Clippa · No se pudo iniciar', 0x10)
        sys.exit(1)
