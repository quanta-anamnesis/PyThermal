from __future__ import division, print_function

import fractions
import math as mt

import numpy as np
cimport numpy as np
cimport cython

import Main
import Output


# Calculates nCr (total no. of combinations)
@cython.boundscheck(False)
cdef int ncr(int n, int r):
    f = mt.factorial
    return int(f(n) / (f(r) * f(n - r)))


# Calculates nC0 + nC1 + ... + nCk
@cython.boundscheck(False)
cdef int sum_ncr(int n, int k):
    cdef int s = 0
    cdef int r
    # s = 0
    for r in range(k):
        s += int(ncr(n, r))
    return s


# Relabels states
@cython.boundscheck(False)
def relabel(np.ndarray e_states):
    s = Main.System()
    
    x = np.zeros(shape=(2, s.nop + 1), dtype=np.int32)
    y, dump = [], []
    
    cdef int n
    
    for state in e_states:
        comm, temp = [], []
        n = 0

        for j in state:
            if j <= s.link_pos:
                comm.append(j)
                n += 1

        x[1][n] += 1

        if comm not in dump:
            x[0][n] += 1
            dump.append(comm)

        temp += [x[0][n], n, x[1][n]]
        y.append(temp)

        if x[1][n] == ncr(s.nol_b, s.nop - n):
            x[1][n] = 0
    return np.array(y)


# Calculates the density matrix for sub-lattice A
@cython.boundscheck(False)
def density_matrix_a(np.ndarray label, np.ndarray e_vec, int nos):
    s = Main.System()

    dim_a = int(sum_ncr(s.nol_a, s.nop + 1))
    density_mat_a = np.zeros(shape=(dim_a, dim_a), dtype=complex)
    
    cdef unsigned int i, j, m, n

    for i in range(nos):
        for j in range(nos):
            if label[i][1] == label[j][1] and label[i][2] == label[j][2]:
                m = int(label[i][0] + sum_ncr(s.nol_a, label[i][1]) - 1)
                n = int(label[j][0] + sum_ncr(s.nol_a, label[j][1]) - 1)
                density_mat_a[m][n] += np.vdot(e_vec[j], e_vec[i])

    # Calculates trace & trace of square of density matrix A
    den_trace_a = np.trace(density_mat_a.real)
    # den_trace_a2 = np.trace(np.linalg.matrix_power(density_mat_a, 2))

    # Error checking to make sure trace of DM remains ~1.0
    if mt.fabs(den_trace_a - 1.0) > 1.0e-5:
        Output.warning('Trace of density matrix A is not 1, Trace=', den_trace_a)

    # print(density_mat_a)
    return density_mat_a


# Calculates the density matrix, its trace and the trace of the square of the density matrix for sub-lattice B
@cython.boundscheck(False)
def density_matrix_b(np.ndarray label, np.ndarray e_vec, int nos):
    s = Main.System()

    dim_b = sum_ncr(s.nol_b, s.nop + 1)
    density_mat_b = np.zeros(shape=(dim_b, dim_b), dtype=complex)
    
    cdef unsigned int i, j, m, n

    for i in range(nos):
        for j in range(nos):
            if label[i][1] == label[j][1] and label[i][0] == label[j][0]:
                m = int(label[i][2] + sum_ncr(s.nol_b, (s.nop - label[i][1])) - 1)
                n = int(label[j][2] + sum_ncr(s.nol_b, (s.nop - label[j][1])) - 1)
                density_mat_b[m][n] += np.vdot(e_vec[j], e_vec[i])

    # Calculate trace & trace square of density matrix B
    den_trace_b = np.trace(density_mat_b.real)
    den_trace_b2 = np.trace(np.linalg.matrix_power(density_mat_b, 2))
    # print(den_trace_b2)

    # Error checking to make sure trace of DM remains ~1.0
    if mt.fabs(den_trace_b - 1.0) > 1.0e-4:
        Output.warning('Trace of density matrix B is not 1, Trace=', den_trace_b)

    # print('matrix=\n', density_mat_b)

    return density_mat_b


# GCD using Euclid's Algorithm
def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a


def lcm(a, b):
    # print(a, b, gcd(a, b))
    return (a // fractions.gcd(a, b)) * b


def lcm_call(*args):
    return reduce(lcm, args)


def recursion_time(eigenvalues):
    Output.warning('Recursion time is currently in beta')
    tau = 1 / np.absolute(eigenvalues)
    tau = sorted(tau)
    # print tau
    tau_min = np.amin(tau)
    tau /= tau_min
    tau *= 1.0e3
    tau_int = tau.astype(np.uint64)
    # print tau_int
    return lcm_call(*tau_int) * tau_min / 1.0e3
