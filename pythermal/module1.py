# This file is a part of PyThermal. https://github.com/dkpinto/PyThermal
#
# PyThermal - Time evolving hard-core bosons on a 2D crystal lattice
# Thermalization and Quantum Entanglement Project Group
# St. Stephen's Centre for Theoretical Physics
#
# Project Mentor: Dr. A. Gupta
# Project Students: A. Kumar, D. Pinto and M. Ghosh

from __future__ import division, print_function

import itertools as it
import multiprocessing as mp

import numpy as np
import scipy.linalg as la
from tqdm import tqdm

try:
    from builtins import range
except ImportError:
    from __builtin__ import range

__all__ = ['eigenstates_lattice', 'hamiltonian_2d',
           'distribute', 'parallel_call_hamiltonian', 'eigenvalvec']


def eigenstates_lattice(lat, nop, del_pos=None):
    """
    Returns eigenstates for a given lattice & particles after deleting sites
    :param lat: Array of lattice sites
    :param nop: Nop of particles in lattice
    :param del_pos: Lattice sites to delete
    :return: Eigenstates
    :return: Total no. of states

    """
    if del_pos is None:
        e_states = np.array(list(it.combinations(lat, nop)), dtype=np.int32)
    else:
        lat_del = np.delete(lat, del_pos - 1)
        e_states = np.array(list(it.combinations(lat_del, nop)),
                            dtype=np.int32)

    return e_states, len(e_states)


def hamiltonian_2d(start, stop, nos, nsa, nop, e_states, queue, h):
    """
    :param start: Start iterations at this point
    :param stop: Stop iterations at this point
    :param nos: No. of states
    :param nsa: Shape of lattice
    :param nop: No. of particles
    :param e_states: Array of eigenstates
    :param queue: Multiprocessing queue to store each processes' output
    :param h: Hamiltonian matrix

    """
    for j in tqdm(range(start, stop)):  # Start/Stop defined by distribute()

        for k in range(nos):  # k iterates over all possibilities

            c = np.intersect1d(e_states[j], e_states[k])
            # Sum of common elements
            c_sum = np.sum(c, dtype=np.int32)
            # No. of common elements
            c_size = np.size(c)

            j_sum = np.sum(e_states[j], dtype=np.int32)
            k_sum = np.sum(e_states[k], dtype=np.int32)

            if c_size == nop - 1:
                # Only one element differs

                if abs(j_sum - k_sum) == nsa:
                    # Element differs by dimension
                    h[j, k] = float(1)

                elif (k_sum - j_sum) == 1 and not (j_sum - c_sum) % nsa == 0:
                    # Right/Left edge
                    h[j, k] = float(1)

                elif (j_sum - k_sum) == 1 and not (j_sum - c_sum) % nsa == 1:
                    # Right/Left edge
                    h[j, k] = float(1)

                else:
                    continue

            else:
                continue

    queue.put(h)


def distribute(n_items, n_processes, i):
    """
    Distributes processes among processors
    :param n_items: Total no. of items
    :param n_processes: No. of processors/cores/threads
    :param i: Iterator over n_processes
    :return: Start point of ith process
    :return: Stop point of ith process

    """
    items_per_process = n_items // n_processes  # Integer division
    start = i * items_per_process

    # For last process, appends all remaining items to last core
    if i == n_processes - 1:
        stop = n_items
    else:
        stop = items_per_process * (i + 1)

    return start, stop


def parallel_call_hamiltonian(e_states, nos, nsa, nop):
    """
    Multiple parallel calls to hamiltonian_2d.
    :param e_states: Array of eigenstates
    :param nos: No. of states
    :param nsa: Shape of lattice.
    :param nop: No. of particles
    :return: Hamiltonian matrix

    """
    process_list = []
    queue = mp.Queue()  # Setting up a queue to store each processes' output
    h = np.zeros(shape=(nos, nos), dtype=np.float32)
    # No. of processes to create for parallel processing
    n_processes = mp.cpu_count()

    for i in range(n_processes):
        start, stop = distribute(nos, n_processes, i)
        args = (start, stop, nos, nsa, nop, e_states, queue, h)

        process = mp.Process(target=hamiltonian_2d, args=args)
        process_list.append(process)  # Create list of processes
        process.start()

    for i in range(n_processes):  # Retrieves output from queue
        h += queue.get()

    while not queue.empty():  # Clear queue
        h += queue.get()

    for jobs in process_list:  # Joins processes together
        jobs.join()

    return h


def eigenvalvec(h):
    """
    Calculates eigenvectors and eigenvalues used Pade algorithm
    (link to OpenBLAS Fortran libraries for parallel processing)
    :param h: Hamiltonian matrix
    :return: Real eigenvalues
    :return: Complex eigenvectors

    """
    eigenvalues, eigenvectors = la.eig(h, check_finite=False)

    # Sort eigenvalues and eigenvectors by ascending eigenvalue
    idx = eigenvalues.argsort()
    eigenvectors = eigenvectors[:, idx]
    eigenvalues = eigenvalues[idx]

    return eigenvalues.real, eigenvectors
