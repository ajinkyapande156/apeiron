# apeiron/core/base_module.py

from abc import ABC, abstractmethod

class BaseModule(ABC):
    """Abstract base class for pluggable modules."""

    @abstractmethod
    def validate(self):
        """Perform validation using the module's validation component."""
        pass

    @abstractmethod
    def generate_matrix(self):
        """Generate matrix using the module's matrix generator component."""
        pass

    @abstractmethod
    def generate_payload(self):
        """Generate payload using the module's payload generator component."""
        pass
