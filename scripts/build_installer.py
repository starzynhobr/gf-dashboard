"""Automação completa do processo de build e geração do instalador Windows do GF Farmer.

Executa:
1. Build do frontend React (npm run build)
2. Geração do ícone (.ico) se necessário
3. Compilação do executável com PyInstaller
4. Compilação do instalador .exe com Inno Setup (ISCC.exe)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_iscc() -> Path:
    """Localiza o compilador ISCC.exe do Inno Setup no sistema."""
    iscc_in_path = shutil.which("iscc")
    if iscc_in_path:
        return Path(iscc_in_path)

    prog_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    prog_64 = os.environ.get("PROGRAMFILES", r"C:\Program Files")

    standard_paths = [
        Path(prog_x86) / "Inno Setup 6" / "ISCC.exe",
        Path(prog_64) / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]

    for candidate in standard_paths:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "Compilador do Inno Setup (ISCC.exe) não encontrado no PATH nem nos diretórios padrão. "
        "Verifique se o Inno Setup 6 está instalado."
    )


def step(message: str) -> None:
    print(f"\n{'=' * 70}\n[BUILD] {message}\n{'=' * 70}")


def get_release_version() -> str:
    """Verifica e retorna a versão comum do projeto, frontend e instalador."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        backend_version = tomllib.load(project_file)["project"]["version"]
    with (PROJECT_ROOT / "frontend" / "package.json").open(encoding="utf-8") as package_file:
        frontend_version = json.load(package_file)["version"]
    init_source = (PROJECT_ROOT / "src" / "gf_dashboard" / "__init__.py").read_text(
        encoding="utf-8"
    )
    init_match = re.search(r'^__version__ = ["\']([^"\']+)["\']$', init_source, re.MULTILINE)
    setup_source = (PROJECT_ROOT / "installer" / "setup.iss").read_text(encoding="utf-8")
    setup_match = re.search(r'^#define MyAppVersion "([^"]+)"$', setup_source, re.MULTILINE)
    versions = {"pyproject.toml": backend_version, "frontend/package.json": frontend_version}
    if init_match is None or setup_match is None:
        raise SystemExit("Não foi possível ler a versão do backend ou do instalador.")
    versions["gf_dashboard.__version__"] = init_match.group(1)
    versions["installer/setup.iss"] = setup_match.group(1)
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{name}={version}" for name, version in versions.items())
        raise SystemExit(f"Versões divergentes; atualize todas antes de gerar o pacote: {details}")
    return backend_version


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    display_cmd = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    print(f">> Executando: {display_cmd}")
    result = subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT))
    if result.returncode != 0:
        raise SystemExit(f"Comando falhou com código {result.returncode}: {display_cmd}")


def generate_icon_if_needed(ico_path: Path) -> None:
    if ico_path.is_file():
        return
    generate_script = (
        "from pathlib import Path, sys\n"
        "from PySide6.QtCore import Qt\n"
        "from PySide6.QtGui import QGuiApplication, QImage\n"
        "root = Path('.').resolve()\n"
        "app = QGuiApplication(sys.argv[:1])\n"
        "img = QImage(str(root / 'frontend' / 'src' / 'assets' / 'gf-farmer-mark.png'))\n"
        "scaled = img.scaled(\n"
        "    256, 256, Qt.AspectRatioMode.KeepAspectRatio, "
        "Qt.TransformationMode.SmoothTransformation\n"
        ")\n"
        "out = root / 'build_assets' / 'app_icon.ico'\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "scaled.save(str(out), 'ICO')\n"
    )
    run_command(["uv", "run", "--no-sync", "python", "-c", generate_script])


def main() -> None:
    version = get_release_version()
    step(f"Versão selecionada: {version}")
    step("1/4: Compilando frontend React com Vite")
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    run_command([npm_cmd, "--prefix", "frontend", "run", "build"])

    step("2/4: Verificando/gerando build_assets/app_icon.ico")
    ico_path = PROJECT_ROOT / "build_assets" / "app_icon.ico"
    generate_icon_if_needed(ico_path)
    print(f"Ícone OK: {ico_path} ({ico_path.stat().st_size:,} bytes)")

    step("3/4: Empacotando aplicação desktop com PyInstaller")
    run_command(["uv", "run", "--no-sync", "pyinstaller", "gf_farmer.spec", "--clean", "-y"])

    bundled_exe = PROJECT_ROOT / "dist" / "GF Farmer" / "GF Farmer.exe"
    if not bundled_exe.is_file():
        raise SystemExit(f"Executável empacotado não encontrado em: {bundled_exe}")
    print(f"Executável compilado: {bundled_exe}")
    step("Verificando inicialização real do executável empacotado")
    # Importa todo o bootstrap congelado, incluindo QtCore, sem abrir o banco pessoal.
    smoke = subprocess.run([str(bundled_exe), "--packaging-smoke"], timeout=30, cwd=PROJECT_ROOT)
    if smoke.returncode != 0:
        raise SystemExit(
            f"O executável empacotado falhou ao iniciar (código {smoke.returncode}); "
            "instalador não gerado."
        )
    print("Inicialização do pacote: OK")

    step("4/4: Gerando instalador Windows com Inno Setup")
    iscc_path = find_iscc()
    iss_script = PROJECT_ROOT / "installer" / "setup.iss"
    print(f"Usando Inno Setup: {iscc_path}")
    print(f"Script: {iss_script}")
    run_command([str(iscc_path), str(iss_script)])

    installer_output = PROJECT_ROOT / "dist" / "installer" / f"GF_Farmer_Setup_v{version}.exe"
    if not installer_output.is_file():
        raise SystemExit(f"Instalador final não encontrado em: {installer_output}")

    size_mb = installer_output.stat().st_size / (1024 * 1024)
    step("SUCESSO: Instalador do GF Farmer gerado com sucesso!")
    print(f"Local do Instalador: {installer_output}")
    print(f"Tamanho: {size_mb:.2f} MB\n")


if __name__ == "__main__":
    main()
