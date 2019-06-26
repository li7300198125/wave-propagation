import cmath as cm
import numpy as np

__author__ = 'Lytaev Mikhail (mikelytaev@gmail.com)'


class Source:

    def max_angle(self):
        pass


class GaussAntenna(Source):

    def __init__(self, *, freq_hz=None, wavelength=None, height, beam_width, eval_angle, polarz):
        self.height = height
        if freq_hz is None:
            self.wavelength = wavelength
            self.freq_hz = 3e8 / self.wavelength
        else:
            self.freq_hz = freq_hz
            self.wavelength = 3e8 / freq_hz
        self.k0 = 2 * cm.pi / self.wavelength
        self.beam_width = beam_width
        self.eval_angle = eval_angle
        self.polarz = polarz
        self._ww = cm.sqrt(2 * cm.log(2)) / (self.k0 * cm.sin(beam_width * cm.pi / 180 / 2))

    def _ufsp(self, z):
        return 1 / (cm.sqrt(cm.pi) * self._ww) * np.exp(-1j * self.k0 * np.sin(self.eval_angle * cm.pi / 180) * z) * \
               np.exp(-((z - self.height) / self._ww) ** 2)

    def _ufsn(self, z):
        return 1 / (cm.sqrt(cm.pi) * self._ww) * np.exp(-1j * self.k0 * np.sin(self.eval_angle * cm.pi / 180) * (-z)) * \
               np.exp(-((-z - self.height) / self._ww) ** 2)

    def aperture(self, z):
        if self.polarz.upper() == 'H':
            return self._ufsp(z) - self._ufsn(z)
        else:
            return self._ufsp(z) + self._ufsn(z)

    def max_angle(self):
        return self.beam_width + abs(self.eval_angle)


class GaussSource3D:

    def __init__(self, *, freq_hz, height, ver_beamwidth, hor_beamwidth, polarz):
        self.freq_hz = freq_hz
        self.wavelength = 3e8 / freq_hz
        self.height = height
        self.ver_beamwidth = ver_beamwidth
        self.hor_beamwidth = hor_beamwidth
        self.polarz = polarz
        self.k0 = 2 * cm.pi / self.wavelength

    def aperture(self, y_grid, z_grid):
        ww_ver = cm.sqrt(2 * cm.log(2)) / (self.k0 * cm.sin(self.ver_beamwidth * cm.pi / 180 / 2))
        ww_hor = cm.sqrt(2 * cm.log(2)) / (self.k0 * cm.sin(self.hor_beamwidth * cm.pi / 180 / 2))
        ver_ant = 1 / (cm.sqrt(cm.pi) * ww_ver) * np.exp(-((z_grid - self.height) / ww_ver) ** 2)
        hor_ant = 1 / (cm.sqrt(cm.pi) * ww_hor) * np.exp(-(y_grid / ww_hor) ** 2)
        hor = np.tile(hor_ant, (len(z_grid), 1)).transpose()
        ver = np.tile(ver_ant, (len(y_grid), 1))
        return hor * ver