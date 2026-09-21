import os
import base64
import requests

def get_baidu_access_token() -> str:
    """
    获取百度 OCR 的 access_token（有效期 30 天）
    用 API Key 和 Secret Key 换 token
    """
    api_key = os.getenv("BAIDU_OCR_API_KEY")
    secret_key = os.getenv("BAIDU_OCR_SECRET_KEY")

    if not api_key or not secret_key:
        raise RuntimeError(
            "未配置 BAIDU_OCR_API_KEY 或 BAIDU_OCR_SECRET_KEY，"
            "请在环境变量中设置百度 OCR 密钥"
        )

    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key,
    }
    resp = requests.post(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取百度 access_token 失败: {data}")
    return data["access_token"]

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    调用百度 OCR 通用文字识别接口，从图片中提取文字
    文档: https://cloud.baidu.com/doc/OCR/s/zk3h7xz52
    """
    access_token = get_baidu_access_token()
    url = (
        "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        f"?access_token={access_token}"
    )

    # 百度 OCR 需要 base64 编码的图片
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "image": img_base64,
        "language_type": "CHN_ENG",  # 中英文混合
    }

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if "error_code" in result:
        raise RuntimeError(
            f"百度 OCR 识别失败: error_code={result['error_code']}, "
            f"error_msg={result.get('error_msg', '')}"
        )

    # 提取所有行的文字，按顺序拼接
    words = [item["words"] for item in result.get("words_result", [])]
    return "\n".join(words)