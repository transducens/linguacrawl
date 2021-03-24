# linguacrawl
`linguacrawl` is a tool implemented in Python3 that allows to crawl a number of top-level domains to download any text
documents in the languages specified by the user. The objective of this tool is to get as much data of interest in the
minimum time possible. To achieve this, a scout strategy is adopted to stop crawling web hosts that are not productive
enough. The user can specify which are the languages of interest and a number of documents to be downloaded. After
downloading this number of documents, the amount of data in the targeted languages is checked and if the criteria set by
the user are not fulfilled, the web host is discarded for crawling.

Another interesting feature of linguacrawl as regards performance is that it is implemented following a
provider-consumer architecture. When crawling a website, it is important to keep a waiting time between consecutive
requests to avoid causing trouble in the host server of the website. This means that the crawler may be inactive for
some between requests. Since linguacrawl targets top-level domains, many websites can be crawled at the same time. Using
a provider-consumer architecture allows to spend the waiting time between requests to a website in downloading documents
from other sites. In this way, as the crawler discovers new web hosts to be crawled it becomes more and more productive
(until reaching the limits set by the user).  
 
## Installation and usage
To install linguacrawl first clone the code from the repository:
```shell script
git clone https://github.com/transducens/linguacrawl.git
```
then, get into the downloaded directory and install the dependencies by running:
```shell script
cd linguacrawl
pip3 install -r requirements.txt
```
Finally, use pip3 again to install the tool:
 ```shell script
pip3 install .
```
In order to run the tool, just run the command followed by the path to the configuration file:
 ```shell script
linguacrawl /home/user/config.yaml
```
Note that there is a sample configuration file in the directory config; it can be adapted for any specific crawling
project. The following section describes all the options that can be included in the configuration file.

## Configuration
To use linguacrawl, we need to prepare a configuration file. This configuration file must be in `yaml` format and will
contain different options related to the crawling process, the targeted contents, etc. This section describes all the
options that can be included in the configuration file.

### Basic options
These are general options that are related the basic aspects of configuration of the tool and the crawling task to be
carried out.

#### seed_urls and seed_urls_from_file
`seed_urls` is a list of seed URLs from which to start crawling. The larger this list, the faster the process of
crawling new data. During crawling, linguacrawl discovers new websites to be visited by looking for new URLs in the
documents available from the seed ULRs. If only one seed URL is set, this process of discovering new sites o visit will
be slower (or even could not be possible, if the seed website do not contain links to other sites in the accepted TLDs).
Therefore, it is advisable to add as many different URLs to the list as possible. An example:
```yaml
seed_urls: ['https://www.ffff.es/', 'https://www.dddd.cat/']
```
If this list is too large, the alternative `seed_urls_from_file` option is provided. This option allows to define the
path to a text file that contains the list of seed URLs (one URL per line):
```yaml
seed_urls_from_file: '/home/user/my_seed_urls.txt'
```

#### langs_of_interest
Option `langs_of_interest` is a mandatory option, and allows to specify the code of the languages of interest of the
crawl. If we are interested in crawling every document in English, Spanish and Catalan, we will set this option to the
following list:
```yaml
langs_of_interest: ['en','es','ca']`
```

#### accepted_tlds
Option `accepted_tlds` allows to define the list of top-level domains (TLDs) accepted during crawling. This means that
any websites in a different TLD will not be visited. For example, if we want to constraint our crawling to the `.cat`
and `.es` TLDs, we can set this option to:
```yaml
accepted_tlds: ['es','cat']
```

#### accepted_content
Option `accepted_content` allows to specify the type of content accepted. By default, this option is set to
`(text/html)`:
```yaml
accepted_content: '(text/html)'
```

#### output_dir
Option `output_dir` is a mandatory option, and allows to define the output dir where the files produced during crawling will be
stored, for example:
```yaml
output_dir: '/home/user/crawl_output'
```
Three files may be created for every web host visited: 
* one or more files with extension `.warc.gz` containing all the documents downloaded in
[WARC](https://en.wikipedia.org/wiki/Web_ARChive) format,
* a file with extension `.state` that contains the internal state of the crawler when crawling is stopped, to allow 
resuming the crawl at some point in the future, and
* a file with extension `.bitextor.gz` that consists of a TSV list of fields: URL, language code, HTML and
text extracted with the library [html2text](https://pypi.org/project/html2text); some of these fields can be
used by the tool Bitextor to try to identify parallel data. In the near future, this tool will prove a script to
transform these fields into the format expected by Bitextor.

#### verbose
If `verbose` is set to `false`, only errors will be reported through `stderr`; if it is set to `true`,  much more
information will be provided about the process (be careful, this information could be huge if many parallel jobs are run
in parallel). For example: 
```yaml
verbose: False
```

#### max_jobs
Option `max_jobs` allows to determine how many crawling processes can be run in parallel. This value will be defined
according to the computational resources of the machine were the tool is used. For example, in a machine with 12
threads, this option can be set to 12:
```yaml
max_jobs: 12
```

#### resume_crawling
If this option is set to `true`, the crawling tool will look for the file with extension `.state` for every new web host
to be visited. If this file exists, it will load the previous state of the crawler for it and will only visit pages that
have not been visited before. As regards the WARC file produced, a new file will be created every time the crawling is 
resumed. New files will be named with extension `.1.warc.gz`, `.2.warc.gz`, etc. The same applies for files with
extension `.bitextor.gz`. To activate resuming, set the option as follows:
```yaml
resume_crawling: True
```

### Web crawler configuration

Options to configure the behaviour of the crawling robot/s used. 

#### user_agent
Option `user_agent` is a mandatory option, and allows to specify the user agent for the crawler launched. The user agent
is an important information provided to web servers at the time of requesting access to a page. This allows servers to
limit access to contents through `robots.txt`. For example, we could set Google's bot user agent string 
by seting this option to the following string:
```yaml
user_agent: 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
```

#### crawl_delay
`crawl_delay` option allows to specify the delay (in seconds) between consecutive requests to a web domain. This delay
only affects to requests to the same web domain and is aimed at preventing to hinder the web servers that host the
website. The default value for this property is 3 seconds, but it can be modified by seting the option in the
configuration file, for example: 
```yaml
crawl_delay: 5
```

#### max_time_per_site
`max_time_per_site` option allows to specify the maximum crawling time (in seconds) devoted to a single web domain. When
this time is reached, crawling is stopped for this web site. For example, if we want to stop crawling a site after 24
hours, we can set the option:
```yaml
max_time_per_site: 5184000
```

#### connection_timeout
`connection_timeout` allows to set the connection time out (in seconds) for a given web server. For example, to set this
variable to 10 seconds:
 ```yaml
connection_timeout: 10
```

#### prefix_filter
With option `prefix_filter`, one can automatically discard links that start with a specified prefix. This 
option accepts a list of prefixes that can be defined as a regular expression. For example, to avoid adding
links to e-mails, we could set the following option:  
```yaml
prefix_filter: ['mailto:']
```

#### max_folder_tree_depth
Option `max_folder_tree_depth` allows to set te maximum folder depth for a URL to be taken into account. Defining this
option helps to avoid falling in loops that keep concatenating a string to a URL (in this case, a string that
corresponds to a folder). For example, to set this option to 20, use:  
```yaml
max_folder_tree_depth: 20
```

#### max_attempts
Option `max_attempts` allows to define the maximum number of attempts to visit a web page. If it is not possible to
download a page after the maximum number of attempts, it is discarded. For example, to set this option to three
attempts, use:
```yaml
max_attempts: 3
```

#### url_blacklist
Option `url_blacklist` allows to specify a list of web domains that will not be taken into account. The following could
be an example of web domains that we may want to discard in our crawling:
```yaml
url_blacklist: ['wordpress','blogspot','facebook','google','wikipedia','youtube','perehodi','twitter','instagram']
```
Note that, by defining a web domain, for example `google`, we are discarding web hosts such as `www.google.com`,
`www.google.cat`, `mail.google.com`, etc.

### Language scout options
One of the most relevant features of linguacrawl is that it is designed to get language-specific text data from the
Internet. In order to make crawling as productive as possible, it implements a scout strategy that stops crawling a web
host if, after downloading a given number of documents, no enough useful data has been downloaded. The following options
allow the user to configure this scouting method.

#### scout_steps
Option `scout_steps` determines the number of pages to be downloaded from a web page before the scouting criterion
is evaluated. After this is done, the web host may be discarded (crawling will be stopped on this site) or accepted to
keep crawling, but the scout criterion will not be evaluated again. Example:
```yaml
scout_steps: 200
```

#### min_langs_in_site
Option `min_langs_in_site` is used by the scout criterion. If we are interested in identifying websites with
multilingual content and we have defined a list of languages for option `langs_of_interest`, we can specify the minimum
number of those languages that need to appear in a web host to be accepted by the scout criterion. For example, we could
set that English, Spanish and Catalan are our languages of interest, and specify that at least two of them have to
appear in a web host to consider it useful: 
```yaml
min_langs_in_site: 2
```

#### mandatory_lang
Option `mandatory_lang` is related to the previous option `min_langs_in_site`, and allows to specify a language that is
that is required to appear in a web host in order to be considered useful by the scout criterion. When running a
multilingual crawling, we may be mostly interested in one of the languages. Following the previous example, if we are
crawling English, Spanish and Catalan data, we may be mostly interested in Catalan (for example, if we plan to build
Catalan-English and Catalan-Spanish parallel corpora). In that case, we would define the option as follows:
```yaml
mandatory_lang: 'ca'
```

#### min_percent_mandatory_lang
Option `min_percent_mandatory_lang` is related to the previous option `mandatory_lang` and allows to define the expected
percentage of documents in the mandatory language at the moment of evaluating the scout criterion. For example, we can
specify that, at least, 10% of the documents downloaded from a web host need to be in the mandatory language to be 
considered a useful web host:
```yaml
min_percent_mandatory_lang: 10
```

## License
This software has been released un [GPL3](https://www.gnu.org/licenses/gpl-3.0.html) license. 

## Acknowledgements

Developed by Universitat d'Alacant as part of its contribution to the GoURMET project, which received funding from the
European Union’s Horizon 2020 research and innovation programme under grant agreement No 825299.
