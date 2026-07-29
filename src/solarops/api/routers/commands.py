from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from solarops.api.dependencies import get_composition
from solarops.api.schemas.audit import AuditEntryResponse
from solarops.api.schemas.command import CommandDetailResponse, CommandSummaryResponse
from solarops.platform.api_composition import SystemComposition
from solarops.shared_kernel import CommandId, SiteId

router = APIRouter(tags=["commands"])


@router.get("/sites/{site_id}/commands", response_model=list[CommandSummaryResponse])
def list_commands(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> list[CommandSummaryResponse]:
    commands = composition.command_repository.list_by_site(SiteId(site_id))
    return [CommandSummaryResponse.from_domain(c) for c in commands]


@router.get("/commands/{command_id}", response_model=CommandDetailResponse)
def get_command(
    command_id: str, composition: SystemComposition = Depends(get_composition)
) -> CommandDetailResponse:
    command = composition.command_repository.get(CommandId(command_id))
    if command is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no command {command_id!r}")
    return CommandDetailResponse.from_domain(command)


@router.get("/commands/{command_id}/audit", response_model=list[AuditEntryResponse])
def get_command_audit(
    command_id: str, composition: SystemComposition = Depends(get_composition)
) -> list[AuditEntryResponse]:
    if composition.command_repository.get(CommandId(command_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no command {command_id!r}")
    entries = composition.audit_log.for_aggregate(command_id)
    return [AuditEntryResponse.from_domain(e) for e in entries]
