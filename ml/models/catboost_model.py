from catboost import CatBoostClassifier


def make_catboost(**overrides):
    params = dict(
        iterations=600, depth=6, learning_rate=0.04, l2_leaf_reg=5,
        loss_function="Logloss", eval_metric="PRAUC", random_seed=26103,
        verbose=False, allow_writing_files=False, thread_count=-1,
    )
    params.update(overrides)
    return CatBoostClassifier(**params)
