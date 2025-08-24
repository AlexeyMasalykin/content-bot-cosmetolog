# utils/vk_utils.py
import requests
import io
import time
import logging
from typing import Optional, Dict, Any
from config import VK_ACCESS_TOKEN, VK_GROUP_ID, VK_API_VERSION

VK_API = "https://api.vk.com/method"
HTTP_TIMEOUT = 30
log = logging.getLogger("tg-vk-bot")


class VkApiError(RuntimeError):
    pass


class VKPublisher:
    def __init__(self, vk_api_key: str, group_id: str):
        self.vk_api_key = vk_api_key
        self.group_id = group_id

    def _vk_call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        max_retries: int = 4,
    ) -> Dict[str, Any]:
        """
        Вызов метода VK API с базовой retry-логикой.
        """
        if params is None:
            params = {}
        params.setdefault("access_token", self.vk_api_key)
        params.setdefault("v", VK_API_VERSION)

        attempt = 0
        while True:
            attempt += 1
            try:
                # Для методов с длинным текстом используем POST data вместо params
                if method == "wall.post" and "message" in params:
                    # Отправляем данные в теле запроса для избежания 414 ошибки
                    r = requests.post(f"{VK_API}/{method}", data=params, files=files, timeout=HTTP_TIMEOUT)
                    log.info(f"VK API {method} using POST data (text length: {len(params.get('message', ''))})")
                else:
                    # Для остальных методов используем обычные параметры
                    r = requests.post(f"{VK_API}/{method}", params=params, files=files, timeout=HTTP_TIMEOUT)
                log.info(f"VK API {method} response status: {r.status_code}")
                log.info(f"VK API {method} response text (first 200 chars): {r.text[:200]}")

                if not r.text.strip():
                    log.error(f"VK API {method} returned empty response")
                    if attempt < max_retries:
                        time.sleep(0.8 * attempt)
                        continue
                    raise VkApiError(f"VK API returned empty response for {method}")

                data = r.json()
            except requests.exceptions.JSONDecodeError as e:
                log.error(f"VK API {method} JSON decode error. Response: {r.text[:500]}")
                if attempt < max_retries:
                    time.sleep(0.8 * attempt)
                    continue
                raise VkApiError(f"VK API вернул некорректный JSON для {method}: {e}") from e
            except Exception as e:
                log.error(f"VK API {method} request failed: {e}")
                if attempt < max_retries:
                    time.sleep(0.8 * attempt)
                    continue
                raise VkApiError(f"VK API запрос не удался: {e}") from e

            err = data.get("error")
            if not err:
                return data

            code = err.get("error_code")
            msg = err.get("error_msg", "Unknown VK error")
            if code == 6 and attempt < max_retries:  # Too many requests
                time.sleep(0.7 * attempt)
                continue
            raise VkApiError(f"VK API error {code}: {msg}")

    def upload_photo(self, image_url: Optional[str] = None, image_bytes: Optional[bytes] = None) -> str:
        """
        Загружает фото в альбом группы и возвращает attachment id.
        Можно передать либо URL, либо байты изображения.
        """
        # 1. Получить upload_url
        try:
            upload_url_resp = self._vk_call("photos.getWallUploadServer", params={"group_id": self.group_id})
            upload_url = upload_url_resp["response"]["upload_url"]
            log.info(f"VK upload URL obtained: {upload_url[:50]}...")
        except Exception as e:
            raise VkApiError(f"Failed to get VK upload URL: {e}")

        # 2. Скачать или использовать готовое изображение
        if image_url:
            image_data = requests.get(image_url, timeout=HTTP_TIMEOUT).content
        elif image_bytes:
            image_data = image_bytes
        else:
            raise ValueError("Не передано изображение для загрузки")

        # Проверяем размер изображения
        if len(image_data) == 0:
            raise VkApiError("Image data is empty")
        if len(image_data) > 50 * 1024 * 1024:  # 50MB limit
            raise VkApiError(f"Image too large: {len(image_data)} bytes")

        log.info(f"VK image size: {len(image_data)} bytes")

        # 3. Загрузить на сервер VK
        try:
            upload_response = requests.post(
                upload_url, files={"photo": ("image.jpg", io.BytesIO(image_data), "image/jpeg")}, timeout=HTTP_TIMEOUT
            ).json()

            # Проверяем ответ загрузки
            if "photo" not in upload_response or not upload_response["photo"]:
                raise VkApiError(f"VK upload failed: {upload_response}")

            log.info(f"VK upload successful: {upload_response.keys()}")

        except requests.exceptions.RequestException as e:
            raise VkApiError(f"VK upload request failed: {e}")
        except ValueError as e:
            raise VkApiError(f"VK upload response not JSON: {e}")

        # 4. Сохранить фото
        save_response = self._vk_call(
            "photos.saveWallPhoto",
            params={
                "group_id": self.group_id,
                "photo": upload_response["photo"],
                "server": upload_response["server"],
                "hash": upload_response["hash"],
            },
        )

        ph = save_response["response"][0]
        return f"photo{ph['owner_id']}_{ph['id']}"

    def publish_post(self, content: str, image_url: Optional[str] = None, image_bytes: Optional[bytes] = None) -> Dict:
        """
        Публикация поста в VK с текстом и опционально картинкой.
        """
        params = {"from_group": 1, "owner_id": f"-{self.group_id}", "message": content}
        if image_url or image_bytes:
            attachment = self.upload_photo(image_url=image_url, image_bytes=image_bytes)
            params["attachments"] = attachment

        return self._vk_call("wall.post", params=params)

    @staticmethod
    def post_url(group_id: str, post_id: int) -> str:
        return f"https://vk.com/wall-{group_id}_{post_id}"


# Глобальный экземпляр для использования в коде
vk_publisher = VKPublisher(VK_ACCESS_TOKEN, VK_GROUP_ID)


# Старые функции-обёртки для совместимости с уже существующим кодом
def vk_publish_text(group_id: str, text: str) -> int:
    resp = vk_publisher.publish_post(text)
    return int(resp["response"]["post_id"])


def vk_publish_photo_and_text(group_id: str, image_bytes: bytes, text: str) -> int:
    resp = vk_publisher.publish_post(text, image_bytes=image_bytes)
    return int(resp["response"]["post_id"])


def vk_post_url(group_id: str, post_id: int) -> str:
    return VKPublisher.post_url(group_id, post_id)


def vk_publish_with_image_required(group_id: str, image_bytes: bytes, text: str) -> int:
    """
    Публикует пост с изображением в VK с гарантией наличия картинки.
    Пробует разные стратегии, но всегда с картинкой.
    """

    # Стратегия 1: Обычная публикация с картинкой
    try:
        log.info("VK Strategy 1: Normal photo+text post")
        resp = vk_publisher.publish_post(text, image_bytes=image_bytes)
        post_id = int(resp["response"]["post_id"])
        log.info(f"VK Strategy 1 success: post_id={post_id}")
        return post_id
    except Exception as e:
        log.warning(f"VK Strategy 1 failed: {e}")

    # Стратегия 2: Сначала загружаем картинку, потом публикуем
    try:
        log.info("VK Strategy 2: Upload image first, then post")
        attachment = vk_publisher.upload_photo(image_bytes=image_bytes)
        resp = vk_publisher._vk_call(
            "wall.post", params={"owner_id": f"-{group_id}", "message": text, "attachments": attachment}
        )
        post_id = int(resp["response"]["post_id"])
        log.info(f"VK Strategy 2 success: post_id={post_id}")
        return post_id
    except Exception as e:
        log.warning(f"VK Strategy 2 failed: {e}")

    # Стратегия 3: Минимальный текст с картинкой
    try:
        log.info("VK Strategy 3: Minimal text with image")
        # Импортируем здесь, чтобы избежать циклического импорта
        import re

        clean_text = re.sub(r"[^\w\s\.\,\!\?\-\n]", "", text)  # Убираем спецсимволы
        short_text = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
        resp = vk_publisher.publish_post(short_text, image_bytes=image_bytes)
        post_id = int(resp["response"]["post_id"])
        log.info(f"VK Strategy 3 success: post_id={post_id}")
        return post_id
    except Exception as e:
        log.warning(f"VK Strategy 3 failed: {e}")

    # Стратегия 4: Только картинка с минимальным текстом
    try:
        log.info("VK Strategy 4: Image with minimal text")
        minimal_text = "Новый пост"
        resp = vk_publisher.publish_post(minimal_text, image_bytes=image_bytes)
        post_id = int(resp["response"]["post_id"])
        log.info(f"VK Strategy 4 success: post_id={post_id}")
        return post_id
    except Exception as e:
        log.warning(f"VK Strategy 4 failed: {e}")

    # Если все стратегии не сработали
    raise VkApiError("Не удалось опубликовать пост с картинкой ни одним способом")
