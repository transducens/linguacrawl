import http


class Connection:
    def __init__(self, url):

        if url.get_scheme() == 'http':
            conn = http.client.HTTPConnection(url.get_url_parts().netloc, timeout=self.conn_timeout)
        else:
            conn = http.client.HTTPSConnection(url.get_url_parts().netloc, timeout=self.conn_timeout)
        conn.request('GET', quote(url.get_url_parts().path, '?=&%/'), headers={'User-Agent': self.user_agent})
        self.response = conn.getresponse()