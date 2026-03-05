from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
from typing import List



@dataclass
class Contest:
    id: int  # 比赛ID
    name: str  # 比赛名称
    url: str  # 比赛链接
    start_time: int  # 开始时间戳（秒）
    duration: int  # 持续时间（秒）


@dataclass
class Rating:
    name: str  # 用户名
    current: int  # 当前积分


class Platform(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    async def get_contests(self) -> List[Contest]:
        """
        获取比赛列表

        Returns:
            比赛列表
        """
        pass
