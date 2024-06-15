

"""Classes und functions for Gnucash's business section.
"""

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
        gnc_class_name = "gnc" + cls.gnc_class(book).GetTypeString()
        query.search_for(gnc_class_name)
        entities = []
        for result in query.run():
            ent = cls.gnc_class(instance=result)
            entities.append(cls(ent))
            # example methods: https://code.gnucash.org/docs/STABLE/group__Vendor.html
            print(ent.GetName())
        return entities

    def clone_to(self, other: gnucash.Book):
        """Create a copy of this Entity in the book ``other``.

Implementing classes must reimplement the ``_update_specific(...)`` method.

Parameters
----------
other: gnucash.Book
    The Gnucash book to which this Entity shall be cloned.
        """
        # Create object
        clone_ptr = self.gnc_class.Create(other)
        clone = gnucash_business.Vendor(instance=clone_ptr)

        # Helper objects
        curr_old = self._bas.GetCurrency()
        curr_clone = target.get_table().lookup("CURRENCY", curr_old.get_mnemonic())

        # Set common properties
        clone.SetID(self._base.GetID())
        clone.SetName(self._base.GetName())
        clone.SetCurrency(curr_clone)

        # Address is in a separate object
        addr_old = self._base.GetAddr()
        addr_clone = clone.GetAddr()
        addr_clone.SetName(addr_old.GetName())
        addr_clone.SetAddr1(addr_old.GetAddr1())
        from IPython import embed
        embed()

    @abc.abstractmethod
    def _update_specific(self, other: Entity) -> None:
        """Set everything in ``other`` that is not common to all Entity classes.

More specifically, by default, the following properties are set already:

- ID
- Name
- Currency
- Address

Everything else should be set in this method.
        """
        pass


class Vendor(Entity):
    # gnc_class_name = "gncVendor"
    gnc_class = gnucash_business.Vendor
