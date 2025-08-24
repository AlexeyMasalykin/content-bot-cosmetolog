import time
from yandex_cloud_ml_sdk import YCloudML
from config import YANDEX_API_KEY, YANDEX_FOLDER_ID

def generate_image_bytes_with_yc(prompt: str) -> bytes:
    sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)
    model = sdk.models.image_generation("yandex-art").configure(
        width_ratio=1, height_ratio=1, seed=int(time.time())
    )
    op = model.run_deferred(prompt)
    result = op.wait()
    return bytes(result.image_bytes)