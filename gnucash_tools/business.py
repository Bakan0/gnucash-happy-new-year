

"""Classes und functions for Gnucash's business section.
"""

from __future__ import annotations

import abc
from abc import ABC
from typing import Optional

import gnucash
from gnucash import gnucash_business


class Entity(ABC):
    """Base class for Customers, Vendors, Employees.
    """

    # gnc_class_name: Optional[str] = None  # e.g. "gncVendor"

    # gnc_class: Must be set by implementing classes.
    gnc_class: type[gnucash_business.GnuCashBusinessEntity]

    def __init__(self, base_obj: gnucash_business.GnuCashBusinessEntity):
        """
Parameters
----------
base_obj: gnucash_business.GnuCashBusinessEntity
    The basic GnuCash entity upon which this object is based.
        """
        self._base = base_obj

    @classmethod
    def get_all(cls, book: gnucash.Book):
        # Code adapted from
        # https://github.com/Gnucash/gnucash/blob/stable/bindings/python/example_scripts/rest-api/gnucash_rest.py
        query = gnucash.Query()
        query.set_book(book)
        gnc_class_name = "gnc" + cls.gnc_class.__name__
        query.search_for(gnc_class_name)
        entities = []
        for result in query.run():
            ent = cls.gnc_class(instance=result)
            entities.append(cls(ent))
        return entities

    def clone_to(self, other: gnucash.Book):
        """Create a copy of this Entity in the book ``other``.

Implementing classes must reimplement the ``_update_specific(...)`` method.

Parameters
----------
other: gnucash.Book
    The Gnucash book to which this Entity shall be cloned.
        """
        # example methods: https://code.gnucash.org/docs/STABLE/group__Vendor.html

        # Create object
        clone_ptr = self.gnc_class.Create(other)
        clone = type(self)(self.gnc_class(instance=clone_ptr))

        # Helper objects
        curr_old = self._base.GetCurrency()
        curr_clone = other.get_table().lookup("CURRENCY", curr_old.get_mnemonic())

        # Set common properties
        clone._base.SetID(self._base.GetID())
        clone._base.SetName(self._base.GetName())
        clone._base.SetActive(self._base.GetActive())
        clone._base.SetCurrency(curr_clone)

        # Address is in a separate object
        addr_old = self._base.GetAddr()
        addr_clone = clone._base.GetAddr()
        addr_clone.SetName(addr_old.GetName())
        addr_clone.SetAddr1(addr_old.GetAddr1())

        self._update_specific(other=clone)

    @abc.abstractmethod
    def _update_specific(self, other) -> None:
        """Set everything in ``other`` that is not common to all Entity classes.

More specifically, by default, the following properties are set already:

- ID
- Name
- Currency
- Address
- Active

Everything else should be set in this method.
        """
        pass


class Vendor(Entity):
    # gnc_class_name = "gncVendor"
    gnc_class = gnucash_business.Vendor

    def _update_specific(self, other: Vendor) -> None:
        """Set missing properties.

The missing properties are:
- Notes
- TaxIncluded
- Terms

Parameters
----------
other: Vendor
    The entity to update.
        """
        other._base.SetNotes(self._base.GetNotes())
        other._base.SetTaxIncluded(self._base.GetTaxIncluded())
        other._base.SetTerms(self._base.GetTerms())
