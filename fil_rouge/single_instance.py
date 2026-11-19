"""Utilitaires pour garantir une seule instance Streamlit par application.

- Tue les instances Streamlit existantes de la même appli (même script).
- Si lancé via `python <app>.py`, relance automatiquement via `streamlit run`
  après nettoyage (permet de redémarrer proprement même si le port était occupé).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Iterable, List, Optional


def _ps_quote(value: str) -> str:
    """Échappe une chaîne pour PowerShell (single-quoted)."""
    return "'" + value.replace("'", "''") + "'"


def _is_windows() -> bool:
    return os.name == "nt"


def _run_powershell(script: str, timeout: int = 20) -> None:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        # Best-effort : ne jamais bloquer le démarrage de l'appli
        pass


def kill_streamlit_instances(script_path: str, *, exclude_pid: Optional[int] = None) -> None:
    """Tue les processus `streamlit run` qui exécutent le même script (basename)."""
    if not _is_windows():
        return

    script_path = os.path.abspath(script_path)
    name = os.path.basename(script_path)
    me = os.getpid() if exclude_pid is None else int(exclude_pid)

    ps = (
        "$me = {me}; $name = {name}; "
        "Get-CimInstance Win32_Process | "
        "Where-Object {{ "
        "$_.ProcessId -ne $me "
        "-and $_.CommandLine "
        "-and ($_.CommandLine -match 'streamlit') "
        "-and ($_.CommandLine -match 'run') "
        "-and ($_.CommandLine -match $name) "
        "}} | ForEach-Object {{ "
        "try {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop }} catch {{}} "
        "}}"
    ).format(me=me, name=_ps_quote(name))

    _run_powershell(ps)


def kill_all_streamlit(*, exclude_pid: Optional[int] = None) -> None:
    """Tue tous les serveurs Streamlit (`streamlit run`)."""
    if not _is_windows():
        return

    me = os.getpid() if exclude_pid is None else int(exclude_pid)
    ps = (
        "$me = {me}; "
        "Get-CimInstance Win32_Process | "
        "Where-Object {{ "
        "$_.ProcessId -ne $me "
        "-and $_.CommandLine "
        "-and ($_.CommandLine -match 'streamlit') "
        "-and ($_.CommandLine -match 'run') "
        "}} | ForEach-Object {{ "
        "try {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop }} catch {{}} "
        "}}"
    ).format(me=me)

    _run_powershell(ps)


def _in_streamlit_runtime() -> bool:
    """Retourne True si le script s'exécute dans le runtime Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore

        return get_script_run_ctx() is not None
    except Exception:
        pass
    # Fallback heuristique
    return "streamlit.runtime" in sys.modules or os.environ.get("STREAMLIT_RUNTIME") == "1"


def bootstrap_streamlit_app(
    script_path: str,
    *,
    port: int = 8501,
    extra_args: Optional[Iterable[str]] = None,
) -> None:
    """Garantit une instance unique pour ce script.

    - Tue les autres instances de la même appli.
    - Si exécuté hors runtime Streamlit (ex: `python app.py`), relance via
      `python -m streamlit run ...` puis quitte le processus courant.
    - Si exécuté dans Streamlit, ne relance pas (évite les boucles) mais a déjà nettoyé.
    """
    if os.environ.get("AWP_NO_BOOTSTRAP") == "1":
        return

    script_path = os.path.abspath(script_path)
    guard_key = f"_STREAMLIT_SINGLETON_BOOTSTRAPPED::{script_path}"
    if os.environ.get(guard_key) == str(os.getpid()):
        return
    os.environ[guard_key] = str(os.getpid())

    # Nettoyage des instances similaires puis courte pause pour libérer le port
    try:
        kill_streamlit_instances(script_path)
    except Exception:
        pass
    time.sleep(0.8)

    # Déjà dans Streamlit -> continuer normalement
    if _in_streamlit_runtime():
        return

    # Arguments à transmettre au relancement (par défaut: argv utilisateur)
    if extra_args is None:
        extra_args = sys.argv[1:]
    args_list = list(extra_args)

    # Hors runtime Streamlit -> (re)lancer proprement via streamlit run
    cmd: List[str] = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        script_path,
    ]
    cmd.extend(args_list)

    # Forcer un port si non fourni, pour permettre le redémarrage sur le même port
    has_port = any(a == "--server.port" or a.startswith("--server.port=") for a in args_list)
    if not has_port:
        cmd.extend(["--server.port", str(int(port))])

    # Remplacer le processus courant si possible, sinon lancer puis sortir
    try:
        if os.name == "nt":
            # subprocess + exit est plus fiable que execv sur Windows
            rc = subprocess.call(cmd)
            raise SystemExit(rc)
        else:
            os.execv(cmd[0], cmd)
    except SystemExit:
        raise
    except Exception:
        # Dernier recours : tenter un lancement détaché
        try:
            subprocess.Popen(cmd)
        except Exception:
            pass
        raise SystemExit(0)
