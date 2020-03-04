import time
import threading
from threading import Thread, Lock, BoundedSemaphore
from link import Link
from site_crawler import SiteCrawler
import logging
import copy
import heapq
#import psutil
#psutil.cpu_percent()
# SET THE SEED FOR REPRODUCIBILITY TESTS
# SEED=4
# random.seed(SEED)


class MultiSiteCrawler(object):
    def __init__(self, config, scout=None):

        self.config = config
        urls_per_domain = {}
        for seed_url in config["seed_urls"]:
            url = Link(seed_url)
            if url.get_domain() not in urls_per_domain:
                urls_per_domain[url.get_domain()] = []
            urls_per_domain[url.get_domain()].append(url)

        self.curr_crawlers = 0
        self.scout = scout
        self.domain_crawlers = {}
        self.pending_crawlers = []
        for domain, urls in urls_per_domain.items():
            crawler = SiteCrawler(self.curr_crawlers, self, urls, domain, config, copy.deepcopy(self.scout))
            heapq.heappush(self.pending_crawlers, (self.curr_crawlers, crawler))
            self.domain_crawlers[domain] = crawler
            self.curr_crawlers += 1
        self.new_seed_urls = {}
        self.seen_domains = set()
        self.pending_to_crawl_concurrency_lock = Lock()
        self.new_seed_urls_concurrency_lock = Lock()
        # List of all the threads created
        self.threads = []
        # Maximum number of threads that will be run at the same time
        self.max_jobs = config["max_jobs"]
        #self.new_worker_semaphore = BoundedSemaphore(value=self.max_jobs)
        # If this flag is set to True, next job will clean the list of crawlers before starting a new crawl
        self.remove_stopped_crawlers_from_list = False
        Link.prefix_filter = config["prefix_filter"]
        self.interrupt = False

    def start_crawling(self):
        # If the interrupt flat is not enabled and, either there are crawlers available or there are threads running
        # in background, a thread is started
        for i in range(0, self.max_jobs):
            t = Thread(target=self._pick_crawler_and_run_one_doc)
            self.threads.append(t)
            t.daemon = False
            t.start()

    def _pick_crawler_and_run_one_doc(self):
        while not self.interrupt and (len(self.pending_crawlers) > 0 or threading.active_count() > 1):
            #try:
            #self.new_worker_semaphore.acquire()
            crawler = self.pop_crawler_from_heap()
            if crawler is not None:
                crawler.crawl_one_page()
            else:
                self._expand_crawlers_list()
        #finally:
        #    self.new_worker_semaphore.release()

    def pop_crawler_from_heap(self):
        try:
            self.pending_to_crawl_concurrency_lock.acquire()
            priority, crawler = heapq.heappop(self.pending_crawlers)
        except IndexError:
            crawler = None
        finally:
            self.pending_to_crawl_concurrency_lock.release()
        return crawler

    def push_crawler_to_heap(self, crawler):
        try:
            self.pending_to_crawl_concurrency_lock.acquire()
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
        try:
            self.new_seed_urls_concurrency_lock.acquire()
            for d, url_set in self.new_seed_urls.items():
                url_list = list(url_set)
                if d in self.domain_crawlers:
                    c = self.domain_crawlers[d]
                    if c.interrupt:
                        del self.domain_crawlers[d]
                        self.seen_domains.add(d)
                    else:
                        c.extend_url_list(url_list)
                elif d not in self.seen_domains:
                    crawler = SiteCrawler(self.curr_crawlers, self, url_list, d, self.config, copy.deepcopy(self.scout))
                    self.push_crawler_to_heap(crawler)
                    self.domain_crawlers[d] = crawler
                    self.curr_crawlers += 1
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
