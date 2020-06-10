from posixpath import normpath
import re
import tldextract
from urllib.parse import urlparse


class Link(object):
    # Static variable: prefix_filter
    prefix_filter = ""

    def __init__(self, link, in_url=None):
        if link is not None:
            self.original_link = re.sub(r'#[^#]*$', '', link)
        else:
            self.original_link = ""
        self._norm_url = None
        self._url_parts = None
        self._host_parts = None
        self._depth = None
        self.wait_until = None
        self.parent_url = in_url

    def get_norm_url(self):
        if self._norm_url is None:
            self._norm_url = self.get_url_parts().geturl()
        return self._norm_url

    def get_host_parts(self):
        if self._host_parts is None:
            self._host_parts = tldextract.extract(self.get_norm_url())
        return self._host_parts

    def get_domain(self):
        parts = self.get_host_parts()
        return parts.domain+"."+parts.suffix

    def get_sub_domain(self):
        parts = self.get_host_parts()
        if parts.subdomain is None or parts.subdomain == "":
            return parts.domain+"."+parts.suffix
        else:
            return parts.subdomain+"."+parts.domain+"."+parts.suffix

    def get_tld(self):
        parts = self.get_host_parts()
        return parts.suffix

    def get_url_parts(self):
        if self._url_parts is None:
            try:
                self._url_parts = urlparse(self._normalise_url())
                if len(self._url_parts.netloc) == 0 and self.parent_url is not None:
                    self._url_parts = self._url_parts._replace(netloc=self.parent_url.get_url_parts().netloc)
                if len(self._url_parts.scheme) == 0 and self.parent_url is not None:
                    self._url_parts = self._url_parts._replace(scheme=self.parent_url.get_url_parts().scheme)
                normalised_path = normpath(self._url_parts.path)
                normalised_path = re.sub(r"^\.+", "", normalised_path)
                self._url_parts = self._url_parts._replace(path=normalised_path)
            except ValueError:
                self._url_parts = urlparse("")
        return self._url_parts

    def get_scheme(self):
        parts = self.get_url_parts()
        return parts.scheme

    def _normalise_url(self):
        if self.original_link.startswith("http://") or self.original_link.startswith("https://"):
            return self.original_link
        else:
            return "http://"+self.original_link

    def is_valid(self):
        if len(self.get_norm_url()) == 0:
            return False
        # Longer than limit set by the standard RFC7230 are discarded
        elif len(self.original_link) > 2000:
            return False
        elif self.prefix_filter != '' and re.search(self.prefix_filter, self.original_link):
            return False
        else:
            return True

    def get_depth(self):
        if self._depth is None:
            self._depth = self._calc_depth()
        return self._depth

    def get_root_url(self):
        parts = self.get_url_parts()
        return parts.scheme+"://"+parts.netloc

    def _calc_depth(self):
        # calculate url depth
        return len(self.get_url_parts().path.rstrip('/').split('/')) - 1

    def __hash__(self):
        return hash(self.get_norm_url())

    def __str__(self):
        return self.get_norm_url()
