#!/usr/bin/env python3
"""
Batch upload card images to API.
Script sẽ scan tất cả ảnh trong folder và upload qua API.

Usage:
  python3 batch_upload_cards.py http://localhost:8000
"""

import sys
import asyncio
from pathlib import Path
import aiohttp
import argparse
from tqdm.asyncio import tqdm


async def upload_image(session, api_url, image_path):
    """Upload single image to API."""
    try:
        with open(image_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=image_path.name)

            async with session.post(
                f"{api_url}/api/cards/upload-by-name",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"status": "success", "file": image_path.name, "id": result["id"]}
                else:
                    text = await resp.text()
                    return {"status": "error", "file": image_path.name, "error": f"HTTP {resp.status}: {text}"}
    except Exception as e:
        return {"status": "error", "file": image_path.name, "error": str(e)}


async def batch_upload(api_url, images_dir):
    """Upload tất cả ảnh từ folder."""
    images_path = Path(images_dir)

    if not images_path.exists():
        print(f"❌ Folder không tồn tại: {images_dir}")
        return

    # Tìm tất cả ảnh
    image_files = sorted(
        list(images_path.glob("*.jpg")) +
        list(images_path.glob("*.jpeg")) +
        list(images_path.glob("*.png")) +
        list(images_path.glob("*.JPG")) +
        list(images_path.glob("*.JPEG")) +
        list(images_path.glob("*.PNG"))
    )

    if not image_files:
        print(f"❌ Không tìm thấy ảnh trong {images_dir}")
        return

    print(f"📷 Tìm thấy {len(image_files)} ảnh")
    print(f"🚀 Server: {api_url}")
    print("-" * 60)

    success_count = 0
    error_count = 0
    errors = []

    async with aiohttp.ClientSession() as session:
        tasks = [upload_image(session, api_url, img) for img in image_files]
        results = await tqdm.gather(*tasks, desc="Uploading")

    for result in results:
        if result["status"] == "success":
            print(f"✅ {result['file']}")
            success_count += 1
        else:
            print(f"❌ {result['file']}: {result['error']}")
            error_count += 1
            errors.append(result)

    print("-" * 60)
    print(f"\n📊 Kết quả:")
    print(f"   ✅ Thành công: {success_count}")
    print(f"   ❌ Lỗi: {error_count}")

    if errors:
        print(f"\n⚠️  Chi tiết lỗi:")
        for err in errors[:5]:
            print(f"   - {err['file']}: {err['error']}")
        if len(errors) > 5:
            print(f"   ... và {len(errors)-5} lỗi khác")


def main():
    parser = argparse.ArgumentParser(
        description="Batch upload card images to server API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 batch_upload_cards.py http://localhost:8000
  python3 batch_upload_cards.py http://localhost:8000 ./uploads/card_images
        """
    )
    parser.add_argument(
        "api_url",
        help="API server URL (e.g., http://localhost:8000)"
    )
    parser.add_argument(
        "images_dir",
        nargs="?",
        default="./uploads/card_images",
        help="Images directory (default: ./uploads/card_images)"
    )

    args = parser.parse_args()

    asyncio.run(batch_upload(args.api_url.rstrip('/'), args.images_dir))


if __name__ == "__main__":
    main()
