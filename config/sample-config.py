user_agent: 'gourmet/1.0 (https://gourmet-project.eu/)'
langs_of_interest: ['en','ky','ru']
crawl_delay: 5
#max_time_per_site: {'required': False, 'type': 'int'},
#max_size_per_site: {'required': False, 'type': 'int'},
connection_timeout: 10
max_jobs: 12
#resume_crawling: {'required': False, 'type': 'boolean', 'default': True},
accepted_tlds: ['kg']
seed_urls: ['http://zakupki.gov.kg/']
#seed_urls: ['http://kabar.kg/','https://www.super.kg/','http://sti.gov.kg/','https://www.mashina.kg/','https://www.job.kg/','http://zakupki.gov.kg/','http://www.turmush.kg/','https://elcat.kg/','https://lalafo.kg/','https://24.kg/','http://minjust.gov.kg/','https://okmot.kg/','https://sputnik.kg/','http://namba.kg','https://salyk.kg/','https://www.vb.kg/','https://kloop.kg/','https://www.kp.kg/','https://www.for.kg/','https://kyrtag.kg/','https://knews.kg/','https://www.gazeta.kg/','http://www.pr.kg/','http://internews.kg/','http://kyrgyztuusu.kg/','https://www.msn.kg/','http://religion.gov.kg/','http://geti.gov.kg/','http://nism.gov.kg/','http://ssm.gov.kg/','http://gamsumo.gov.kg/','http://ssm.gov.kg/','http://sudexpert.gov.kg/','https://beeline.kg','https://o.kg/ru/chastnym-klientam/']
#seed_urls: ['https://www.vilaweb.cat/','http://web.gencat.cat/','http://www.tv3.cat']
#seed_urls: ['https://www.ua.es','https://www.uv.es']
#seed_urls: ['http://www.deusto-publicaciones.es/deusto/index.php/es/orkestra-es/orkestra02c-libros/orkestra44-cast']
#seed_urls_from_file: {'required': False, 'type': 'string'},
prefix_filter: 'mailto:'
output_dir: '/home/mespla/crawl_output3'
verbose: True
accepted_content: '(text/html)'
max_folder_tree_depth: 20
max_attempts: 3
scout_steps: 200
min_langs_in_site: 2
mandatory_lang: 'ky'
min_percent_mandatory_lang: 10
url_blacklist: ['wordpress','blogspot','facebook','google','wikipedia','youtube','perehodi','twitter','instagram']
