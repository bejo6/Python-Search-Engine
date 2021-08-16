import os
import sys
import getopt
import threading
from bing import Bing
from yahoo import Yahoo
from google import Google


def usage():
    print('usage')


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


def engine_tasks(engine, keyword, output: str = None):
    links = engine.search(keyword)
    if output:
        save_links(links, output)
    else:
        save_links(links)


def engine_start(keyword: str, output: str = None):
    bing = Bing()
    yahoo = Yahoo()
    google = Google()

    threads = []

    for engine in [bing, yahoo, google]:
        t = threading.Thread(target=engine_tasks, args=(engine, keyword, output))
        threads.append(t)

    if threads:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'k:o:h', ['keyword=', 'output=', 'help'])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    output = None
    keyword = None
    for o, a in opts:
        if o in ("-k", "--keyword"):
            keyword = a
        elif o in ("-o", "--output"):
            output = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if keyword:
        engine_start(keyword=keyword, output=output)


if __name__ == '__main__':
    main()
