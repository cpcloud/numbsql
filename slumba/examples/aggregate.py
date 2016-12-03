import sqlite3

from slumba import sqlite_udaf


@sqlite_udaf(float64(float64))
@jitclass([
    ('mean', float64),
    ('sum_of_squares_of_differences', float64),
    ('count', int64),
])
class Var(object):
    def __init__(self):
        self.mean = 0.0
        self.sum_of_squares_of_differences = 0.0
        self.count = 0

    def step(self, value):
        self.count += 1
        delta = value - self.mean
        self.mean += delta
        self.sum_of_squares_of_differences += delta * (value - self.mean)

    def finalize(self):
        return self.sum_of_squares_of_differences / (self.count - 1)


@sqlite_udaf(float64(float64, float64))
@jitclass([
    ('mean1', float64),
    ('mean2', float64),
    ('mean12', float64),
    ('count', int64)
])
class Cov(object):
    def __init__(self):
        self.mean1 = 0.0
        self.mean2 = 0.0
        self.mean12 = 0.0
        self.count = 0

    def step(self, x, y):
        self.count += 1
        n = self.count
        delta1 = (x - self.mean1) / n
        self.mean1 += delta1
        delta2 = (y - self.mean2) / n
        self.mean2 += delta2
        self.mean12 += (n - 1) * delta1 * delta2 - self.mean12 / n

    def finalize(self):
        n = self.count
        return n / (n - 1) * self.mean12



@sqlite_udaf(float64(float64))
@jitclass([
    ('total', float64),
    ('count', int64),
])
class Avg(object):
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        self.total += value
        self.count += 1

    def finalize(self):
        return self.total / self.count


def main():
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE t (random_numbers DOUBLE PRECISION)')
    random_numbers = [(random.random(),) for _ in range(5000000)]

    con.executemany('INSERT INTO t VALUES (?)', random_numbers)

    # new way of registering C functions
    register_aggregate_function(con, b'myavg', 1,
            Avg.step.address, Avg.finalize.address)

    con.create_aggregate('myavg2', 1, Avg.numba_class.class_type.class_def)

    query1 = 'select myavg(random_numbers) as myavg from t'
    query2 = 'select myavg2(random_numbers) as oldavg from t'


    start1 = time.time()
    exe1 = con.execute(query1)
    t1 = time.time() - start1
    result1 = list(exe1)

    start2 = time.time()
    exe2 = con.execute(query2)
    t2 = time.time() - start2
    result2 = list(exe2)

    print(result1 == result2)
    print('t1 == {:.2f}'.format(t1))
    print('t2 == {:.2f}'.format(t2))


if __name__ == '__main__':
    main()
