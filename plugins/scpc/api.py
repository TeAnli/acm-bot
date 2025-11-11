# 通用headers
from functools import wraps
from typing import Callable, Literal


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Content-Type': 'application/json',
}
# 获取 scpc 用户信息
def user_info_url(username: str) -> str:
    return f'http://scpc.fun/api/get-user-home-info?username={username}'
# 获取 codeforces 比赛信息
def codeforces_contests_url(include_gym: bool = False) -> str:
    return f'https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}'
# 获取 洛谷 比赛信息
def luogu_contests_url(page: int = 1) -> str:
    return f'https://www.luogu.com.cn/contest/list?_contentOnly=1&page={page}'
# 获取 scpc 比赛信息
def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    return f'http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}'
# 获取 codeforces 用户积分
def codeforces_user_rating_url(username: str) -> str:
    return f'https://codeforces.com/api/user.rating?handle={username}'

