"""Module documentation example."""
import os
import pickle
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from PersonalFinanceControl import LocalManagementConstants, get_personal_configs


# TODO: make this a singleton
class NubankBill:
    def load_open_bill_details(self, use_cached: bool):
        (
            self.open_bill_details,
            self.open_bill_close_date,
        ) = self._get_open_bill_details(use_cached)
        if not use_cached:
            self._cache_open_bill_details(self.open_bill_details)

        self.open_bill_payments = self._get_open_bill_payments(self.open_bill_details)

    def _get_open_bill_payments(self, open_bill_details):
        open_bill_payments = pd.DataFrame(open_bill_details["bill"]["line_items"])

        # drop data that isnt a payment
        open_bill_payments.dropna(inplace=True, subset="charges")
        open_bill_payments.reset_index(inplace=True)

        return open_bill_payments

    def _get_open_bill_details(self, use_cached: bool):
        if not use_cached:
            return self._get_open_bill_details_online()

        return self._get_open_bill_details_cached()

    def _get_open_bill_details_cached(self):
        with open(LocalManagementConstants.CACHE_BILL_FILEPATH, "rb") as f:
            open_bill_details: List[Dict[str, Any]] = pickle.load(f)

        return open_bill_details, self._get_open_bill_close_date(open_bill_details)

    def _get_open_bill_details_online(self):
        nu = get_personal_configs.get_nubank_client()
        bills: List[Dict[str, Any]] = nu.get_bills()
        open_bill = self._get_open_bill(bills)
        open_bill_details = nu.get_bill_details(open_bill)

        return open_bill_details, self._get_open_bill_close_date(open_bill_details)

    def _get_open_bill_close_date(self, open_bill_details):
        return datetime.strptime(
            open_bill_details["bill"]["summary"]["close_date"], "%Y-%m-%d"
        )

    def _get_open_bill(self, bills):
        return next(filter(lambda bill: bill["state"] == "open", bills))

    def _cache_open_bill_details(self, open_bill_details):
        os.makedirs(LocalManagementConstants.CACHE_FOLDER, exist_ok=True)

        with open(LocalManagementConstants.CACHE_BILL_FILEPATH, "wb") as f:
            pickle.dump(open_bill_details, f)


# TODO: make this a singleton
class CostsAnalyzer:
    def load_costs(self):
        self.personal_costs_plan = get_personal_configs.get_expense_plan()
        self.fixed_costs_plan = self.personal_costs_plan["fixed"]
        self.variable_costs_plan = self.personal_costs_plan["variable"]

    def load_analyzed_costs(self, open_bill_payments, open_bill_close_date):
        self.fixed_costs_analyzed = self._get_fixed_costs_analyzed(
            open_bill_payments, self.fixed_costs_plan
        )

        self.variable_costs_analyzed = self._get_variable_costs_analyzed(
            self.variable_costs_plan, open_bill_close_date
        )

        self.all_costs_analyzed: pd.DataFrame = pd.concat(
            [self.fixed_costs_analyzed, self.variable_costs_analyzed], axis=0
        )

        self.extra_payments_sum = (
            self.all_costs_analyzed.loc[
                self.all_costs_analyzed["extra_payment"], "amount_pending"
            ].sum()
            * -1
        )

        self.variable_payments_open_sum = self.all_costs_analyzed.loc[
            (self.all_costs_analyzed["type"] == "variable")
            & (self.all_costs_analyzed["this_bill_payment"]),
            "amount_pending",
        ].sum()

        ignored_fixed_cost_titles = map(
            lambda fixed_cost: fixed_cost["title"], self.fixed_costs_plan
        )

        self.other_payments_sum = (
            open_bill_payments.loc[
                ~open_bill_payments["title"].isin(ignored_fixed_cost_titles), "amount"
            ].sum()
            / 100
        )

        self.payments_categorized = self._get_payments_categorized(open_bill_payments)

    def _get_payments_categorized(self, open_bill_payments: pd.DataFrame):
        payments_categorized = open_bill_payments.copy()

        payments_categorized = payments_categorized[
            ["title", "post_date", "category", "charges", "amount"]
        ]

        payments_categorized = payments_categorized.merge(
            self.all_costs_analyzed[["title", "type"]], how="left", on="title"
        )

        payments_categorized.loc[payments_categorized["type"].isna(), "type"] = "other"

        payments_categorized["amount"] /= 100

        return payments_categorized

    def _get_fixed_costs_analyzed(
        self,
        open_bill_payments: pd.DataFrame,
        fixed_costs_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        fixed_costs_status = []
        for fixed_cost in fixed_costs_list:
            fixed_cost_payments = open_bill_payments.loc[
                open_bill_payments["title"] == fixed_cost["title"]
            ]
            fixed_cost_amount_payed = fixed_cost_payments["amount"].sum() / 100

            amount_pending = fixed_cost["amount"] - fixed_cost_amount_payed

            cost_data = {
                "type": "fixed",
                "title": fixed_cost["title"],
                "amount_payed": fixed_cost_amount_payed,
                "amount_pending": amount_pending,
                "already_payed": amount_pending <= 0,
                "this_bill_payment": True,
                "extra_payment": amount_pending < 0,
            }
            fixed_costs_status.append(cost_data)

        return pd.DataFrame(fixed_costs_status)

    def _get_variable_costs_analyzed(
        self,
        variable_costs_list: List[Dict[str, Any]],
        bill_close_date: datetime,
    ) -> Dict[str, Any]:
        variable_costs_status = []
        for variable_cost in variable_costs_list:
            if variable_cost["already_payed"] is True:
                amount_pending = 0
            else:
                amount_pending = variable_cost["amount"]

            pay_due_date = datetime.strptime(variable_cost["payment_date"], "%Y/%m/%d")

            due_this_bill = pay_due_date < bill_close_date

            cost_data = {
                "type": "variable",
                "title": variable_cost["title"],
                "amount_payed": variable_cost["amount"] - amount_pending,
                "already_payed": variable_cost["already_payed"],
                "amount_pending": amount_pending,
                "this_bill_payment": due_this_bill,
                "extra_payment": amount_pending < 0,
            }
            variable_costs_status.append(cost_data)

        return pd.DataFrame(variable_costs_status)


def setup_CostsAnalyzer(nu_bill: NubankBill):
    cost_analyzer = CostsAnalyzer()
    cost_analyzer.load_costs()
    cost_analyzer.load_analyzed_costs(
        nu_bill.open_bill_payments, nu_bill.open_bill_close_date
    )
    return cost_analyzer


def setup_NubankBill(use_cached: bool):
    nu_bill = NubankBill()
    nu_bill.load_open_bill_details(use_cached)

    return nu_bill


@dataclass
class RequestedData:
    other_payments_sum: float
    planned_payments_analyzed: pd.DataFrame
    all_payments_categorized: pd.DataFrame
    close_date: str
    variable_payments_pending: float
    fixed_cost_extra_payments: float


def request_data(use_cached: bool) -> RequestedData:
    nu_bill = setup_NubankBill(use_cached)
    costs_analyzer = setup_CostsAnalyzer(nu_bill)
    data = RequestedData(
        **{
            "other_payments_sum": costs_analyzer.other_payments_sum,
            "planned_payments_analyzed": costs_analyzer.all_costs_analyzed,
            "all_payments_categorized": costs_analyzer.payments_categorized,
            "close_date": nu_bill.open_bill_close_date.strftime("%Y-%m-%d"),
            "variable_payments_pending": costs_analyzer.variable_payments_open_sum,
            "fixed_cost_extra_payments": costs_analyzer.extra_payments_sum,
        }
    )

    return data
