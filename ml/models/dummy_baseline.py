from sklearn.dummy import DummyClassifier


def make_dummy(strategy="prior"):
    return DummyClassifier(strategy=strategy, random_state=26103)
