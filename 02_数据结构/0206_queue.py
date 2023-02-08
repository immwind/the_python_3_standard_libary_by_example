"""
import:: `import queue`
doc:: [queue](https://docs.python.org/zh-cn/3/library/queue.html)
desc:: 队列
"""

import functools
from queue import PriorityQueue
import threading


# 装饰器，为类生成比较排序方法
@functools.total_ordering
class Job:
    def __init__(self, priority: int, description: str):
        self.priority = priority
        self.description = description
        print("New JOB", description)
        return

    # PriorityQueue 是不相等比较, 因此这个函数在当前场景下不会执行
    def __eq__(self, other):
        try:
            return self.priority == other.priority
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.priority < other.priority
        except AttributeError:
            return NotImplemented


# 最小值先被取出, 由 (sorted(list(entries))[0]) 返回
# 因此数字越小优先级越高
q = PriorityQueue()

q.put(Job(3, "中优先级"))
q.put(Job(42, "低优先级"))
q.put(Job(2, "高优先级"))


def process_job(q: PriorityQueue):
    while True:
        next_job = q.get()
        print("Processing job:", next_job.description)
        q.task_done()


workers = [
    threading.Thread(target=process_job, args=(q,), daemon=True),
    threading.Thread(target=process_job, args=(q,), daemon=True),
]

for w in workers:
    # w.setDaemon(True) # 这个方法在 3.10 中弃用, 改用参数
    w.start()

q.join()  # 阻塞进程，直到所有任务处理

"""
返回:
New JOB 中优先级
New JOB 低优先级
New JOB 高优先级
Processing job: 高优先级
Processing job: 中优先级
Processing job: 低优先级
"""

# ############################################################################ #
# 多线程播客客户程序

from queue import Queue
import threading
import urllib
from urllib.parse import urlparse

import feedparser

num_fetch_threads = 2
enclosure_queue = Queue()

# 这里增加了一个国内捕蛇者说 RSS 链接
feed_urls = [
    "https://pythonhunter.org/feed/audio.xml",
    "http://talkpython.fm/episodes/rss",
]


def message(s: str):
    """打印当前线程"""
    # print("{}: {}".format(threading.current_thread().name, s))
    print(f"{threading.current_thread().name}: {s}")


def download_enclosures(q: Queue):
    """通过队列获取链接并下载
    (执行后无限循环, 只有主线程结束时才结束)
    """

    while True:
        message("等待获取队列 URL")
        url = q.get()  # 即使队列为空，这里也会阻塞等待
        filename = url.rpartition("/")[-1]
        message(f"开始下载: {filename}, {url}")
        # 因为捕蛇者说需要加 headers 才允许下载
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        # response = urllib.request.urlopen(url)
        data = response.read()

        # message("writing to {}".format(filename))
        # 保存 mp3 文件
        with open(filename, "wb") as outfile:
            outfile.write(data)
        # 加 task_done() 的目的是告诉队列，任务已经完成,
        # 这样 join() 才会在最后一个任务完成后解除阻塞
        q.task_done()
        message(f"保存成功: {filename}")


# 运行两个线程进行下载
for i in range(num_fetch_threads):
    worker = threading.Thread(
        target=download_enclosures,
        args=(enclosure_queue,),
        daemon=True,
        name="worker-{}".format(i),
    )
    # worker.setDaemon(True)
    worker.start()

# 通过 feedparser 提取 RSS 内容，并把要下载的数据加到队列
for url in feed_urls:
    # 解析 URL，获取数据，以字典形式返回
    response = feedparser.parse(url)
    for entry in response["entries"][:5]:
        # enclosures 返回的是一个列表（一般长度为 1）
        # 如果一些 URL 是无意义的字符，可以通过 title 获取标题
        title = entry.title
        for enclosure in entry.get("enclosures", []):
            # 解析 URL，这里的主要用途是获取文件名用于打印输出
            parsed_url = urlparse(enclosure["url"])
            # message("queuing {}".format(parsed_url.path.rpartition("/")[-1]))
            message(f"添加 {title} 到队列")
            enclosure_queue.put(enclosure["url"])

message("*** 等待下载完成")
enclosure_queue.join()
message("*** 完成")

"""
原来 .get() 默认会阻塞等待, 之前习惯先用 .empty() 去判断是否为空,
然后再使用 .get() 获取, 看来是多此一举了.
"""
