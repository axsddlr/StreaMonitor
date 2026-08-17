import requests.cookies


def load_cookies_from_netscape(path):
    jar = requests.cookies.RequestsCookieJar()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#') and not line.startswith('#HttpOnly_'):
                continue
            parts = line.split('\t')
            if len(parts) < 7:
                continue
            domain, _flag, path, _secure, _expires, name, value = parts[:7]
            domain = domain.replace('#HttpOnly_', '', 1)
            jar.set(name, value, domain=domain, path=path)
    return jar


def dump_cookies_to_netscape(cookies, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookies:
            domain = cookie.domain
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            secure = 'TRUE' if cookie.secure else 'FALSE'
            expires = str(int(cookie.expires)) if cookie.expires else '0'
            f.write('\t'.join([
                domain, flag, cookie.path or '/', secure, expires,
                cookie.name, cookie.value or '',
            ]) + '\n')
