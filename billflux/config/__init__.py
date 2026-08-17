"""Module inicialization file config"""

from pathlib import Path

from dynaconf import Dynaconf

ROOT_PATH = Path(__file__).resolve().parent.parent.parent

settings = Dynaconf(
    envvar_prefix="BillFlux",
    root_path=str(ROOT_PATH),
    settings_files=["settings.toml"],
)
