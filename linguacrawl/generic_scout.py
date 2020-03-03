
class GenericScout:
    def __init__(self, max_steps):
        # Maximum number of steps to be taken during scout phase of crawling
        self.max_steps = max_steps
        # Current scout steps
        self.steps = 0

    def recommendation_ready(self):
        return self.max_steps <= self.steps

    def step(self, doc):
        if self.max_steps <= self.steps:
            return
        else:
            self.steps += 1

    def recommendation_keep_crawling(self):
        pass
