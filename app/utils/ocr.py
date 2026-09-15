from paddleocr import PaddleOCR
from PIL import Image
import io
import numpy as np

ocr = PaddleOCR(
    use_angle_cls=True, 
    lang="ch"
)

def extract_text_from_image(image_bytes: bytes) -> str:
    """从图片内容中提取文字"""
    image = Image.open(io.BytesIO(image_bytes))

    # 把 PIL Image 转成 numpy 数组再传给 PaddleOCR
    result = ocr(np.array(image), cls=True)
    
    text = []
    for line in result:
        for item in line:
            text.append(item[1][0])
    return "\n".join(text)