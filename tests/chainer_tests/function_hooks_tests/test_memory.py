import unittest

import chainer
from chainer import cuda
from chainer import functions
from chainer import function_hooks
from chainer import gradient_check
from chainer import links
from chainer.testing import attr
import numpy


class TestMemoryHookToLink(unittest.TestCase):

    def setUp(self):
        self.h = function_hooks.MemoryHook()
        self.l = links.Linear(5, 5)
        self.x = numpy.random.uniform(-0.1, 0.1, (3, 5)).astype(numpy.float32)
        self.gy = numpy.random.uniform(-0.1, 0.1, (3, 5)).astype(numpy.float32)

    def test_forward_cpu(self):
        with self.h:
            self.l(chainer.Variable(self.x))

    @attr.gpu
    def test_forward_gpu(self):
        self.l.to_gpu()
        with self.h:
            self.l(chainer.Variable(cuda.to_gpu(self.x)))

    def test_backward_cpu(self):
        with self.h:
            gradient_check.check_backward(self.l, self.x, self.gy)

    @attr.gpu
    def test_backward_gpu(self):
        self.l.to_gpu()
        with self.h:
            gradient_check.check_backward(
                self.l, cuda.to_gpu(self.x), cuda.to_gpu(self.gy))


class TestMemoryHookToFunction(unittest.TestCase):

    def setUp(self):
        self.h = function_hooks.MemoryHook()
        self.f = functions.Exp()
        self.f.add_hook(self.h)
        self.x = numpy.random.uniform(-0.1, 0.1, (3, 5)).astype(numpy.float32)
        self.gy = numpy.random.uniform(-0.1, 0.1, (3, 5)).astype(numpy.float32)

    def test_forward_cpu(self):
        self.f(chainer.Variable(self.x))

    @attr.gpu
    def test_fowward_gpu(self):
        self.f(chainer.Variable(cuda.to_gpu(self.x)))

    def test_backward_cpu(self):
        gradient_check.check_backward(self.f, self.x, self.gy)

    @attr.gpu
    def test_backward_gpu(self):
        gradient_check.check_backward(
            self.f, cuda.to_gpu(self.x), cuda.to_gpu(self.gy))