from dataclasses import dataclass
import logging
import types
from enum import Enum

import numpy as np
import scipy.linalg as sla
import cmath as cm

from transforms.frft import *
from transforms.fcc_fourier.fcc import *


class ThinBody2d:

    def __init__(self, x1_m: float, x2_m: float, eps_r: complex):
        self.x1_m = x1_m
        self.x2_m = x2_m
        self.eps_r = eps_r

    def get_intersecting_intervals(self, x_m):
        pass


class Plate(ThinBody2d):

    def __init__(self, x0_m, z1_m, z2_m, width_m, eps_r):
        self.x1_m = x0_m - width_m / 2
        self.x2_m = x0_m + width_m / 2
        self.z1_m = z1_m
        self.z2_m = z2_m
        self.eps_r = eps_r

    def get_intersecting_intervals(self, x_m):
        if self.x1_m <= x_m <= self.x2_m:
            return [(self.z1_m, self.z2_m)]
        else:
            return []


class SpectralIntegrationMethod(Enum):
    fractional_ft = 1,
    fcc = 2


@dataclass
class ThinScatteringComputationalParams:
    max_p_k0: float
    p_grid_size: int
    x_grid_size: int
    x_min_m: float
    x_max_m: float
    z_min_m: float
    z_max_m: float
    quadrature_points: int
    alpha: float
    spectral_integration_method: SpectralIntegrationMethod


class ThinScatteringDebugData:

    def __init__(self):
        self.phi = None
        self.rhs = None


class ThinScattering:

    def __init__(self, wavelength, bodies, params: ThinScatteringComputationalParams, fur_q_func: types.FunctionType = None, save_debug=False):
        self.bodies = bodies
        self.params = params
        self.k0 = 2 * cm.pi / wavelength
        self.max_p = self.params.max_p_k0 * self.k0
        #self.p_computational_grid, self.d_p = np.linspace(-self.max_p, self.max_p, self.params.p_grid_size, retstep=True)
        if self.params.spectral_integration_method == SpectralIntegrationMethod.fractional_ft:
            self.p_computational_grid = get_fcft_grid(self.params.p_grid_size, 2 * self.max_p)
            self.p_grid_is_regular = True
            self.d_p = self.p_computational_grid[1] - self.p_computational_grid[0]
        elif self.params.spectral_integration_method == SpectralIntegrationMethod.fcc:
            self.p_computational_grid = chebyshev_grid(-self.max_p, self.max_p, self.params.p_grid_size)
            self.p_grid_is_regular = False
            t = -np.concatenate((self.p_computational_grid[1::] - self.p_computational_grid[0:-1:],
                                 [self.p_computational_grid[-1] - self.p_computational_grid[-2]]))
            _, self.d_p = np.meshgrid(self.p_computational_grid, t, indexing='ij')
        self.x_computational_grid, self.dx = np.linspace(self.params.x_min_m, self.params.x_max_m, self.params.x_grid_size, retstep=True)
        #self.z_computational_grid, self.dz = np.linspace(self.params.z_min_m, self.params.z_max_m, retstep=True)
        self.z_computational_grid = get_fcft_grid(self.params.p_grid_size, self.params.z_max_m * 2)
        self.dz = self.z_computational_grid[1] - self.z_computational_grid[0]

        self.quad_x_grid = np.empty((len(self.bodies), self.params.quadrature_points))
        self.quad_weights = np.empty((len(self.bodies), self.params.quadrature_points))
        for body_index, body in enumerate(self.bodies):
            if self.params.quadrature_points == 1:
                self.quad_x_grid[body_index] = np.array([(body.x1_m + body.x2_m) / 2])
                self.quad_weights[body_index] = np.array([body.x2_m - body.x1_m])
            else:
                self.quad_x_grid[body_index, :], dx = np.linspace(body.x1_m, body.x2_m, self.params.quadrature_points, retstep=True)
                self.quad_weights[body_index, :] = np.concatenate(([dx / 2], np.repeat(dx, self.params.quadrature_points - 2), [dx / 2]))

        if fur_q_func is None:
            self.qrc_q = self.p_computational_grid*0 + 1 / cm.sqrt(2*cm.pi)
        else:
            self.qrc_q = fur_q_func(self.p_computational_grid)

        self.super_ker_size = len(self.p_computational_grid) * self.params.quadrature_points * len(bodies)
        gms = self.super_ker_size**2 * 16 /1024/1024
        logging.debug("matrix %d x %d, size = %d mb", self.super_ker_size, self.super_ker_size, gms)

        self.debug_data = ThinScatteringDebugData() if save_debug else None

    def green_function(self, x, xsh, p):
        if len(p.shape) == 2:
            xv, xshv, pv = x, xsh, p
        else:
            xv, xshv, pv = np.meshgrid(x, xsh, p, indexing='ij')
        gv = -1 / (2 * self._gamma(pv)) * np.exp(-self._gamma(pv) * np.abs(xv - xshv))
        return np.squeeze(gv)

    def _gamma(self, p):
        alpha = self.params.alpha
        a = np.sqrt((np.sqrt((self.k0 ** 2 - p ** 2) ** 2 + (alpha*self.k0 ** 2) ** 2) - (self.k0 ** 2 - p ** 2)) / 2)
        d = -np.sqrt((np.sqrt((self.k0 ** 2 - p ** 2) ** 2 + (alpha*self.k0 ** 2) ** 2) + (self.k0 ** 2 - p ** 2)) / 2)
        return a + 1j*d

    def _ker(self, body_number_i, body_number_j, i, j):
        pv, pshv = np.meshgrid(self.p_computational_grid, self.p_computational_grid, indexing='ij')
        return self.k0**2 / cm.sqrt(2*cm.pi) * self._body_z_fourier(body_number_i, self.quad_x_grid[body_number_i][i], pv - pshv) * \
                self._int_green_f(self.quad_weights[body_number_i][i], self.quad_x_grid[body_number_i][i], self.quad_x_grid[body_number_j][j], pshv) * self.d_p
            #self.green_function(self.quad_x_grid[body_number_i][i], self.quad_x_grid[body_number_j][j], pshv) * self.quad_weights[body_number_i][i] * self.d_p

    def _rhs(self, body_number, i):
        pv, pshv = np.meshgrid(self.p_computational_grid, self.p_computational_grid, indexing='ij')
        _, qshv = np.meshgrid(self.p_computational_grid, self.qrc_q, indexing='ij')
        m = self._body_z_fourier(body_number, self.quad_x_grid[body_number][i], pv - pshv) * \
            self._int_green_f(self.quad_weights[body_number][i], self.quad_x_grid[body_number][i], 0, pshv) * qshv
            #self.green_function(self.quad_x_grid[body_number][i], 0, pshv) * qshv * self.quad_weights[body_number][i]

        return np.sum(m * self.d_p, axis=1)    #TODO improve integral approximation??

    def _body_z_fourier(self, body_number, x_m, p):
        intervals = self.bodies[body_number].get_intersecting_intervals(x_m)
        res = np.zeros(p.shape, dtype=complex)
        for (a, b) in intervals:
            f = 1j / p * (np.exp(-1j * p * b) - np.exp(-1j * p * a))
            f[abs(p) < 0.0000001] = b - a
            res += f

        res *= 1 / cm.sqrt(2*cm.pi) * (self.bodies[body_number].eps_r - 1)
        return res

    def _super_ker(self):
        sk = np.empty((self.super_ker_size, self.super_ker_size), dtype=complex)
        ks = len(self.p_computational_grid)
        t = len(self.p_computational_grid) * self.params.quadrature_points
        for body_i in range(0, len(self.bodies)):
            for body_j in range(0, len(self.bodies)):
                for x_i in range(0, len(self.quad_x_grid[body_i])):
                    for x_j in range(0, len(self.quad_x_grid[body_j])):
                        sk[(body_i*t + ks*x_i):(body_i*t + ks*(x_i + 1)):, (body_j*t + ks*x_j):(body_j*t + ks*(x_j + 1)):] = \
                            self._ker(body_i, body_j, x_i, x_j)
        return sk

    def _super_rhs(self):
        rs = np.empty(self.super_ker_size, dtype=complex)
        ks = len(self.p_computational_grid)
        t = len(self.p_computational_grid) * self.params.quadrature_points
        for body_i in range(0, len(self.bodies)):
            for x_i in range(0, len(self.quad_x_grid[body_i])):
                rs[(body_i*t + ks*x_i):(body_i*t + ks*(x_i + 1)):] = self._rhs(body_i, x_i)
        return rs

    def _int_green_f(self, h, xi, xj, p):
        if abs(xi - xj) < 0.00000001:
            return 1 / self._gamma(p)**2 * (np.exp(-self._gamma(p)*h/2)-1)
        else:
            return 1 / (2*self._gamma(p)**2) *np.exp(-self._gamma(p)*abs(xi-xj))*(np.exp(-self._gamma(p)*h/2) - np.exp(self._gamma(p)*h/2))
        return self.green_function(xi, xj, p) * h

    def calculate(self):
        if len(self.bodies) > 0:
            logging.debug("Preparing kernel")
            ker = self._super_ker()
            logging.debug("Preparing right-hand side")
            rhs = self._super_rhs()
            #logging.debug("||ker|| = %d, cond(ker) = %d", np.linalg.norm(ker), np.linalg.cond(ker))
            #logging.debug("||rhs|| = %d", np.linalg.norm(rhs))
            left = np.eye(self.super_ker_size) + ker
            logging.debug("Solving system of integral equations")
            super_phi = sla.solve(left, rhs)
            #logging.debug("||s_phi|| = %d", np.linalg.norm(super_phi))

        if self.debug_data:
            self.debug_data.phi = super_phi
            self.debug_data.rhs = rhs

        logging.debug("Preparing psi")
        ks = len(self.p_computational_grid)
        t = len(self.p_computational_grid) * self.params.quadrature_points
        psi = self.green_function(self.x_computational_grid, 0, self.p_computational_grid) * self.qrc_q
        for body_i in range(0, len(self.bodies)):
            for x_i in range(0, len(self.quad_x_grid[body_i])):
                phi = super_phi[(body_i*t + ks*x_i):(body_i*t + ks*(x_i + 1)):]
                psi += -self.k0**2/cm.sqrt(2*cm.pi) * self.green_function(
                    self.x_computational_grid, self.quad_x_grid[body_i][x_i], self.p_computational_grid) * phi

        logging.debug("Calculating inverse Fourier transform")
        if self.params.spectral_integration_method == SpectralIntegrationMethod.fractional_ft:
            res = ifcft(psi, 2 * self.max_p, 2 * self.params.z_max_m)
        else:
            res = 1 / cm.sqrt(2 * cm.pi) * FCCFourier(2 * self.max_p, self.params.p_grid_size, -self.z_computational_grid).forward(psi.T, -self.max_p, self.max_p).T
        return res
