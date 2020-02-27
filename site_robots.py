from urllib.robotparser import RobotFileParser
import urllib.request
from ssl import CertificateError
import socket
import http.client
from threading import Lock
import logging


class SiteRobots:
    def __init__(self, user_agent, default_delay=5, timeout=10):
        self._site_robots = {}
        self.timeout = timeout
        self.default_delay = default_delay
        self.user_agent = user_agent
        self._delay = None
        self.connection_lock = Lock()

    def add(self, url, max_attempts, domain=None):
        if not url.get_sub_domain() in self._site_robots:
            logging.debug("No robots available for subdomain %s", url.get_sub_domain())
            attempts = 0
            retry = True
            rp = None
            while retry and attempts <= max_attempts:
                logging.debug("Trying (%s) to read robots.txt for subdomain %s", str(attempts), url.get_sub_domain())
                retry = False
                subdomain_robots_url = url.get_scheme()+"://"+url.get_sub_domain()+"/robots.txt"
                rp = urllib.robotparser.RobotFileParser()
                try:
                    attempts += 1
                    self.connection_lock.acquire()
                    with urllib.request.urlopen(subdomain_robots_url, timeout=self.timeout) as f:
                        raw = f.read()
                        rp.parse(raw.decode("utf-8").splitlines())
                    logging.debug("Robots.txt read successfuly for subdomain %s", url.get_sub_domain())
                except urllib.error.HTTPError as err:
                    logging.debug("HTTPError (code %s) while trying to read robots.txt for subdomain %s", str(err.code), url.get_sub_domain())
                    if err.code in (400, 404, 406, 410):
                        rp.allow_all = True
                    elif err.code == 408 or err.code == 504:
                        rp = None
                    else:
                        rp.disallow_all = True
                except UnicodeError:
                    rp.disallow_all = True
                except urllib.error.URLError:
                    rp.disallow_all = True
                except CertificateError:
                    logging.info("WARNING: %s caused a certificate error: nothing will be deonlowaded from the site",
                              url.get_norm_url())
                    rp.disallow_all = True
                except socket.timeout:
                    retry = True
                except http.client.RemoteDisconnected:
                    retry = True
                except ConnectionResetError:
                    retry = True
                except:
                    rp.disallow_all = True
                finally:
                    self.connection_lock.release()
            if rp is None:
                rp = urllib.robotparser.RobotFileParser()
                rp.disallow_all = True
            self._site_robots[url.get_sub_domain()] = rp
            subdomain_delay = self._get_delay_for_url(url)
            # We keep the most restrictive delay value among all the robots.txt in the domain
            if subdomain_delay is not None and (self._delay is None or subdomain_delay > self._delay):
                self._delay = subdomain_delay

    def fetch(self, url, max_attempts, domain=None):
        self.add(url, max_attempts, domain)
        result = self._site_robots[url.get_sub_domain()].can_fetch(self.user_agent, url.get_norm_url())
        logging.debug("Trying to fetch %s with user agent %s. Result: %s", url.get_norm_url(), self.user_agent, result)
        return result

    def _get_delay_for_url(self, url):
        try:
            delay = self._site_robots[url.get_sub_domain()].crawl_delay(self.user_agent)
        except AttributeError:
            delay = self.default_delay
        return delay

    def get_delay(self):
        if self._delay is None:
            return self.default_delay
        else:
            return self._delay
