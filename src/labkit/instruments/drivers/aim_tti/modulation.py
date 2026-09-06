"""Modulation — **not available on the TGR6000**.

The TGR6000 is a fast-sweep CW signal generator. Its remote command set
(Instruction Manual Iss 9, "Command List") contains **no** AM, FM, ΦM or pulse
modulation commands, and the specification lists no modulation capability: the
only occurrence of "FM" in the manual is the *residual FM* noise figure of the
carrier. There is therefore nothing to drive here.

This menu is provided so the capability is *discoverable* rather than silently
missing: every modulation setter raises :class:`ModulationNotSupportedError`
with a clear message, and :meth:`Modulation.is_supported` returns ``False``. If a
modulation-capable Aim-TTi generator is added later, it can override this menu
with real commands.
"""

from __future__ import annotations

from ...base import Menu

__all__ = ["Modulation", "ModulationNotSupportedError"]


class ModulationNotSupportedError(NotImplementedError):
    """Raised when modulation is requested on a generator that has none.

    The TGR6000 exposes no modulation commands over its remote interface, so the
    :class:`Modulation` menu cannot carry out AM/FM/ΦM/pulse requests.
    """


class Modulation(Menu):
    """Modulation control — unsupported on the TGR6000 (every setter raises).

    See the module docstring: the TGR6000 has no modulation commands. The
    methods exist to document that fact where a user would look for it.
    """

    def is_supported(self) -> bool:
        """Return ``False``: this generator has no modulation capability."""
        return False

    def _unsupported(self, feature: str) -> "None":
        raise ModulationNotSupportedError(
            f"{feature} modulation is not available on the TGR6000: its remote "
            "command set defines no modulation commands (Instruction Manual "
            "Iss 9, 'Command List')."
        )

    def set_am(self, *args: object, **kwargs: object) -> None:
        """Amplitude modulation — unsupported; raises :class:`ModulationNotSupportedError`."""
        self._unsupported("AM")

    def set_fm(self, *args: object, **kwargs: object) -> None:
        """Frequency modulation — unsupported; raises :class:`ModulationNotSupportedError`."""
        self._unsupported("FM")

    def set_pm(self, *args: object, **kwargs: object) -> None:
        """Phase modulation — unsupported; raises :class:`ModulationNotSupportedError`."""
        self._unsupported("Phase (ΦM)")

    def set_pulse(self, *args: object, **kwargs: object) -> None:
        """Pulse modulation — unsupported; raises :class:`ModulationNotSupportedError`."""
        self._unsupported("Pulse")

    def disable(self) -> None:
        """Disable modulation — a no-op, since the TGR6000 is always unmodulated."""
        return None
