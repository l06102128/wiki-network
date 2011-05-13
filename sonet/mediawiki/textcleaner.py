try:
    import re2 as re
except ImportError:
    import logging
    logging.warn('pyre2 not available: some functionalities can not be used')
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
    import re


class TextCleaner:
    """
    Class with some methods to clean text in order to obtain only significant
    words. For performance reasons there's the need of creating an instance of
    the class instead of using class-methods directly
    """

    def __init__(self):
        """
        Compiles regular expressions for performance
        """
        self.clean_regex = (
            (re.compile(r"(^|\s)(\w\.)+"), ""),
            (re.compile(r"[\:|;|8|=|-]+[a-z](\s|$)", re.IGNORECASE), ""))

        self.clean_wiki_regex = (
            (re.compile(r"(?:https?://)(?:[\w]+\.)(?:\.?[\w]{2,})+(\S+)?"),
                        ""),
            (re.compile(r"\[{1,2}([^\:\|]+?)\]{1,2}", re.DOTALL), r"\1"),
            (re.compile(r"\[{1,2}.+?[\||\:]([^\|^\:]+?)\]{1,2}",
                        re.DOTALL), r"\1"),
            (re.compile(r"\[{1,2}.+?\]{1,2}", re.DOTALL), ""),
            (re.compile(r"\{{1,3}.+?\}{1,3}", re.DOTALL), ""),
            #(re.compile(r"[\w|\s]+:\w+(.+?\])?", re.U), ""))
            (re.compile(r"\|(.+)?(\s+?)?=(\s+?)?(.+)?"), ""))

        # Stripping HTML tags and comments
        self.clean_html_regex = ((re.compile(r"<\!--.+?-->", re.DOTALL), ""),
                                (re.compile(r"<.+?>"), ""),
                                (re.compile(r"\&\w+;"), ""))

    def clean_wiki_syntax(self, text):
        """
        Cleans self._text from wiki syntax
        """
        for regex, replace in self.clean_wiki_regex:
            text = regex.sub(replace, text)
        return text

    def clean_html_syntax(self, text):
        """
        Cleans self._text from HTML tags and comments
        """
        for regex, replace in self.clean_html_regex:
            text = regex.sub(replace, text)
        return text

    def clean_text(self, text):
        """
        Cleans self._text from emoticons and acronyms
        """
        for regex, replace in self.clean_regex:
            text = regex.sub(replace, text)
        return text

    def clean_all(self, text):
        text = self.clean_text(text)
        text = self.clean_wiki_syntax(text)
        text = self.clean_html_syntax(text)
        return text
