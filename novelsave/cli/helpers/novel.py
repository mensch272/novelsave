import os
import sys
from typing import Optional

from dependency_injector.wiring import inject, Provide
from loguru import logger

from novelsave.cli.helpers.source import get_source_gateway
from novelsave.containers import Application
from novelsave.core.entities.novel import Novel
from novelsave.services import NovelService
from novelsave.utils.adapters import DTOAdapter
from novelsave.utils.concurrent import ConcurrentActionsController


@inject
def create_novel(
        url: str,
        novel_service: NovelService = Provide[Application.services.novel_service],
) -> Novel:
    """
    retrieve information about the novel from webpage and insert novel into database.
    this includes chapter list and metadata.
    """
    source_gateway = get_source_gateway(url)

    logger.info(f'Retrieving novel (url={url})...')
    novel_dto, chapter_dtos, metadata_dtos = source_gateway.novel_by_url(url)

    novel = novel_service.insert_novel(novel_dto)
    novel_service.insert_chapters(novel, chapter_dtos)
    novel_service.insert_metadata(novel, metadata_dtos)

    logger.info(f'New novel (id={novel.id}, title={novel.title}, chapters={len(chapter_dtos)})')
    return novel


@inject
def update_novel(
        novel: Novel,
        novel_service: NovelService = Provide[Application.services.novel_service],
):
    url = novel_service.get_url(novel)
    logger.debug(f'Using (url={url})')

    source_gateway = get_source_gateway(url)

    logger.info(f'Retrieving novel (url={url})...')
    novel_dto, chapter_dtos, metadata_dtos = source_gateway.novel_by_url(url)

    novel_service.update_novel(novel, novel_dto)
    novel_service.update_chapters(novel, chapter_dtos)
    novel_service.update_metadata(novel, metadata_dtos)

    logger.info(f'Updated novel (id={novel.id}, title={novel.title}, chapters={len(chapter_dtos)})')
    return novel


@inject
def download_pending(
        novel: Novel,
        limit: int,
        novel_service: NovelService = Provide[Application.services.novel_service],
        dto_adapter: DTOAdapter = Provide[Application.adapters.dto_adapter],
):
    chapters = novel_service.get_pending_chapters(novel, limit)
    if not chapters:
        logger.error(f'Novel (title={novel.title}) has no pending chapters.')

    url = novel_service.get_url(novel)
    logger.debug(f'Using (url={url})')

    source_gateway = get_source_gateway(url)

    # setup controller
    controller = ConcurrentActionsController(min(os.cpu_count(), len(chapters)), source_gateway.update_chapter_content)
    for chapter in chapters:
        controller.add(dto_adapter.chapter_to_dto(chapter))

    logger.info(f'Downloading pending chapters (count={len(chapters)}, threads={len(controller.threads)})...')
    for chapter_dto in controller.iter():
        novel_service.update_content(chapter_dto)

    logger.info(f'Download complete.')


@inject
def get_novel(
        id_or_url: str,
        novel_service: NovelService = Provide[Application.services.novel_service],
) -> Optional[Novel]:
    """retrieve novel is it exists in the database otherwise return none"""
    is_url = id_or_url.startswith("http")
    if is_url:
        novel = novel_service.get_novel_by_url(id_or_url)
    else:
        try:
            novel = novel_service.get_novel_by_id(int(id_or_url))
        except ValueError:
            logger.error(f'Value provided ({id_or_url}) is neither a url or an id.')
            sys.exit(1)

    if not novel:
        logger.error(f'Novel ({"url" if is_url else "id"}={id_or_url}) not found.')

    return novel


@inject
def get_or_create_novel(
        id_or_url: str,
) -> Novel:
    """retrieve specified novel from database or web-crawl and create the novel"""
    novel = get_novel(id_or_url)

    if novel is None:
        if not id_or_url.startswith("http"):
            sys.exit(1)

        novel = create_novel(id_or_url)

    return novel
