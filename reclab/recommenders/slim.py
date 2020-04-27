"""An implementation of the SLIM recommender.

See http://glaros.dtc.umn.edu/gkhome/node/774 for details.
"""
import numpy as np
import scipy.sparse
import sklearn.linear_model
import time

from . import recommender


class SLIM(recommender.PredictRecommender):
    """The SLIM recommendation model which is a sparse linear method.

    Parameters
    ----------
    alpha : float
        Constant that multiplies the regularization terms.
    l1_ratio : float
        The ratio of the L1 regularization term with respect to the L2 regularization.
    max_iter : int
        The maximum number of iterations to train the model for.
    tol : float
        The tolerance below which the optimization will stop.
    seed : int
        The random seed to use when training the model.

    """

    def __init__(self,
                 alpha=1.0,
                 l1_ratio=0.1,
                 positive=True,
                 max_iter=100,
                 tol=1e-4,
                 seed=0):
        """Create a SLIM recommender."""
        super().__init__()
        print("h")
        self._model = sklearn.linear_model.ElasticNet(alpha=alpha,
                                                      l1_ratio=l1_ratio,
                                                      positive=positive,
                                                      fit_intercept=False,
                                                      copy_X=False,
                                                      precompute=True,
                                                      selection='random',
                                                      max_iter=max_iter,
                                                      tol=tol,
                                                      random_state=seed)
        self._weights = None
        self._hyperparameters.update(locals())

        # We only want the function arguments so remove class related objects.
        del self._hyperparameters['self']
        del self._hyperparameters['__class__']

    @property
    def name(self):  # noqa: D102
        return 'slim'

    def update(self, users=None, items=None, ratings=None):  # noqa: D102
        start = time.time()
        start0 = start
        super().update(users, items, ratings)
        super_time = time.time() - start
        num_items = len(self._items)
        self._weights = scipy.sparse.dok_matrix((num_items, num_items))
        start = time.time()
        ratings = self._ratings.tolil()
        tolil_time = time.time() - start 
        for item_id in range(num_items):
            start = time.time()
            target = ratings[:, item_id].toarray()
            toarr_time = time.time() - start
            # Zero out the column of the current item to prevent a trivial solution.
            ratings[:, item_id] = 0
            # Fit the mode and save the weights.
            start = time.time()
            self._model.fit(ratings, target)
            fit_time = time.time() - start
            self._weights[:, item_id] = self._model.sparse_coef_.T
            self._weights[item_id, item_id] = 0
            # Restore the rating column.
            ratings[:, item_id] = target
        start = time.time()
        self._weights = scipy.sparse.csr_matrix(self._weights)
        csr_time = time.time() - start
        print("total: {}, super: {}, tolil: {}, ".format(time.time()-start0,
                                                         super_time, tolil_time) + 
              "toarray(x{}): {}, fit(x{}):{}, csr:{}".format(num_items, toarr_time,
                                                             num_items, fit_time, csr_time))

    def _predict(self, user_item):  # noqa: D102
        # Predict on all user-item pairs.
        start = time.time()
        all_predictions = (self._ratings @ self._weights).todense()
        print("all predictions: {}".format(time.time() - start), end=' ')
        predictions = []
        for user_id, item_id, _ in user_item:
            predictions.append(all_predictions[user_id, item_id])
        print("total: {}".format(time.time() - start))

        return np.array(predictions)
