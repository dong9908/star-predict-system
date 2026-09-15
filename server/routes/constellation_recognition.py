from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
import logging

from services.constellation_recognition import recognize


logger = logging.getLogger(__name__)

constellation_recognition_router = APIRouter()
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png"}


@constellation_recognition_router.post("/recognize")
async def recognize_constellation(image: UploadFile = File(...)):
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="JPG 또는 PNG 이미지만 업로드할 수 있습니다.",
        )

    content = await image.read(MAX_IMAGE_BYTES + 1)

    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="이미지 크기는 최대 10MB입니다.",
        )

    try:
        suffix = ".png" if image.content_type == "image/png" else ".jpg"

        return await run_in_threadpool(
            recognize,
            content,
            suffix=suffix,
            filename=image.filename or "",
        )

    except ValueError as exc:
        logger.warning(
            "별자리 이미지 분석 입력 오류: filename=%s, error=%s",
            image.filename,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except FileNotFoundError as exc:
        logger.error(
            "별자리 이미지 분석에 필요한 파일을 찾을 수 없음: filename=%s, error=%s",
            image.filename,
            exc,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception:
        logger.exception(
            "별자리 이미지 분석 중 예상하지 못한 오류: filename=%s",
            image.filename,
        )
        raise HTTPException(
            status_code=500,
            detail="이미지 분석 중 오류가 발생했습니다.",
        ) from None