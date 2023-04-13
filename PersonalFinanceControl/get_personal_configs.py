import json
from typing import Any, Dict, List

from pynubank import Nubank

from PersonalFinanceControl import LocalManagementConstants


def get_secrets() -> Dict[str, Any]:
    with open(LocalManagementConstants.SECRETS_LOCATION, "r") as f:
        data = json.load(f)
    return data


def get_expense_plan() -> (
    Dict[str, List[Dict[str, float | int | str]] | Dict[str, Any]]
):
    expense_plan = get_secrets()["costs"]

    for variable_cost in expense_plan["variable"]:
        variable_cost["already_paid"] = bool(variable_cost["already_paid"])

    return expense_plan


def get_nubank_client() -> Nubank:
    secret_data = get_secrets()

    cpf = secret_data["cpf"]
    app_password = secret_data["app_password"]
    certificate_path = secret_data["certificate_path"]

    nu = Nubank()
    nu.authenticate_with_cert(cpf, app_password, certificate_path)
    return nu
