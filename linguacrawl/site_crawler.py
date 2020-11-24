import time
from urllib.parse import quote
import http.client
import io
import logging
import pickle
import re
import sys
import time
from .site_robots import SiteRobots
from threading import Thread, Lock
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from .web_document import WebDocument
from .link import Link
import os.path
import socket
import ssl
import gzip
import threading
# SET THE SEED FOR REPRODUCIBILITY TESTS
# SEED=4
# random.seed(SEED)


class SiteCrawler(object):
    def __init__(self, priority, multi_site_crawler, seed_urls, domain, config, scout=None, fasttextmodel=None):
        # Multi-site crawler object that manages current crawler
        self.multi_site_crawler = multi_site_crawler

        # Concurrency lock to ensure that only one process accesses URL lists (pending, visited and attempts)
        #self.url_list_concurrency_lock = Lock()
        # Concurrency lock to ensure that only one process accesses to write the status and the output WARC file
        self.file_write_concurrency_lock = Lock()

        self.interrupt_concurrency_lock = Lock()

        # Domain corresponding to the seed URLs to be crawled
        self.domain = domain
        # Accepted TLDs in the crawl
        self.tlds = config["accepted_tlds"]

        # Set of URLs that have been already crawled
        self.visited = set()
        # Map that counts the number of times a URL is visited and could not be accessed
        self.attempts = {}
        # Links that must not be re-crawled until some time has passed
        self.asleep_links = {}
        # Maximum number of attempts to visit a website and receiving an error until it is discarded
        self.max_attempts = config["max_attempts"]

        # Maximum
        self.max_folder_tree_depth = config["max_folder_tree_depth"]
        # Accepted content time (for example: (text/html) )
        self.accepted_content_type = config["accepted_content"]
        # List of regular expressions to discard URLs
        self.url_blacklist_re = config["url_blacklist"]

        # If interrupt is set to False, crawling stops
        self.interrupt = False
        self.sleep_thread = None

        # Variable that keeps the current size of the crawling
        self.crawl_size = 0.0
        # Priority of the process when added to the queue that manages all the crawlers in MultiSiteCrawler
        self.priority = priority

        # Path to the file that stores crawling state dump
        self.dumpfile = config["output_dir"] + "/" + self.domain + ".state"
        # Path to the file where WARC is writen
        self.output_file_name = config["output_dir"] + "/" + self.domain + ".warc.gz"
        self.metadata_output_file_name = config["output_dir"] + "/" + self.domain + ".bitextor.gz"
        name_counter = 1
        while os.path.isfile(self.output_file_name):
            self.output_file_name = config["output_dir"] + "/" + self.domain + "." + str(name_counter) + ".warc.gz"
            self.metadata_output_file_name = config["output_dir"] + "/" + self.domain + "." + str(
                name_counter) + ".bitextor.gz"
            name_counter += 1
        #f_out = open(self.output_file_name, 'wb')
        #self.writer = WARCWriter(f_out, gzip=True)
        #self.metadata_writer = gzip.open(metadata_output_file_name, "wb")

        # Scout object that will determine if the website is promising and if crawling should be interrupted
        self.scout = scout
        # The user will only keep documents in these languages
        self.langs_of_interest = config["langs_of_interest"]
        self.fasttextmodel=fasttextmodel

        # User agent of the crawl
        self.user_agent = config["user_agent"]
        # Connection timeout
        self.conn_timeout = config["connection_timeout"]
        # Setting default crawling delay
        self.default_delay = config["crawl_delay"]
        # Init list of pending URLs from seed URLs; every URL is checked to confirm that it can be visited
        self.pending_urls = []
        # Robots parser: it is initialised from the first valid seed URL found
        self.robots = SiteRobots(self.user_agent, self.default_delay, self.conn_timeout)
        #self.url_list_concurrency_lock.acquire()
        for url in seed_urls:
            if url.is_valid():
                self.add_url_to_list(url)
        #self.url_list_concurrency_lock.release()

        # If a path is provided, the previous crawling status is restored to resume crawling
        if config["resume_crawling"]:
            if os.path.isfile(self.dumpfile):
                self.load_status(pickle.load(open(self.dumpfile, 'rb')))


        # Maximum crawling size for this site
        if "max_size_per_site" not in config:
            self.max_size = None
        else:
            self.max_size = config["max_size_per_site"]
        # Maximum crawling time for this site
        if "max_time_per_site" not in config:
            self.max_time = None
        else:
            self.max_time = config["max_time_per_site"]
        # Starting time of the crawling; it is used to decide when max_time is reached
        self.starts = int(time.time())
        # Time of the last connection; it is used to make sure that delay is fulfilled
        self.last_connection = self.starts - self.default_delay

    def extend_url_list(self, url_list):
        #self.url_list_concurrency_lock.acquire()
        for u in url_list:
            self.add_url_to_list(u)
        #self.url_list_concurrency_lock.release()

    # Adding URL to the list of URLs to be visited during crawling; before doing so, checks if it was already visited or
    # if it infringes TLD restrictions
    def add_url_to_list(self, url):
        if not url.is_valid():
            logging.info('Thread %s: "%s" is not a valid URL', threading.current_thread().name,  url.get_norm_url())
        if url.get_norm_url() in self.visited or url in self.pending_urls:
            logging.info('Thread %s: "%s" already used before (it may be pending of crawling)', threading.current_thread().name, url.get_norm_url())
        else:
            logging.info('Thread %s: "%s" added to pending URLs', threading.current_thread().name, url.get_norm_url())
            self.pending_urls.append(url)

    def get_pending_url(self):
        url = None
        #try:
        #self.url_list_concurrency_lock.acquire()
        sleeping_urls = []
        while len(self.pending_urls) > 0 and url is None:
            # Next URL is picked from the list of pending URLs and is added to the list of visited URLs
            tmp_url = self.pending_urls.pop()
            if tmp_url.wait_until is not None and tmp_url.wait_until > time.time():
                sleeping_urls.append(url)
            else:
                self.visited.add(tmp_url.get_norm_url())
                url = tmp_url
        self.pending_urls.extend(sleeping_urls)
        #finally:
        #    self.url_list_concurrency_lock.release()
        #threading.current_thread().name = "crawling: "+url.get_norm_url()
        return url

    def _process_link(self, link, url):
        # Longer than limit set by the standard RFC7230 are discarded
        if not link.is_valid():
            logging.info("Thread %s: %s is not a valid link from %s",threading.current_thread().name,str(link),str(url))
            return None
        # Filter url using URL blacklist_re
        for f in self.url_blacklist_re:
            if re.search(f, link.get_norm_url()):
                logging.info("Thread %s: %s in black list from %s",threading.current_thread().name,str(link),str(url))
                return None

        if self.domain == link.get_domain():
            #self.url_list_concurrency_lock.acquire()
            self.add_url_to_list(link)
            #self.url_list_concurrency_lock.release()
            return link
        elif link.get_tld() in self.tlds:
            logging.info("Thread %s: %s not in same domain, but in same TLD as %s",threading.current_thread().name,str(link),str(url))
            #self.url_list_concurrency_lock.acquire()
            if link.get_norm_url() in self.visited:
                logging.info('Thread %s: "%s" already used to extend list of seed URLs', threading.current_thread().name, link.get_norm_url())
                #self.url_list_concurrency_lock.release()
            else:
                logging.info('Thread %s: "%s" used to extend list of seed URLs', threading.current_thread().name, link.get_norm_url())
                self.visited.add(link.get_norm_url())
                #self.url_list_concurrency_lock.release()
                self.multi_site_crawler.extend_seed_urls(link)
            return link
        else:
            logging.info('Thread %s: "%s" discarded: not in the same TLD', threading.current_thread().name, link.get_norm_url())
            return None

    def _calc_depth(self, url):
        # calculate url depth
        return len(url.replace('https', 'http').replace(self.root_url, '')
                   .rstrip('/').split('/')) - 1

    def connect_to_server(self, url):
        res = None
        try:
            logging.info('Thread %s: Connecting to: %s', threading.current_thread().name, url.get_norm_url())
            self.last_connection = time.time()
            # Connections are done with a delay to avoid blocking the server
            if url.get_url_parts().scheme == 'http':
                try:
                    conn = http.client.HTTPConnection(url.get_url_parts().netloc, timeout=self.conn_timeout)
                except:
                    conn = http.client.HTTPSConnection(url.get_url_parts().netloc, timeout=self.conn_timeout)
            else:
                conn = http.client.HTTPSConnection(url.get_url_parts().netloc, timeout=self.conn_timeout)
            logging.info('Thread %s: Connection obtained: %s', threading.current_thread().name, url.get_norm_url())

            conn.request('GET', quote(url.get_url_parts().path, '?=&%/'), headers={'User-Agent': self.user_agent})
            logging.info('Thread %s: Get request set %s', threading.current_thread().name, url.get_norm_url())

            res = conn.getresponse()

            logging.info('Thread %s: Response obtained from: %s', threading.current_thread().name, url.get_norm_url())
        except (http.client.HTTPException, EnvironmentError) as e:
            logging.info('Thread %s: HTTPException when trying to connect to "%s"', threading.current_thread().name,  url.get_norm_url())
            conn = None
            self.process_failed_url(url)
        except socket.timeout:
            logging.info('Thread %s: socket timeout for "%s"', threading.current_thread().name,  url.get_norm_url())
            if conn is not None:
                conn.close()
            self.process_failed_url(url)
        except ssl.CertificateError:
            logging.info('Thread %s: certificate error for "%s"', threading.current_thread().name,  url.get_norm_url())
            if conn is not None:
                conn.close()
            self.process_failed_url(url)
        except ConnectionResetError:
            logging.info('Thread %s: connection reset error for "%s"', threading.current_thread().name,  url.get_norm_url())
            if conn is not None:
                conn.close()
            self.process_failed_url(url)
        except Exception as ex:
            logging.info(str(ex))
            if conn is not None:
                conn.close()
        if conn is None:
            logging.info('Thread %s: connection is closed for "%s"', threading.current_thread().name,  url.get_norm_url())
        else:
            logging.info('Thread %s: connection is correct for "%s"', threading.current_thread().name,  url.get_norm_url())
        return conn, res

    # The method returns True if the response status is 2XX and the document should be processed; otherwhise it takes
    # the corresponding action (manage redirects or errors)
    def deal_with_response_status(self, url, response):
        if 200 <= response.status <= 226:
            return True
        elif 301 <= response.status <= 308:
            rlink = self._process_link(Link(response.getheader('location')), url)
            if rlink is not None:
                logging.info('Thread %s: %s Redirect: %s -> %s', threading.current_thread().name, threading.current_thread().name, url.get_norm_url(), rlink.get_norm_url())
        elif 400 <= response.status <= 407 or 409 <= response.status <= 412 or 414 <= response.status <= 427 or 431 <= response.status:
            self.process_failed_url(url, retry=False)
        elif response.status == 408:
            self.process_failed_url(url, retry=True)
        elif response.status == 413 or response.status == 428:
            waiting_time = response.getheader('Retry-After')
            if waiting_time is None:
                url.wait_until = time.time() + 500
            else:
                url.wait_until = time.time() + int(waiting_time)
            self.process_failed_url(url, retry=True)
        else:
            self.process_failed_url(url, retry=False)
        return False

    def crawl_one_page(self):
        self.multi_site_crawler.new_running_crawler()
        url = self.get_pending_url()
        import sys
        #if url:
        #    sys.stderr.write("Craling: "+url.original_link+"\n")
        #else:
        #    sys.stderr.write("URL is none\n")

        if not self.is_interrupted() and url is not None:
            if not self.robots.fetch(url, self.max_attempts, self.domain):
                logging.info("Thread %s: robots.txt forbids crawling URL: %s", threading.current_thread().name, url.get_norm_url())
                return
            connection, server_response = self.connect_to_server(url)

            # If response is 2XX, the web page is processed
            if server_response is not None and self.deal_with_response_status(url, server_response):
                # Check content type
                content_type = server_response.getheader('Content-Type')
                doc = None
                if content_type is not None and not re.search(self.accepted_content_type, content_type):
                    logging.info("Thread %s: %s discarded: wrong file type", threading.current_thread().name, url.get_norm_url())
                else:
                    doc = WebDocument(server_response, url, self.max_attempts, self.fasttextmodel)
                connection.close()

                if doc is None:
                    logging.info("Thread %s: %s could not be processed", threading.current_thread().name, url.get_norm_url())
                else:
                    logging.info("Thread %s: %s document downloaded", threading.current_thread().name, url.get_norm_url())
                    if not doc.utf_text:
                        logging.info("Thread %s: %s document does not content text or could not be converted into UTF", threading.current_thread().name, url.get_norm_url())
                    else:
                        logging.info("Thread %s: %s document contains text", threading.current_thread().name, url.get_norm_url())
                        links_set = doc.get_link_set()
                        # We can shuffle links to avoid to get biased by the structure of the site
                        # random.shuffle(linksset)
                        listoflinks = []
                        for li in links_set:
                            listoflinks.append(li.get_norm_url())
                        for link in links_set:
                            proc_link = self._process_link(link, doc.url)
                            #logging.info("Thread %s: After processing %s, _process_link says %s", threading.current_thread().name, str(link), str(proc_link))
                        #logging.info("Thread %s: %s new links added to list after processing %s: %s", threading.current_thread().name, str(len(listoflinks)), url.get_norm_url(), str(listoflinks))

                        if doc.get_lang() is None:
                            logging.info("Thread %s: %s discarded: language detection is not reliable", threading.current_thread().name, url.get_norm_url())
                        elif doc.get_lang() not in self.langs_of_interest:
                            logging.info("Thread %s: %s discarded: language not among languages of interest (detected=%s)",
                                         threading.current_thread().name, url.get_norm_url(), doc.get_lang())
                        else:
                            logging.info("Thread %s: Applying scout to %s", threading.current_thread().name, url.get_norm_url())
                            self.run_scout(doc)
                            # The document is writen to the warc
                            #sys.stderr.write("Document "+url.original_link+" was writen into WARC file at "+str(time.time())+"\n")
                            self.write_document(doc)
                            logging.info("Thread %s: %s saved to disk", threading.current_thread().name, url.get_norm_url())
            else:
                if connection is not None:
                    connection.close()

            if self.max_size is not None and self.crawl_size > self.max_size:
                logging.info("Thread %s: %s interrupted because of size limit reached", threading.current_thread().name, url.get_norm_url())
                self.interrupt_crawl()
            elif self.max_time is not None and time.time() - self.crawlstarts > self.max_time:
                logging.info("Thread %s: %s interrupted because of time limit reached", threading.current_thread().name, url.get_norm_url())
                self.interrupt_crawl()
            elif len(self.pending_urls) == 0:
                logging.info("Thread %s: %s interrupted because no more URLs pending", threading.current_thread().name, url.get_norm_url())
                self.interrupt_crawl()
        logging.info("Thread %s: Interrupt flag is %s", threading.current_thread().name, str(self.is_interrupted()))
        # If the crawler is allowed to continue crawling, wait until delay has passed and continue
        if not self.is_interrupted():
            #sys.stderr.write("Document "+url.original_link+" going to sleep\n")
            self.sleep_thread = Thread(target=self._wait_and_queue)
            self.sleep_thread.daemon = True
            self.sleep_thread.name = self.sleep_thread.name + "_sleep"
            self.sleep_thread.start()
        else:
            self.multi_site_crawler.new_done_crawler()

    def _wait_and_queue(self):
        sleeptime = self.robots.get_delay() - (time.time() - self.last_connection)
        logging.info("Thread %s: Crawler %s going to sleep for %s", threading.current_thread().name, self.domain, str(sleeptime))
        if sleeptime > 0:
            time.sleep(sleeptime)
        logging.info("Thread %s: Crawler %s woke up", threading.current_thread().name, self.domain)
        self.multi_site_crawler.crawler_ready(self)
        self.multi_site_crawler.new_done_crawler()
        

    # Scout is run until the recommendation_ready is ready; once it is, the object scout is deleted
    def run_scout(self, doc):
        if self.scout is not None:
            self.scout.step(doc)
            if self.scout.recommendation_ready():
                if not self.scout.recommendation_keep_crawling():
                    logging.info("Thread %s: Website discarded after crawling %s due to infringement of scout rule",
                                 threading.current_thread().name, doc.url.get_norm_url())
                    self.interrupt_crawl()
                else:
                    logging.info("Thread %s: Scout recommends keeping crawling website after downloading %s; langs of interest found: %s",
                                 threading.current_thread().name, doc.url.get_norm_url(), str(self.scout.lang_evidence))
                self.scout = None

    def process_failed_url(self, url, retry=True):
        if not retry:
            #self.url_list_concurrency_lock.acquire()
            self.visited.add(url.get_norm_url())
            #self.url_list_concurrency_lock.release()
            logging.info('Thread %s: %s: the URL does not exist', threading.current_thread().name, url.get_norm_url())
        else:
            if url.get_norm_url() not in self.attempts:
                #self.url_list_concurrency_lock.acquire()
                self.add_url_to_list(url)
                self.attempts[url.get_norm_url()] = 1
                self.visited.remove(url.get_norm_url())
                #self.url_list_concurrency_lock.release()
                logging.info('Thread %s: %s: retrying (attempt 1)', threading.current_thread().name, url.get_norm_url())
            else:
                if self.attempts[url.get_norm_url()] <= self.max_attempts:
                    logging.info('Thread %s: %s: retrying (attempt %s)', threading.current_thread().name, url, str(self.attempts[url.get_norm_url()]))
                    #self.url_list_concurrency_lock.acquire()
                    self.add_url_to_list(url)
                    self.attempts[url.get_norm_url()] += 1
                    self.visited.remove(url.get_norm_url())
                    #self.url_list_concurrency_lock.release()
                else:
                    #self.url_list_concurrency_lock.acquire()
                    del self.attempts[url.get_norm_url()]
                    self.visited.add(url.get_norm_url())
                    #self.url_list_concurrency_lock.release()
                    logging.info('Thread %s: %s: given up after %s attempts', threading.current_thread().name, url.get_norm_url(), str(self.max_attempts))

    def write_document(self, doc):
        #self.file_write_concurrency_lock.acquire()

        f_out = open(self.output_file_name, 'ab')
        writer = WARCWriter(f_out, gzip=True)
        metadata_writer = gzip.open(self.metadata_output_file_name, "ab")
                                
        try:
            headers_list = doc.response.getheaders()
            http_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')
            norm_url = doc.url.get_norm_url()
            record = writer.create_warc_record(norm_url, 'response', payload=io.BytesIO(doc.text),
                                                    http_headers=http_headers)
            writer.write_record(record)
            self.crawl_size += sys.getsizeof(doc.text) / 1000000.0
            #if not metadata_writer.closed and self.metadata_writer is not None:
            metadata_writer.write(("%s\t%s\t%s\n" % (doc.url.get_norm_url(), str(doc.encoding), str(doc.get_lang()))).encode())
        finally:
            f_out.close()
            metadata_writer.close()
            #self.file_write_concurrency_lock.release()

    def get_status_object(self):
        targets = []
        for u in self.pending_urls:
            targets.append(u.get_norm_url())
        return {'visited': self.visited, 'pendingurls': targets, 'attempts': self.attempts}

    def load_status(self, status_obj):
        #try:
            #self.file_write_concurrency_lock.acquire()
            self.visited = status_obj['visited']
            self.pending_urls = []
            for u in status_obj['pendingurls']:
                self.pending_urls.append(Link(u))
            self.attempts = status_obj['attempts']

        #finally:
        #    self.file_write_concurrency_lock.release()


    def save_status(self):
        if self.dumpfile is not None:
            pickle.dump(self.get_status_object(), open(self.dumpfile, 'wb'))

    def interrupt_crawl(self):
        try:
            self.interrupt_concurrency_lock.acquire()
            self.interrupt = True
            self.file_write_concurrency_lock.acquire()
            self.save_status()
        finally:
            self.file_write_concurrency_lock.release()
            self.interrupt_concurrency_lock.release()

    def is_interrupted(self):
        self.interrupt_concurrency_lock.acquire()
        output = self.interrupt
        self.interrupt_concurrency_lock.release()
        return output

    def __hash__(self):
        return hash(self.domain)

    def one_thread_less(self):
        self.threads += 1
