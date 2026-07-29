from __future__ import annotations

import io
import zipfile
from pathlib import Path
from uuid import UUID

import httpx
import structlog
from app.config import GradingSettings

log = structlog.get_logger("grading.pack_materialize")


async def ensure_local_pack_root(
    client: httpx.AsyncClient,
    settings: GradingSettings,
    *,
    user_id: UUID,
    pack_id: UUID,
    version: str,
    disk_path: Path,
    object_key: str | None,
) -> str:
                                                                                    
    if disk_path.is_dir():  # noqa: ASYNC240 — sync existence check before download
        return str(disk_path)
    if not object_key or not settings.media_service_url:
        raise RuntimeError(f"pack root missing on disk: {disk_path}")

    safe_version = version.replace("/", "_").replace("..", "_")
    asset_id = f"packs/{pack_id}/{safe_version}/archive.zip"
    target = Path(settings.packs_root) / str(user_id) / str(pack_id) / safe_version
    if target.is_dir() and any(target.iterdir()):  # noqa: ASYNC240
        return str(target)

    response = await client.get(
        f"{settings.media_service_url}/internal/v1/media/{asset_id}",
        headers={"X-User-Id": str(user_id)},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.content
    if not payload:
        raise RuntimeError("empty pack archive from media")

    staging = target.parent / f".hydrate-{safe_version}"
    if staging.exists():
        _rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            archive.extractall(staging)
        if target.exists():
            _rmtree(target)
        staging.rename(target)
    except (OSError, zipfile.BadZipFile) as exc:
        _rmtree(staging)
        log.warning("pack_hydrate_failed", pack_id=str(pack_id), error=str(exc))
        raise RuntimeError("failed to hydrate pack from media") from exc

    return str(target)


def _rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)
