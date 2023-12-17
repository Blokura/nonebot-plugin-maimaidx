from typing import Any, List, Optional

import httpx

from ..config import maiconfig
from .maimaidx_error import *


class ChuniAPI:
    
    ChuniAPI = 'https://www.diving-fish.com/api/chunithmprober'
    
    def __init__(self) -> None:
        """封装Api"""
    
    
    def load_token(self) -> str:
        self.token = maiconfig.maimaidxtoken
        self.headers = {'developer-token': self.token}
    
    
    async def _request(self, method: str, url: str, **kwargs) -> Any:
        
        session = httpx.AsyncClient(timeout=30)
        res = await session.request(method, url, **kwargs)

        data = None
        
        if self.ChuniAPI in url:
            if res.status_code == 200:
                data = res.json()
            elif res.status_code == 400:
                raise UserNotFoundError
            elif res.status_code == 403:
                raise UserDisabledQueryError
            else:
                raise UnknownError
        elif self.ChuniAliasAPI in url:
            if res.status_code == 200:
                data = res.json()
                if 'error' in data:
                    raise ValueError(f'发生错误：{data["error"]}')
            elif res.status_code == 400:
                raise EnterError
            elif res.status_code == 500:
                raise ServerError
            else:
                raise UnknownError
        await session.aclose()
        return data
    
    
    async def music_data(self):
        """获取曲目数据"""
        return await self._request('GET', self.ChuniAPI + '/music_data')
    
    
    async def chart_stats(self):
        """获取单曲数据"""
        return await self._request('GET', self.ChuniAPI + '/chart_stats')
    
    
    async def query_user(self, project: str, *, qqid: Optional[int] = None, username: Optional[str] = None, version: Optional[List[str]] = None):
        """
        请求用户数据
        
        - `project`: 查询的功能
            - `player`: 查询用户b50
            - `plate`: 按版本查询用户游玩成绩
        - `qqid`: 用户QQ
        - `username`: 查分器用户名
        """
        json = {}
        if qqid:
            json['qq'] = qqid
        if username:
            json['username'] = username
        if version:
            json['version'] = version
        if project == 'player':
            json['b50'] = True
        return await self._request('POST', self.ChuniAPI + f'/query/{project}', json=json)
    
    
    async def query_user_dev(self, *, qqid: Optional[int] = None, username: Optional[str] = None):
        """
        使用开发者接口获取用户数据，请确保拥有和输入了开发者 `token`
        
        - `qqid`: 用户QQ
        - `username`: 查分器用户名
        """
        params = {}
        if qqid:
            params['qq'] = qqid
        if username:
            params['username'] = username
        return await self._request('GET', self.ChuniAPI + f'/dev/player/records', headers=self.headers, params=params)
    
    
    async def rating_ranking(self):
        """获取查分器排行榜"""
        return await self._request('GET', self.ChuniAPI + f'/rating_ranking')
            
chuniApi = ChuniAPI()
