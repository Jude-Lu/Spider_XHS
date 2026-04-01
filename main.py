import json
import os
import urllib
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx


def save_json(data, file_path):
    with open(file_path, mode='w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f'数据保存至 {file_path}')


class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        """
        爬取一个笔记的信息
        :param note_url:
        :param cookies_str:
        :return:
        """
        note_info = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                note_info = note_info['data']['items'][0]
                note_info['url'] = note_url
                note_info = handle_note_info(note_info)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None):
        """
        爬取一些笔记的信息
        :param notes:
        :param cookies_str:
        :param base_path:
        :return:
        """
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        note_list = []
        for note_url in notes:
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if note_info is not None and success:
                note_list.append(note_info)
        for note_info in note_list:
            if save_choice == 'all' or 'media' in save_choice:
                download_note(note_info, base_path['media'], save_choice)
        if save_choice == 'all' or save_choice == 'excel':
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            save_to_xlsx(note_list, file_path)


    def spider_homefeed_recommend_notes(self, category: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', require_num: int = 20, proxies=None):
        """
        爬取首页推荐的笔记信息
        :param category: 首页频道名称，例如 all
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param save_choice: 保存方式，all/media/excel
        :param excel_name: 保存到 excel 时的文件名
        :param require_num: 需要获取的笔记数量
        :param proxies: 代理
        """
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        note_list = []
        try:
            success, msg, notes = self.xhs_apis.get_homefeed_recommend_by_num(category, require_num, cookies_str, proxies)
            if success:
                for note in notes:
                    if note.get('model_type') != 'note':
                        continue
                    note_id = note.get('id')
                    xsec_token = note.get('xsec_token')
                    if not note_id or not xsec_token:
                        continue
                    note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
                    if note.get('xsec_source'):
                        note_url += f"&xsec_source={note['xsec_source']}"
                    note_list.append(note_url)
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
            note_list = []
        logger.info(f'爬取首页推荐笔记 {category}: {success}, msg: {msg}')
        return note_list, success, msg


    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None):
        """
        爬取一个用户的所有笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo: dict = None,  excel_name: str = '', proxies=None):
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param base_path 保存路径
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            返回搜索的结果
        """
        note_list = []
        try:
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort_type_choice, note_type, note_time, note_range, pos_distance, geo, proxies)
            if success:
                notes = list(filter(lambda x: x['model_type'] == "note", notes))
                logger.info(f'搜索关键词 {query} 笔记数量: {len(notes)}')
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = query
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'搜索关键词 {query} 笔记: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_note_all_comments(self, note_url: str, cookies_str: str, base_path: dict, file_prefix: str = 'note', comment_mode: str = 'all', proxies=None):
        """
        爬取笔记的评论
        :param note_url: 笔记链接，需要包含 xsec_token
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param file_prefix: 文件名前缀
        :param comment_mode: 评论抓取模式，all=全部评论，top=仅一级评论
        """
        try:
            if comment_mode == 'top':
                url_parse = urllib.parse.urlparse(note_url)
                note_id = url_parse.path.split('/')[-1]
                kvs = url_parse.query.split('&')
                kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
                success, msg, comment_list = self.xhs_apis.get_note_all_out_comment(note_id, kvDist['xsec_token'], cookies_str, proxies)
            else:
                success, msg, comment_list = self.xhs_apis.get_note_all_comment(note_url, cookies_str, proxies)
            note_id = os.path.basename(note_url.split('?')[0])
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{file_prefix}_{note_id}_comments_{comment_mode}.json'))
            if success:
                save_json(comment_list, file_path)
        except Exception as e:
            success = False
            msg = e
            comment_list = None
        logger.info(f'爬取笔记评论 {note_url} mode={comment_mode}: {success}, msg: {msg}')
        return comment_list, success, msg

    def spider_user_all_related_info(self, user_url: str, cookies_str: str, base_path: dict, file_prefix: str = 'user', fetch_comments: bool = False, comment_mode: str = 'all', proxies=None):
        """
        爬取用户相关信息：作品、喜欢、收藏，可选爬取全部笔记评论
        :param user_url: 用户主页链接，需要包含 xsec_token
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param file_prefix: 文件名前缀
        :param fetch_comments: 是否爬取用户所有作品的全部评论
        :param comment_mode: 评论抓取模式，all=全部评论，top=仅一级评论
        """
        try:
            url_parse = os.path.basename(user_url.split('?')[0])
            user_id = url_parse
            # 用户信息
            success, msg, user_info = self.xhs_apis.get_user_info(user_id, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            # 作品
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            note_urls = [f"https://www.xiaohongshu.com/explore/{item['note_id']}?xsec_token={item['xsec_token']}" for item in all_note_info]
            # 喜欢
            success, msg, like_notes = self.xhs_apis.get_user_all_like_note_info(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            # 收藏
            success, msg, collect_notes = self.xhs_apis.get_user_all_collect_note_info(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            result = {
                'user_info': user_info,
                'notes': all_note_info,
                'liked_notes': like_notes,
                'collected_notes': collect_notes,
            }
            if fetch_comments:
                note_comments = {}
                for note_url in note_urls:
                    note_id = os.path.basename(note_url.split('?')[0])
                    comments, _, _ = self.spider_note_all_comments(note_url, cookies_str, base_path, file_prefix=f'{file_prefix}_{note_id}', comment_mode=comment_mode, proxies=proxies)
                    note_comments[note_url] = comments
                result['note_comments'] = note_comments
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{file_prefix}_{user_id}_related.json'))
            save_json(result, file_path)
        except Exception as e:
            success = False
            msg = e
            result = None
        logger.info(f'爬取用户相关信息 {user_url}: {success}, msg: {msg}')
        return result, success, msg

    def spider_user_all_note_comments(self, user_url: str, cookies_str: str, base_path: dict, file_prefix: str = 'user', comment_mode: str = 'all', proxies=None):
        """
        爬取用户所有笔记详情，并抓取每条笔记的评论
        :param user_url: 用户主页链接，需要包含 xsec_token
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param file_prefix: 文件名前缀
        :param comment_mode: 评论抓取模式，all=全部评论，top=仅一级评论
        :param proxies: 代理
        """
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            note_urls = [f"https://www.xiaohongshu.com/explore/{item['note_id']}?xsec_token={item['xsec_token']}" for item in all_note_info]
            result = []
            for note_url in note_urls:
                note_id = os.path.basename(note_url.split('?')[0])
                note_info = None
                comments = None
                success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
                if not success:
                    logger.warning(f'获取笔记详情失败 {note_url}: {msg}')
                comments, _, _ = self.spider_note_all_comments(note_url, cookies_str, base_path, file_prefix=f'{file_prefix}_{note_id}', comment_mode=comment_mode, proxies=proxies)
                result.append({
                    'note_url': note_url,
                    'note_info': note_info,
                    'comments': comments,
                })
            user_id = os.path.basename(user_url.split('?')[0])
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{file_prefix}_{user_id}_notes_comments.json'))
            save_json(result, file_path)
        except Exception as e:
            success = False
            msg = e
            result = None
        logger.info(f'爬取用户所有笔记及评论 {user_url}: {success}, msg: {msg}')
        return result, success, msg

    def spider_self_account_activity(self, cookies_str: str, base_path: dict, file_prefix: str = 'account', proxies=None):
        """
        爬取当前登录账号的通知类信息：评论/@ 提醒、赞和收藏、新增关注
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param file_prefix: 文件名前缀
        """
        try:
            success, msg, mentions = self.xhs_apis.get_all_metions(cookies_str, proxies)
            if not success:
                raise Exception(msg)
            success, msg, likes_collects = self.xhs_apis.get_all_likesAndcollects(cookies_str, proxies)
            if not success:
                raise Exception(msg)
            success, msg, connections = self.xhs_apis.get_all_new_connections(cookies_str, proxies)
            if not success:
                raise Exception(msg)
            result = {
                'mentions': mentions,
                'likes_and_collects': likes_collects,
                'new_connections': connections,
            }
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{file_prefix}_activity.json'))
            save_json(result, file_path)
        except Exception as e:
            success = False
            msg = e
            result = None
        logger.info(f'爬取当前登录账号活动信息: {success}, msg: {msg}')
        return result, success, msg

    def spider_user_self_data(self, user_url: str, cookies_str: str, base_path: dict, file_prefix: str = 'self', proxies=None):
        """
        爬取当前登录账号的用户作品 / 点赞 / 收藏
        :param user_url: 当前登录账号的用户主页链接，需要包含 xsec_token
        :param cookies_str: cookies
        :param base_path: 保存路径
        :param file_prefix: 文件名前缀
        """
        try:
            # 爬取当前账号自己的作品详情（包含每条笔记的详情 + 媒体文件）
            _, _, note_list = self.spider_user_all_note(user_url, cookies_str, base_path, 'all', excel_name=file_prefix, proxies=proxies)
            # 爬取当前账号自己的点赞笔记列表
            success, msg, like_notes = self.xhs_apis.get_user_all_like_note_info(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            # 爬取当前账号自己的收藏笔记列表
            success, msg, collect_notes = self.xhs_apis.get_user_all_collect_note_info(user_url, cookies_str, proxies)
            if not success:
                raise Exception(msg)
            result = {
                'liked_notes': like_notes,
                'collected_notes': collect_notes,
            }
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{file_prefix}_likes_collects.json'))
            save_json(result, file_path)
        except Exception as e:
            success = False
            msg = e
            result = None
        logger.info(f'爬取当前登录账号作品/点赞/收藏 {user_url}: {success}, msg: {msg}')
        return result, success, msg

if __name__ == '__main__':
    """
        此文件为爬虫的入口文件，可以直接运行
        apis/xhs_pc_apis.py 为爬虫的api文件，包含小红书的全部数据接口，可以继续封装
        apis/xhs_creator_apis.py 为小红书创作者中心的api文件
        感谢star和follow
    """

    cookies_str, base_path = init()
    data_spider = Data_Spider()
    """
        save_choice: all: 保存所有的信息, media: 保存视频和图片（media-video只下载视频, media-image只下载图片，media都下载）, excel: 保存到excel
        save_choice 为 excel 或者 all 时，excel_name 不能为空
    """


    # 1 爬取列表的所有笔记信息 笔记链接 如下所示 注意此url会过期！
    notes = [
        r'https://www.xiaohongshu.com/explore/683fe17f0000000023017c6a?xsec_token=ABBr_cMzallQeLyKSRdPk9fwzA0torkbT_ubuQP1ayvKA=&xsec_source=pc_user',
    ]
    # data_spider.spider_some_note(notes, cookies_str, base_path, 'all', 'test')

    # 2 爬取用户的所有笔记信息 用户链接 如下所示 注意此url会过期！
    user_url = 'https://www.xiaohongshu.com/user/profile/69c4fc8c000000003303adf1?xsec_token=AB-KWE1ixMIVGDzKkUGNlehpHSrg9cjjk0wF7nU-sIiSU%3D=&xsec_source=pc_feed'
    # data_spider.spider_user_all_note(user_url, cookies_str, base_path, 'all')
    data_spider.spider_user_self_data(user_url, cookies_str, base_path, file_prefix='self')

    # 2.3 爬取首页推荐的笔记信息
    # category 取值示例：all、美食、旅行 等
    # data_spider.spider_homefeed_recommend_notes('all', cookies_str, base_path, 'all', 'home_recommend', require_num=20)
    # 2.4 爬取用户所有笔记详情，并抓取每条笔记的全部评论
    data_spider.spider_user_all_note_comments(user_url, cookies_str, base_path, file_prefix='user_comments', comment_mode='all')
    # 2.5 只抓取用户所有笔记的一级评论
    # data_spider.spider_user_all_note_comments(user_url, cookies_str, base_path, file_prefix='user_comments_top', comment_mode='top')
    # 2.1 如果你只想爬取“当前登录账号”的作品 + 点赞 + 收藏
    # 请把 user_url 替换成你自己的用户主页 URL，并确保该 URL 包含 xsec_token
    # data_spider.spider_user_self_data(user_url, cookies_str, base_path, file_prefix='self')

    # 2.2 爬取当前登录账号的通知类数据：评论/@提醒、赞收藏、新增关注
    # data_spider.spider_self_account_activity(cookies_str, base_path, file_prefix='self_activity')

    # 3 搜索指定关键词的笔记
    query = "榴莲"
    query_num = 10
    sort_type_choice = 0  # 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
    note_type = 0 # 0 不限, 1 视频笔记, 2 普通笔记
    note_time = 0  # 0 不限, 1 一天内, 2 一周内天, 3 半年内
    note_range = 0  # 0 不限, 1 已看过, 2 未看过, 3 已关注
    pos_distance = 0  # 0 不限, 1 同城, 2 附近 指定这个1或2必须要指定 geo
    # geo = {
    #     # 经纬度
    #     "latitude": 39.9725,
    #     "longitude": 116.4207
    # }
    # data_spider.spider_some_search_note(query, query_num, cookies_str, base_path, 'all', sort_type_choice, note_type, note_time, note_range, pos_distance, geo=None)
