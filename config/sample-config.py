user_agent: 'gourmet/1.0 (https://gourmet-project.eu/)'
langs_of_interest: ['en','es','ca']
crawl_delay: 5
#max_time_per_site: {'required': False, 'type': 'int'},
#max_size_per_site: {'required': False, 'type': 'int'},
connection_timeout: 10
max_jobs: 12
#resume_crawling: {'required': False, 'type': 'boolean', 'default': True},
accepted_tlds: ['es','cat']
seed_urls: ['https://www.ua.es/']
#seed_urls: ['https://www.vilaweb.cat/','http://web.gencat.cat/','http://www.tv3.cat']
#seed_urls: ['https://www.ua.es','https://www.uv.es']
#seed_urls: ['http://www.deusto-publicaciones.es/deusto/index.php/es/orkestra-es/orkestra02c-libros/orkestra44-cast']
#seed_urls_from_file: {'required': False, 'type': 'string'},
prefix_filter: 'mailto:'
output_dir: '/home/mespla/crawl_output5'
verbose: False
resume_crawling: True
accepted_content: '(text/html)'
max_folder_tree_depth: 20
max_attempts: 3
scout_steps: 200
min_langs_in_site: 2
mandatory_lang: 'ky'
min_percent_mandatory_lang: 10
url_blacklist: ['wordpress','blogspot','facebook','google','wikipedia','youtube','perehodi','twitter','instagram']
