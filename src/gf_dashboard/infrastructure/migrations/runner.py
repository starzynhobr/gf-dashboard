from __future__ import annotations

from importlib.resources import files

from gf_dashboard.infrastructure.persistence import Migration


def load_migrations() -> tuple[Migration, ...]:
    package = files("gf_dashboard.infrastructure.migrations")
    migration_files = sorted(
        (entry for entry in package.iterdir() if entry.name.endswith(".sql")),
        key=lambda entry: entry.name,
    )
    migrations: list[Migration] = []
    for entry in migration_files:
        version_text, name_with_extension = entry.name.split("_", maxsplit=1)
        migrations.append(
            Migration(
                version=int(version_text),
                name=name_with_extension.removesuffix(".sql"),
                sql=entry.read_text(encoding="utf-8"),
            )
        )
    return tuple(migrations)
