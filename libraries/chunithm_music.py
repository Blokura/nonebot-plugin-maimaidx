import asyncio
import json
import random
import traceback
from collections import namedtuple
from copy import deepcopy
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import aiofiles
import httpx
from PIL import Image
from pydantic import BaseModel, Field

from ..config import *
from .image import image_to_base64
from .chunithm_api_data import chuniApi
from .maimaidx_error import *


async def download_music_pictrue(id: Union[int, str]) -> Union[str, BytesIO]:
    try:
        music_id = str(id)
        while len(music_id) < 4:
            music_id = '0' + music_id
        if (file := chunicoverdir / f'CHU_UI_Jacket_{music_id}.png').exists():
            return file
        return chunicoverdir / 'CHU_UI_Jacket_dummy.png'
                
    except:
        return chunicoverdir / 'CHU_UI_Jacket_dummy.png'


async def openfile(file: str) -> Union[dict, list]:
    async with aiofiles.open(file, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    return data


async def writefile(file: str, data: Any) -> bool:
    async with aiofiles.open(file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    return True
