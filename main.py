import os
import sys
import argparse
import threading
from helper import setup_logger
from config import LOG_LEVEL
from bing import Bing
from yahoo import Yahoo
from google import Google
from ask import Ask
from aol import Aol
from yandex import Yandex
from naver import Naver
from seznam import Seznam
from lycos import Lycos
from metager import MetaGer
from mojeek import Mojeek
from gigablast import Gigablast
from getsearchinfo import GetSearchInfo

logger = setup_logger(level=LOG_LEVEL)


def save_links(links, filename='results.txt'):
    current_links = []
    if not isinstance(links, list):
        return

    if os.path.exists(filename) and os.path.isfile(filename):
        with open(filename, 'r') as f:
            current_links = f.read().splitlines()

    for link in links:
        if link not in current_links:
            with open(filename, 'a', encoding='utf-8', errors='replace') as f:
                try:
                    f.write(f'{link}\n')
                except UnicodeEncodeError:
                    logger.error(link)

            current_links.append(link)


def engine_tasks(engine, keyword: str, output: str = None):
    links = engine.search(keyword)
    if output:
        save_links(links, output)
    else:
        save_links(links)


def engine_start(keyword: str, output: str = None):
    logger.info('Start search with keyword: %s' % keyword)

    engines = [
        Bing(),
        Yahoo(),
        Google(),
        Ask(),
        Aol(),
        Yandex(),
        Naver(),
        Seznam(),
        Lycos(),
        MetaGer(),
        Mojeek(),
        Gigablast(),
        GetSearchInfo(),
    ]

    threads = []

    for engine in engines:
        t = threading.Thread(target=engine_tasks, args=(engine, keyword, output))
        threads.append(t)

    if threads:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


def main():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    # noinspection PyProtectedMember
    parser._optionals.title = 'Options'
    parser.add_argument('-k', '--keyword',
                        dest='keyword',
                        help='Keyword to search',
                        action='store')
    parser.add_argument('-o', '--output',
                        dest='output_file',
                        help='Output results (default results.txt)',
                        default='results.txt',
                        action='store')

    args = parser.parse_args()

    if not args.keyword:
        parser.print_help()
        sys.exit()

    engine_start(keyword=args.keyword, output=args.output_file)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('Quit')
