import re
import cchardet
from .link import Link
import alcazar.bodytext
import cld3
import pycountry
import logging


class WebDocument(object):
    def __init__(self, res, url, max_attempts=1, custom_fasttext_langid_model=None):
        self.response = res
        self.url = url
        self.status = res.status
        self.successfully_read = False
        self.text = self._read_from_response(max_attempts)
        self.encoding, self.utf_text = self._get_encoded_text()
        self.headers = dict(res.getheaders())
        self.links = None
        self._lang = None
        if custom_fasttext_langid_model is not None:
            self.fasttextmodel = custom_fasttext_langid_model
        else:
            self.fasttextmodel = None


    def _read_from_response(self, max_attempts):
        attempts = 0
        output = ""
        while not self.successfully_read and attempts < max_attempts:
            try:
                output = self.response.read()
                self.successfully_read = True
            except:
                attempts += 1
        return output

    # Function that tries to determine the encoding of data and decode it; if encoding detector fails, it tries with
    # three most usual encodings: 'utf-8', 'iso-8859-1', 'windows‑1252'
    def _get_encoded_text(self):
        if self.successfully_read:
            encoding = cchardet.detect(self.text)['encoding']
            if encoding is None:
                encoding = "utf-8"
            if len(self.text) > 0:
                # We convert, even if the text is detected to be UTF8 so, if it is an error and conversion fails,
                # the error is caught here
                for enc in [encoding, 'utf-8', 'iso-8859-1', 'windows‑1252']:
                    try:
                        return enc, self.text.decode(enc)
                    except:
                        pass
        return None, ''

    def get_link_set(self):
        if self.successfully_read and self.links is None:
            extracted_links = re.findall(r"href\s*=\s*['\"]\s*([^'\"]+)['\"]", self.utf_text)
            self.links = [Link(link, self.url) for link in set(extracted_links)]
        return self.links

    def get_lang(self):
        if self.successfully_read and self._lang is None:
            #Extracting actual content of the page and checking language
            utf_text_to_deboilerpipe = re.sub(r'<?xml.*encoding.*?>', '<?xml version="1.0"?>', self.utf_text)
            try:
                article = alcazar.bodytext.parse_article(utf_text_to_deboilerpipe)
                if article.body_text:
                    if self.fasttextmodel is not None:
                        label=self.fasttextmodel.predict(article.body_text.replace("\n"," "))
                        logging.info("Fasttext identified %s category for page %s", str(label), self.url)
                        if "__label__" in label[0][0]:
                            self._lang = label[0][0].strip().split("_")[-1]
                            if len(self._lang) == 3:
                                langinfo = pycountry.languages.get(alpha_3=self._lang)
                                self._lang = langinfo.alpha_2
                    else:
                        self._lang = cld3.get_language(article.body_text)
                        if not self._lang.is_reliable:
                            self._lang = None
                        else:
                            self._lang = self._lang.language
            except Exception as e:
                logging.error(str(e))
                self._lang = None
        logging.info("%s language identified in page %s",self._lang,self.url)
        return self._lang
