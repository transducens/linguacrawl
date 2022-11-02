from .generic_scout import GenericScout


class BitextScout(GenericScout):
    def __init__(self, max_steps, langs_of_interest, min_langs_in_site, mandatory_lang, min_percent_mandatory_lang):
        # Language evidence for every website crawled
        super().__init__(max_steps)
        self.lang_evidence = {}
        self.langs_of_interest = langs_of_interest
        self.min_langs_in_site = min_langs_in_site
        self.mandatory_lang = mandatory_lang
        self.min_percent_mandatory_lang = min_percent_mandatory_lang

    def step(self, doc):
        super().step(doc)
        lang = doc.get_lang()
        if lang is not None and lang in self.langs_of_interest:
            if lang in self.lang_evidence:
                self.lang_evidence[lang] += 1
            else:
                self.lang_evidence[lang] = 1

    def recommendation_keep_crawling(self):
        if self.mandatory_lang in self.lang_evidence:
            percent_mandatory_lang = int(self.lang_evidence[self.mandatory_lang]*100/self.max_steps)
        else:
            percent_mandatory_lang = 0
        return (self.mandatory_lang is None or self.mandatory_lang in self.lang_evidence) and len(
                self.lang_evidence.keys()) >= self.min_langs_in_site and percent_mandatory_lang >= self.min_percent_mandatory_lang
