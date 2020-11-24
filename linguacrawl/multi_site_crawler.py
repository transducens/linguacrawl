import time
import sys
import threading
from threading import Thread, Lock
from .link import Link
from .site_crawler import SiteCrawler
import logging
import copy
import heapq
from queue import Queue


class MultiSiteCrawler(object):
    def __init__(self, config, scout=None):

        self.config = config
        urls_per_domain = {}
        if "seed_urls_from_file" in config:
            with open(config["seed_urls_from_file"],"r") as fseeds:
                for seed_url in fseeds:
                    url = Link(seed_url)
                    if url.get_domain() not in urls_per_domain:
                        urls_per_domain[url.get_domain()] = []
                    urls_per_domain[url.get_domain()].append(url)
        else:
            for seed_url in config["seed_urls"]:
                url = Link(seed_url)
                if url.get_domain() not in urls_per_domain:
                    urls_per_domain[url.get_domain()] = []
                urls_per_domain[url.get_domain()].append(url)

        if config["custom_fasttext_langid"] is not None:
            import fasttext
            self.fasttextmodel = fasttext.load_model(config["custom_fasttext_langid"])
        else:
            self.fasttextmodel = None


        self.curr_crawlers = 0
        self.scout = scout
        self.domain_crawlers = {}
        self.pending_crawlers = []
        for domain, urls in urls_per_domain.items():
            crawler = SiteCrawler(self.curr_crawlers, self, urls, domain, config, copy.deepcopy(self.scout), self.fasttextmodel)
            heapq.heappush(self.pending_crawlers, (self.curr_crawlers, crawler))
            self.domain_crawlers[domain] = crawler
            self.curr_crawlers += 1
        self.new_seed_urls = {}
        self.seen_domains = set()
        self.wait_for_pending_before_dying = Lock()
        self.number_of_running = 0
        self.pending_to_crawl_concurrency_lock = Lock()
        self.new_seed_urls_concurrency_lock = Lock()
        # List of all the threads created
        self.threads = []
        # Maximum number of threads that will be run at the same time
        self.max_jobs = config["max_jobs"]

        self.new_worker_queue = []
        # If this flag is set to True, next job will clean the list of crawlers before starting a new crawl
        self.remove_stopped_crawlers_from_list = False
        Link.prefix_filter = config["prefix_filter"]
        self.interrupt = False

    def new_running_crawler(self):
        self.wait_for_pending_before_dying.acquire()
        self.number_of_running += 1
        self.wait_for_pending_before_dying.release()

    def new_done_crawler(self):
        self.wait_for_pending_before_dying.acquire()
        self.number_of_running -= 1
        self.wait_for_pending_before_dying.release()

    def get_running_crawlers(self):
        self.wait_for_pending_before_dying.acquire()
        output = self.number_of_running
        self.wait_for_pending_before_dying.release()
        return output

    def get_pending_crawlers(self):
        self.pending_to_crawl_concurrency_lock.acquire()
        output = len(self.pending_crawlers)
        self.pending_to_crawl_concurrency_lock.release()
        return output

    def start_crawling(self):
        # If the interrupt flat is not enabled and, either there are crawlers available or there are threads running
        # in background, a thread is started
        for i in range(0, self.max_jobs):
            t = Thread(target=self._pick_crawler_and_run_one_doc)
            self.threads.append(t)
            t.daemon = True
            self.new_worker_queue.append(t)
            t.start()
        while not self.interrupt and (self.get_pending_crawlers() > 0 or self.get_running_crawlers() > 0):
        #while len(self.new_worker_queue) > 0:
            time.sleep(5)
            #t = self.new_worker_queue.pop()
            #t.join()

        #while not self.interrupt and (self.get_pending_crawlers() > 0 or self.get_running_crawlers() > 0):
        #    sys.stderr.write("Pending crawlers: "+str(self.get_pending_crawlers())+" Running crawlers: "+str(self.get_running_crawlers())+" At: "+str(time.time())+"\n")

        #    t = self.new_worker_queue.get()
        #    sys.stderr.write("Pending crawlers: "+str(self.get_pending_crawlers())+" Running crawlers: "+str(self.get_running_crawlers())+" on thread "+t.name+" At: "+str(time.time())+"\n")

        #    t.start()

    def _pick_crawler_and_run_one_doc(self):
        while not self.interrupt and (self.get_pending_crawlers() > 0 or self.get_running_crawlers() > 0):
            sys.stderr.write("Thread "+threading.current_thread().name+" at "+str(time.time())+" when "+str(len(self.pending_crawlers))+" crawlers are available\n")
            crawler = self.pop_crawler_from_heap()
            if crawler is not None and not crawler.is_interrupted():
                crawler.crawl_one_page()
            else:
                self._expand_crawlers_list()
            #t = Thread(target=self._pick_crawler_and_run_one_doc)
            #self.threads.append(t)
            #t.daemon = False
            #self.new_worker_queue.put(t)

    def pop_crawler_from_heap(self):
        try:
            self.pending_to_crawl_concurrency_lock.acquire()
            #logging.info("Number of crawlers available: %s",str(len(self.pending_crawlers)))
            priority, crawler = heapq.heappop(self.pending_crawlers)
        except IndexError:
            crawler = None
        finally:
            self.pending_to_crawl_concurrency_lock.release()
        return crawler

    def push_crawler_to_heap(self, crawler):
        try:
            self.pending_to_crawl_concurrency_lock.acquire()
            logging.info("Crawler %s added to heap again with %s pending URLs", crawler.domain, str(len(crawler.pending_urls)))
            heapq.heappush(self.pending_crawlers, (crawler.priority, crawler))
        finally:
            self.pending_to_crawl_concurrency_lock.release()

    # Method used by the site-crawlers to add new URLs to the new_seed_urls list
    def extend_seed_urls(self, url):
        try:
            self.new_seed_urls_concurrency_lock.acquire()
            if url.get_domain() not in self.seen_domains:
                if url.get_domain() not in self.new_seed_urls:
                    self.new_seed_urls[url.get_domain()] = set()
                self.new_seed_urls[url.get_domain()].add(url)
        finally:
            self.new_seed_urls_concurrency_lock.release()

    # Method that expands the list of site-crawlers by adding any URL in the new_seed_urls list
    def _expand_crawlers_list(self):
        logging.info("Expanding_crawlers_list")
        try:
            self.new_seed_urls_concurrency_lock.acquire()
            logging.info("New URLs to be added: %s", str(len(self.new_seed_urls)))
            if len(self.new_seed_urls) > 0:
                logging.info("Expanding_crawlers_list; before: %s", str(len(self.domain_crawlers)))
                for d, url_set in self.new_seed_urls.items():
                    url_list = list(url_set)
                    if d in self.domain_crawlers:
                        c = self.domain_crawlers[d]
                        if c.is_interrupted():
                            del self.domain_crawlers[d]
                            self.seen_domains.add(d)
                        else:
                            c.extend_url_list(url_list)
                    elif d not in self.seen_domains:
                        crawler = SiteCrawler(self.curr_crawlers, self, url_list, d, self.config, copy.deepcopy(self.scout), self.fasttextmodel)
                        self.push_crawler_to_heap(crawler)
                        self.domain_crawlers[d] = crawler
                        self.curr_crawlers += 1
                logging.info("Expanding_crawlers_list; after: %s", str(len(self.domain_crawlers)))

        finally:
            self.new_seed_urls_concurrency_lock.release()

    def termsighandler(self, signum, frame):
        logging.info("Stopping crawling by user's SIGTERM")
        self.interrupt = True
        logging.info("Running threads: %s", str(threading.active_count()))
        list_of_threads = []
        for t in threading.enumerate():
            list_of_threads.append(t.getName())
        logging.info("List of running threads: %s", " _ ".join(list_of_threads))

        self.new_seed_urls_concurrency_lock.acquire()
        for domain, crawler in self.domain_crawlers.items():
            crawler.interrupt_crawl()
        self.new_seed_urls_concurrency_lock.release()
        logging.info("All interrupted: %s", " _ ".join(list_of_threads))

    def crawler_ready(self, crawler):
        self.push_crawler_to_heap(crawler)
