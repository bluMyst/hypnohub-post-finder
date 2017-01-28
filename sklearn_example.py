# https://youtu.be/84gqSbLcBFE
# On Windows, try Anaconda.
# C:\"Program Files"\Anaconda3\python
import sklearn, sklearn.datasets, sklearn.cross_validation
import sklearn.neighbors
iris = sklearn.datasets.load_iris()

# f(x) = y
x = iris.data
y = iris.target

x_train, x_test, y_train, y_test = sklearn.cross_validation.train_test_split(
    x, y, test_size=.5)

my_classifier = sklearn.neighbors.KNeighborsClassifier()

my_classifier.fit(x_train, y_train)

predictions = my_classifier.predict(x_test)
print(sklearn.metrics.accuracy_score(y_test, predictions))
