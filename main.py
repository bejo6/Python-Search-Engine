import os
import sys
import getopt
import threading
from helper import setup_logger
from config import LOG_LEVEL
from bing import Bing
from yahoo import Yahoo
from google import Google
from ask import Ask
from aol import Aol
from yandex import Yandex


logger = setup_logger(level=LOG_LEVEL)


def usage():
    output = [
        'Usage: python {} [OPTIONS]'.format(sys.argv[0]),
        'OPTIONS:',
        '    -h, --help: Show this help message',
        '    -s, --search: Keyword to search',
        '    -o, --output: output file path',
        'EXAMPLES:',
        '    python {} -k "john doe" -o output.txt'.format(sys.argv[0]),
    ]
    print('\n'.join([f'[*] {o}' for o in output]))
    sys.exit(1)


def save_links(links: list, filename: str = 'results.txt'):
    current_links = []
    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            current_links = f.read().splitlines()

    for link in links:
        if link not in current_links:
            with open(filename, 'a') as f:
                f.write(f'{link}\n')
            current_links.append(link)


def engine_tasks(engine, keyword: str, output: str = None):
    links = engine.search(keyword)
    if output:
        save_links(links, output)
    else:
        save_links(links)


def engine_start(keyword: str, output: str = None):
    engines = [
        Bing(),
        Yahoo(),
        Google(),
        Ask(),
        Aol(),
        Yandex(),
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
    try:
        opts, args = getopt.getopt(sys.argv[1:], 's:o:h', ['search=', 'output=', 'help'])
    except getopt.GetoptError as err:
        logger.error(err)
        usage()
        sys.exit(2)

    output = None
    search = None
    for o, a in opts:
        if o in ("-s", "--search"):
            search = a
        elif o in ("-o", "--output"):
            output = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if not search:
        usage()
        sys.exit()

    engine_start(keyword=search, output=output)


if __name__ == '__main__':
    main()
