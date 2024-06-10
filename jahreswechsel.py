#!/usr/bin/env python3

# Utility for creating a new book, for example at the beginning of the year.
#
# Based upon `new_book_with_opening_balances.py` from the Gnucash Python examples.
#
# Copyright (C) 2009, 2010 Mark Jenkins, ParIT Worker Co-operative <transparency@parit.ca>
# Copyright (C) 2024 Quazgar <quazgar@posteo.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, contact:
# Free Software Foundation           Voice:  +1-617-542-5942
# 51 Franklin Street, Fifth Floor    Fax:    +1-617-542-2652
# Boston, MA  02110-1301,  USA       gnu@gnu.org
#
# @author Mark Jenkins, ParIT Worker Co-operative <mark@parit.ca>
# @author Quazgar <quazgar@posteo.de>

# @file
#   @brief Replicate the account structure of a
#   book and apply basis opening balances from the original

import argparse
import os
from datetime import date

# import piecash

from gnucash import (
    Session, Account, Transaction, Split, GncNumeric, SessionOpenMode)
from gnucash.gnucash_core_c import \
    GNC_DENOM_AUTO, GNC_HOW_DENOM_EXACT, \
    ACCT_TYPE_ASSET, ACCT_TYPE_BANK, ACCT_TYPE_CASH, ACCT_TYPE_CHECKING, \
    ACCT_TYPE_CREDIT, ACCT_TYPE_EQUITY, ACCT_TYPE_EXPENSE, ACCT_TYPE_INCOME, \
    ACCT_TYPE_LIABILITY, ACCT_TYPE_MUTUAL, ACCT_TYPE_PAYABLE, \
    ACCT_TYPE_RECEIVABLE, ACCT_TYPE_STOCK, ACCT_TYPE_ROOT, ACCT_TYPE_TRADING

# This script takes a gnucash url
# and creates a new file/db at a second url that has the same
# account tree and an equivalent opening balance on all the simple balance
# sheet accounts (not for income and expense accounts)
#
# This is done a per currency basis, one opening balance account for each
#
# For non-simple balance sheet accounts (like payable, recievable, stock,
# mutual, and trading, you'll have to put the opening balance in yourself
#
# Invocation examples:
# python3 new_book_with_opening_balances.py \
#   '/home/mark/test.gnucash'
#   'sqlite3:///home/mark/new_test.gnucash'
#
# python3 new_book_with_opening_balances.py \
#   '/home/mark/test.gnucash' \
#   'xml:///crypthome/mark/parit-financial-system/new_test.gnucash'
#
# Remember that the gnucash python package has to be in your PYTHONPATH
# if you're installed GnuCash in a non-standard location, you'll have to do
# something like this
# export PYTHONPATH=gnucash_install_path/lib/python2.x/site-packages/

# argv[1] should be the path to an existing gnucash file/database
# For a file, simply pass the pathname. GnuCash will determine the data format
# xml or sqlite3 automatically.
# For a database you can use these forms:
#   mysql://user:password@host/dbname
#   postgres://user:password@host[:port]/dbname (the port is optional)
#
# argv[2] should be the path for the new gnucash file/database
# For a file, simply pass the pathname prefixed with the requested data format
# like:
#   xml:///home/blah/blah.gnucash
#   sqlite3:///home/blah/blah.gnucash
# Paths can also be relative, for example:
#   xml://from-here/to/there/blah.gnucash
# For a database you can use these forms:
#   mysql://user:password@host/dbname
#   postgres://user:password@host[:port]/dbname (the port is optional)


OPENING_DATE = (1, 1, 2011)  # day, month, year

# possible account types of interest for opening balances
ACCOUNT_TYPES_TO_OPEN = set((
    ACCT_TYPE_BANK,
    ACCT_TYPE_CASH,
    ACCT_TYPE_CREDIT,
    ACCT_TYPE_ASSET,
    ACCT_TYPE_LIABILITY,
    ACCT_TYPE_STOCK,
    ACCT_TYPE_MUTUAL,
    ACCT_TYPE_INCOME,
    ACCT_TYPE_EXPENSE,
    ACCT_TYPE_EQUITY,
    ACCT_TYPE_RECEIVABLE,
    ACCT_TYPE_PAYABLE,
    ACCT_TYPE_TRADING,
))

# You don't need an opening balance for income and expenses, past income
# and expenses should be in Equity->retained earnings
# so we remove them from the above set
ACCOUNT_TYPES_TO_OPEN = ACCOUNT_TYPES_TO_OPEN.difference(set((
    ACCT_TYPE_INCOME,
    ACCT_TYPE_EXPENSE,
)))

# This script isn't capable of properly creating the lots required for
# STOCK, MUTUAL, RECEIVABLE, and PAYABLE -- you'll have to create opening
# balances for them manually; so they are not included in the set for
# opening balances
ACCOUNT_TYPES_TO_OPEN = ACCOUNT_TYPES_TO_OPEN.difference(set((
    ACCT_TYPE_STOCK,
    ACCT_TYPE_MUTUAL,
    ACCT_TYPE_RECEIVABLE,
    ACCT_TYPE_PAYABLE,
)))

# this script isn't capable of properly setting up the transactions for
# ACCT_TYPE_TRADING, you'll have to create opening balances for them manually;
# so, they are not included in the set of accounts used for opening balances
ACCOUNT_TYPES_TO_OPEN.remove(ACCT_TYPE_TRADING)

OPENING_BALANCE_ACCOUNT = ('Equity', 'Opening Balances')

# if possible, this program will try to use the account above for the
# currency listed below, and a variation of the above
# Equity->"Opening Balances Symbol" for all other currencies
PREFERED_CURRENCY_FOR_SIMPLE_OPENING_BALANCE = ("CURRENCY", "CAD")


def initialize_split(book, value, account, trans):
    split = Split(book)
    split.SetValue(value)
    split.SetAccount(account)
    split.SetParent(trans)
    return split


def record_opening_balance(original_account, new_account, new_book,
                           opening_balance_per_currency, commodity_tuple
                           ):
    # create an opening balance if the account type is right
    if new_account.GetType() in ACCOUNT_TYPES_TO_OPEN:
        final_balance = original_account.GetBalance()
        if final_balance.num() != 0:
            # if there is a new currency type, associate with the currency
            # a Transaction which will be the opening transaction for that
            # currency and a GncNumeric value which will be the opening
            # balance account amount
            if commodity_tuple not in opening_balance_per_currency:
                trans = Transaction(new_book)
                trans.BeginEdit()
                opening_balance_per_currency[commodity_tuple] = (
                    trans, GncNumeric(0, 1))
            trans, total = opening_balance_per_currency[commodity_tuple]

            new_total = total.sub(
                final_balance,
                GNC_DENOM_AUTO, GNC_HOW_DENOM_EXACT)

            initialize_split(
                new_book,
                final_balance,
                new_account, trans)
            opening_balance_per_currency[commodity_tuple] = \
                (trans, new_total)


def recursively_build_account_tree(original_parent_account,
                                   new_parent_account,
                                   new_book,
                                   new_commodity_table,
                                   opening_balance_per_currency,
                                   account_types_to_open):

    for child in original_parent_account.get_children():
        original_account = child
        new_account = Account(new_book)
        # attach new account to its parent
        new_parent_account.append_child(new_account)

        # copy simple attributes
        for attribute in ('Name', 'Type', 'Description', 'Notes',
                          'Code', 'TaxRelated', 'Placeholder'):
            # new_account.SetAttribute( original_account.GetAttribute() )
            getattr(new_account, 'Set' + attribute)(
                getattr(original_account, 'Get' + attribute)())

        # copy commodity
        orig_commodity = original_account.GetCommodity()
        namespace = orig_commodity.get_namespace()
        mnemonic = orig_commodity.get_mnemonic()
        new_commodity = new_commodity_table.lookup(namespace, mnemonic)
        if new_commodity == None:
            new_commodity = orig_commodity.clone(new_book)
            new_commodity_table.insert(new_commodity)
        new_account.SetCommodity(new_commodity)

        record_opening_balance(original_account, new_account,
                               new_book, opening_balance_per_currency,
                               (namespace, mnemonic),
                               )

        recursively_build_account_tree(original_account,
                                       new_account,
                                       new_book,
                                       new_commodity_table,
                                       opening_balance_per_currency,
                                       account_types_to_open)


def reconstruct_account_name_with_mnemonic(account_tuple, mnemonic):
    opening_balance_account_pieces = list(account_tuple)
    opening_balance_account_pieces[
        len(opening_balance_account_pieces) - 1] += " - " + mnemonic
    return opening_balance_account_pieces


def find_or_make_account(account_tuple, root_account, book,
                         currency):
    current_account_name, account_path = account_tuple[0], account_tuple[1:]
    current_account = root_account.lookup_by_name(current_account_name)
    if current_account == None:
        current_account = Account(book)
        current_account.SetName(current_account_name)
        current_account.SetCommodity(currency)
        root_account.append_child(current_account)

    if len(account_path) > 0:
        return find_or_make_account(account_path, current_account, book,
                                    currency)
    else:
        account_commod = current_account.GetCommodity()
        if (account_commod.get_mnemonic(),
            account_commod.get_namespace()) == \
            (currency.get_mnemonic(),
             currency.get_namespace()):
            return current_account
        else:
            return None


def choke_on_none_for_no_account(opening_account, extra_string):
    if opening_account == None:
        raise Exception("account currency and name mismatch, " + extra_string)


def create_opening_balance_transaction(commodtable, namespace, mnemonic,
                                       new_book_root, new_book,
                                       opening_trans, opening_amount,
                                       simple_opening_name_used):
    currency = commodtable.lookup(namespace, mnemonic)
    assert (currency.get_instance() is not None)

    if simple_opening_name_used:
        account_pieces = reconstruct_account_name_with_mnemonic(
            OPENING_BALANCE_ACCOUNT,
            mnemonic)
        opening_account = find_or_make_account(
            account_pieces, new_book_root, new_book, currency)
        choke_on_none_for_no_account(opening_account,
                                     ', '.join(account_pieces))
    else:
        opening_account = find_or_make_account(OPENING_BALANCE_ACCOUNT,
                                               new_book_root, new_book,
                                               currency)
        simple_opening_name_used = True
        if opening_account is None:
            account_pieces = reconstruct_account_name_with_mnemonic(
                OPENING_BALANCE_ACCOUNT,
                mnemonic)
            opening_account = find_or_make_account(
                account_pieces, new_book_root, new_book, currency)
            choke_on_none_for_no_account(opening_account,
                                         ', '.join(account_pieces))

    # we don't need to use the opening balance account at all if all
    # the accounts being given an opening balance balance out
    if opening_amount.num() != 0:
        initialize_split(new_book, opening_amount, opening_account,
                         opening_trans)

    opening_trans.SetDate(*OPENING_DATE)
    opening_trans.SetCurrency(currency)
    opening_trans.SetDescription("Opening Balance")
    opening_trans.CommitEdit()

    return simple_opening_name_used


def duplicate_with_opening_balance(old: str, new: str) -> None:
    """Create a new Gnucash file."""
    new = os.path.abspath(new)
    new_sqlite = "sqlite3://" + new
    if not os.path.exists(new):
        new_book_session = Session(new_sqlite, SessionOpenMode.SESSION_NEW_STORE)
        # new_book = new_book_session.get_book()
        # new_book_session.save()
        new_book_session.end()
    else:
        print(f"Warnung! Datei {new} existiert bereits.")

    with (Session(old, SessionOpenMode.SESSION_READ_ONLY) as original_book_session,
          Session(new_sqlite, SessionOpenMode.SESSION_NORMAL_OPEN) as new_book_session):
        new_book = new_book_session.get_book()
        new_book_root = new_book.get_root_account()

        commodtable = new_book.get_table()
        # we discovered that if we didn't have this save early on, there would
        # be trouble later
        new_book_session.save()

        #######################
        # Make dict of balances
        #######################
        opening_balance_per_currency: dict = {}
        recursively_build_account_tree(
            original_book_session.get_book().get_root_account(),
            new_book_root,
            new_book,
            commodtable,
            opening_balance_per_currency,
            ACCOUNT_TYPES_TO_OPEN
        )

        from IPython import embed; embed()

        (namespace, mnemonic) = PREFERED_CURRENCY_FOR_SIMPLE_OPENING_BALANCE
        if (namespace, mnemonic) in opening_balance_per_currency:
            opening_trans, opening_amount = opening_balance_per_currency[
                (namespace, mnemonic)]
            simple_opening_name_used = create_opening_balance_transaction(
                commodtable, namespace, mnemonic,
                new_book_root, new_book,
                opening_trans, opening_amount,
                False)
            del opening_balance_per_currency[
                PREFERED_CURRENCY_FOR_SIMPLE_OPENING_BALANCE]
        else:
            simple_opening_name_used = False

        old_book = original_book_session.get_book()

        from IPython import embed
        embed()

        for (namespace, mnemonic), (opening_trans, opening_amount) in \
                opening_balance_per_currency.items():
            simple_opening_name_used = create_opening_balance_transaction(
                commodtable, namespace, mnemonic,
                new_book_root, new_book,
                opening_trans, opening_amount,
                simple_opening_name_used)


def _parse_arguments():
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Create a new Gnucash file from the account"
                                     " balances of an existing file.")
    parser.add_argument("-i", "--infile", help="Input file (of the old year / booking period).",
                        type=str, required=True)
    parser.add_argument('-o', '--outfile', help="Filename where the new file shall be written.",
                        type=str, required=True)

    return parser.parse_args()


def main():

    args = _parse_arguments()
    assert args.infile, "Must give a valid infile."
    assert args.outfile, "Must give a valid outfile."
    duplicate_with_opening_balance(old=args.infile, new=args.outfile)


if __name__ == "__main__":
    main()
