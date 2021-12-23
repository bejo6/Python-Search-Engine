import os
import re
import random
import logging
from utils.static import list_charset, domain_tlds, user_agent_list


def setup_logger(name=None, level='info'):
    if not name:
        name = 'Search Engine'

    log_format = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    # date_format = '%d-%b-%y %H:%M:%S'
    date_format = '%H:%M:%S'
    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
    )
    logger = logging.getLogger(name=name)

    level = str(level)
    if re.match(r'debug', level, re.I):
        logger.setLevel(logging.DEBUG)
    elif re.match(r'warn(ing)?', level, re.I):
        logger.setLevel(logging.WARNING)
    elif re.match(r'crit(ical)?', level, re.I):
        logger.setLevel(logging.CRITICAL)
    elif re.match(r'error', level, re.I):
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)

    return logger


def full_path(p):
    return os.path.abspath(p)


def path_exist(p):
    return os.path.exists(p)


def file_exist(f):
    if path_exist(f) and os.path.isfile(f):
        return True
    return False


def dir_exist(d):
    if path_exist(d) and os.path.isdir(d):
        return True
    return False


def validate_path(path, isdir=False):
    fpath = full_path(path)
    if isdir:
        directory_name = fpath
    else:
        directory_name = os.path.dirname(fpath)

    if file_exist(directory_name):
        try:
            os.remove(directory_name)
        except os.error as e:
            print(e)
            print('Failed to delete file %s' % directory_name)
            return

    if not path_exist(directory_name):
        try:
            os.makedirs(directory_name)
        except os.error as e:
            print(e)
            print('Failed to create directory %s' % directory_name)
            return

    if dir_exist(directory_name):
        if isdir:
            return os.path.abspath(directory_name)
        else:
            return fpath

    return


def decode_bytes(val):
    decoded = ''
    charset = ''

    for _charset in list_charset:
        charset = _charset
        try:
            decoded = val.decode(charset)
            break
        except UnicodeDecodeError:
            pass
        except LookupError:
            pass

    if decoded and charset:
        return decoded, charset

    charset = 'utf-8'
    decoded = val.decode(charset, 'replace')
    return decoded, charset


def validate_url(url=None, allow_fragments=False):
    if not url:
        return

    spliturl = split_url(url, allow_fragments)
    if not spliturl.get('url'):
        return

    domain = spliturl.get('domain')

    ip_addr = validate_domain_ip(domain)
    if ip_addr:
        return spliturl.get('url')

    valid_domain = validate_domain(domain)
    if valid_domain:
        return spliturl.get('url')

    return


def validate_domain_ip(ip_addr, include_local=False):
    port = ''

    _domain = re.match(r'((https?|s?ftp|ssh)?://)?([^/?]+).*', str(ip_addr), re.I)
    if _domain:
        ip_addr = _domain.group(3)

    patern = r'^(\b((?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:(?<!\.)\b|\.)){4})(:([0-9]+))?$'
    parse_ip = re.match(patern, ip_addr, re.I)
    if not parse_ip:
        return

    ip_addr = parse_ip.group(1)
    if parse_ip.group(4):
        port = parse_ip.group(4)
        if int(port) not in range(1, 65535):
            port = ''

    if not include_local:
        if is_local_ip(ip_addr):
            return

    ip_addr = ':'.join([i for i in [ip_addr, port] if i])

    return ip_addr


def validate_domain(domain: str):
    port = ''

    _domain = re.match(r'((https?|s?ftp|ssh)?://)?([^/?]+).*', domain, re.I)
    if _domain:
        domain = _domain.group(3)

    parse_domain = re.match(r'([a-z0-9-.]+)(:([0-9]+))?', domain, re.I)
    if parse_domain:
        domain = parse_domain.group(1)
        if parse_domain.group(3):
            port = parse_domain.group(3)
            if int(port) not in range(1, 65535):
                port = ''

    domain_split = domain.lower().split('.')
    if len(domain_split) < 2:
        return

    if domain_split[-1] not in domain_tlds:
        return

    for d in domain_split:
        if not d or not re.match(r'^[a-z0-9](([a-z0-9-]+)?([a-z0-9]+))?$', d, re.I):
            return

    domain = '.'.join(domain_split)
    domain = ':'.join([i for i in [domain, port] if i])

    return domain


def get_domain_by_url(url):
    if not url:
        return

    domain_ip = validate_domain_ip(url)
    domain = validate_domain(url)
    if domain_ip:
        domain_ip = domain_ip.split(':')[0]
        return domain_ip

    if domain:
        domain = domain.split(':')[0]
        return domain

    return


def is_local_ip(ip):
    patern = r'(^127\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^172\.1[6-9]{1}[0-9]{0,1}\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^172\.2[0-9]{1}[0-9]{0,1}\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^172\.3[0-1]{1}[0-9]{0,1}\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^192\.168\.[0-9]{1,3}\.[0-9]{1,3}$)|' \
             r'(^169\.254\.[0-9]{1,3}\.[0-9]{1,3}$)'

    if re.match(patern, str(ip).strip()):
        return True

    return False


def split_url(url, allow_fragments=True):
    result = {}
    if not url:
        return result

    url = str(url)
    if not re.match(r'^[a-z]+://[^/?]+.*?$', url, re.I):
        url = re.sub(r'^:?//', '', url)
        url = 'http://%s' % url

    url = unescape_url(url)

    split_fragment = re.split(r'#', url, 1)
    if len(split_fragment) > 1:
        result.update({'fragment': split_fragment[1]})
        url = split_fragment[0]

    split_query = re.split(r'\?', url, 1)
    if len(split_query) > 1:
        result.update({'query': split_query[1]})
        url = split_query[0]

    split_path = re.split(r'(?<![:/])/+', url, 1)
    if len(split_path) > 1:
        result.update({'path': '/%s' % re.sub(r'[/]+', '/', split_path[1])})
        url = split_path[0]

    split_domain = re.split(r'^([a-z]+)://([^/?]+)', url, 1, re.I)
    if len(split_domain) > 2:
        result.update({
            'scheme': split_domain[1].lower(),
            'domain': split_domain[2].lower()
        })

    if result.get('scheme') and result.get('domain'):
        new_url = '%s://%s' % (result.get('scheme'), result.get('domain'))

        if result.get('path'):
            new_url = '%s%s' % (new_url, result.get('path'))
        else:
            new_url = '%s/' % new_url

        if result.get('query'):
            new_url = '%s?%s' % (new_url, result.get('query'))

        if result.get('fragment') and allow_fragments:
            new_url = '%s#%s' % (new_url, result.get('fragment'))

        result.update({'url': new_url})

    return result


def unescape_url(url):
    try:
        import html
        if hasattr(html, 'unescape'):
            return html.unescape(url)
        elif hasattr(html, 'parser'):
            return html.parser.HTMLParser().unescape(url)
        else:
            return url
    except ModuleNotFoundError as err:
        print('ModuleNotFoundError', err)
        import HTMLParser # noqa
        try:
            return HTMLParser.HTMLParser().unescape(url)
        except AttributeError as err:
            print('AttributeError', err)
            pass

    return url


def random_agent():
    return random.choice(user_agent_list)
