import re
from typing import Optional

class BaseCategorizer:
    def categorize(self, merchant_name: Optional[str], description: Optional[str]) -> Optional[str]:
        raise NotImplementedError

class RuleBasedCategorizer(BaseCategorizer):
    RULES = [
        (re.compile(r'\bamazon\b', re.I), 'Shopping'),
        (re.compile(r'\bstripe\b|\bpaypal\b', re.I), 'Income'),
        (re.compile(r'\buber\b|\blyft\b', re.I), 'Transport'),
        (re.compile(r'\baws\b|\bazure\b|\bgoogle cloud\b|\bgooglecloud\b', re.I), 'Software'),
        (re.compile(r'\bstarbucks\b|\bmcdonalds\b|\bcoffee\b', re.I), 'Food'),
    ]

    def categorize(self, merchant_name, description):
        text = ' '.join(filter(None, [merchant_name or '', description or '']))
        for pattern, category in self.RULES:
            if pattern.search(text):
                return category
        return 'Other'
