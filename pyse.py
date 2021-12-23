import os
import sys
import argparse
import threading
from logging import DEBUG
from utils.helper import setup_logger
from engine.aol import Aol
from engine.ask import Ask
from engine.bing import Bing
from engine.getsearchinfo import GetSearchInfo
from engine.gigablast import Gigablast
from engine.google import Google
from engine.lycos import Lycos
from engine.metager import MetaGer
from engine.mojeek import Mojeek
from engine.naver import Naver
from engine.seznam import Seznam
from engine.yahoo import Yahoo
from engine.yandex import Yandex

logger = setup_logger()


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
                    f.write('%s\n' % link)
                except UnicodeEncodeError:
                    logger.error(link)
                except Exception as err:
                    logger.error(err)

            current_links.append(link)


def engine_tasks(engine, keyword, output=None):
    links = engine.search(keyword)
    if output:
        save_links(links, output)
    else:
        save_links(links)


def engine_start(keyword, output=None, debug_mode=False):
    logger.info('Start search with keyword: %s' % keyword)

    engines = [
        Aol(debug=debug_mode),
        Ask(debug=debug_mode),
        Bing(debug=debug_mode),
        GetSearchInfo(debug=debug_mode),
        Gigablast(debug=debug_mode),
        Google(debug=debug_mode),
        Lycos(debug=debug_mode),
        MetaGer(debug=debug_mode),
        Mojeek(debug=debug_mode),
        Naver(debug=debug_mode),
        Seznam(debug=debug_mode),
        Yahoo(debug=debug_mode),
        Yandex(debug=debug_mode),
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
    parser.add_argument('-d', '--debug',
                        dest='debug_mode',
                        help='Set DEBUG mode)',
                        action='store_true')

    args = parser.parse_args()

    if not args.keyword:
        parser.print_help()
        sys.exit()

    if args.debug_mode:
        logger.setLevel(DEBUG)

    engine_start(keyword=args.keyword, output=args.output_file, debug_mode=args.debug_mode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('Quit')
