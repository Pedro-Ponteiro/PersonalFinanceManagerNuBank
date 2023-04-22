import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from tabulate import tabulate

from PersonalFinanceControl import PersonalFinanceControl
from PersonalFinanceControl.get_personal_configs import get_expense_plan


def info1():
    #     gastos variaveis deste mes (VALOR TOTAL)
    #     title	amount	post_date pago?
    expense_plan = get_expense_plan()["variable"]

    expense_plan = pd.DataFrame(expense_plan).sort_values(by="already_paid")

    total_pending = expense_plan.loc[~expense_plan["already_paid"], ["amount"]].sum()
    total_paid = expense_plan.loc[expense_plan["already_paid"], ["amount"]].sum()

    first_line = "Custo Variavel Pendente: " + str(total_pending[0])
    sec_line = "Custo Variavel Pago: " + str(total_paid[0])

    third_line = tabulate(
        expense_plan, headers="keys", tablefmt="psql", showindex=False
    )

    returned_str = "\n".join([first_line, sec_line, third_line])

    return returned_str


def info2(
    planned_payments_analyzed: pd.DataFrame, all_payments_categorized: pd.DataFrame
):
    #     gastos fixos deste mes (VALOR TOTAL)
    # nome	valor	data	pago?
    # join de planned_payments_analyzed e all_payments_categorized

    # Get payment dates
    all_payments_categorized = all_payments_categorized.copy()

    all_payments_categorized = all_payments_categorized.loc[
        all_payments_categorized["type"] == "fixed"
    ]

    all_payments_categorized = all_payments_categorized.groupby("title")[
        "post_date"
    ].last()

    # filter planned_payments by columns

    planned_payments_analyzed = planned_payments_analyzed.copy()

    planned_payments_analyzed = planned_payments_analyzed.loc[
        planned_payments_analyzed["type"] == "fixed",
        ["title", "amount_paid", "amount_pending", "extra_payment"],
    ]

    df_join = planned_payments_analyzed.join(
        all_payments_categorized,
        how="outer",
        on="title",
    )
    df_join = df_join.sort_values(by=["amount_pending", "amount_paid"], ascending=True)

    first_line = "Custo Fixo Pendente: " + str(df_join["amount_pending"].sum())
    sec_line = "Custo Fixo Pago: " + str(df_join["amount_paid"].sum())

    third_line = tabulate(df_join, headers="keys", tablefmt="psql", showindex=False)

    returned_str = "\n".join([first_line, sec_line, third_line])

    return returned_str


def info3(all_payments_categorized: pd.DataFrame):
    #     outros gastos (VALOR TOTAL)
    # nome	valor	data
    # filtro de all_payments_categorized
    all_payments_categorized = all_payments_categorized.copy()

    all_payments_categorized = all_payments_categorized.loc[
        all_payments_categorized["type"] == "other"
    ][["title", "amount", "post_date"]]

    total_paid = all_payments_categorized["amount"].sum()

    first_line = "Outros Pagamentos: " + str(total_paid)

    sec_line = tabulate(
        all_payments_categorized, headers="keys", tablefmt="psql", showindex=False
    )

    returned_str = "\n".join([first_line, sec_line])

    return returned_str


def info4():
    # Custo limite ($$)
    # só um print do que está no json
    return "Custo Limite: " + str(get_expense_plan()["costs_limit"])


def info5(all_payments_categorized: pd.DataFrame):
    # Grafico de custo por dia
    df = all_payments_categorized.copy()

    df["other_payments"] = df[["type", "amount"]].apply(
        lambda row: row["amount"] if row["type"] == "other" else 0, axis=1
    )
    df["planned_payments"] = df[["type", "amount"]].apply(
        lambda row: row["amount"] if row["type"] != "other" else 0, axis=1
    )

    # convert date column to datetime format
    df["post_date"] = pd.to_datetime(df["post_date"], dayfirst=True).dt.strftime(
        "%Y-%m-%d"
    )

    # groupby post_date and calculate cumulative sum of amount
    cumulative_sum = (
        df.groupby("post_date")[["amount", "other_payments", "planned_payments"]]
        .sum()
        .cumsum()
    )

    # create new dataframe with unique post_dates and corresponding cumulative sums
    df_cumulative = pd.DataFrame(
        {
            "post_date": cumulative_sum.index,
            "cumulative_sum": cumulative_sum["amount"].values,
            "cumulative_other_payments": cumulative_sum["other_payments"].values,
            "cumulative_planned_payments": cumulative_sum["planned_payments"].values,
        }
    )

    # create line plot with cumulative sum on y-axis and post_date on x-axis
    ax = sns.lineplot(
        x="post_date", y="cumulative_sum", data=df_cumulative, label="all_payments"
    )

    sns.lineplot(
        x="post_date",
        y="cumulative_other_payments",
        data=df_cumulative,
        label="other_payments",
        ax=ax,
    )

    sns.lineplot(
        x="post_date",
        y="cumulative_planned_payments",
        data=df_cumulative,
        label="planned_payments",
        ax=ax,
    )

    # customize x-axis tick labels
    ax.set_xticklabels(df_cumulative["post_date"], rotation=90)

    # add vertical grid lines
    ax.grid(axis="x", which="both", linestyle="--", color="grey")

    plt.title("Pagamentos Acumulados por Dia")

    plt.savefig("./PersonalFinanceControl/cache/payments_per_day.png")


def info6(all_payments_categorized: pd.DataFrame, planned_costs_analyzed: pd.DataFrame):
    # cálculo de custos x custo limite
    # CustoLimite -
    # (VariaveisPagos+FixosPagos+Outros) -
    # (VariaveisPendentes + FixosPendentes)
    # escrito para lembrar a formula
    # resultado

    # Custo limite: direto do json
    # Variaveis: soma de todas custos variaveis em planned_costs_analyzed
    # Fixos: soma de todas custos Fixos em planned_costs_analyzed
    # Outros: soma de todas custos "Outros" em all_payments_categorized
    cost_limit = get_expense_plan()["costs_limit"]

    planned_costs_analyzed = planned_costs_analyzed.copy()

    var_pending = planned_costs_analyzed.loc[
        planned_costs_analyzed["type"] == "variable", "amount_pending"
    ].sum()
    var_paid = planned_costs_analyzed.loc[
        planned_costs_analyzed["type"] == "variable", "amount_paid"
    ].sum()
    fixed_pending = planned_costs_analyzed.loc[
        planned_costs_analyzed["type"] == "fixed", "amount_pending"
    ].sum()
    fixed_paid = planned_costs_analyzed.loc[
        planned_costs_analyzed["type"] == "fixed", "amount_paid"
    ].sum()

    all_payments_categorized = all_payments_categorized.copy()

    other_payments_paid = all_payments_categorized.loc[
        all_payments_categorized["type"] == "other", "amount"
    ].sum()

    first_line = "Cálculo de Custos x Custo Limite"

    sec_line = (
        "CustoLimite - "
        + "(VariaveisPagos+FixosPagos+Outros)"
        + " - (VariaveisPendentes + FixosPendentes)"
    )

    third_line = (
        f"{cost_limit} - "
        + f"({var_paid} + {fixed_paid} + {other_payments_paid}) - "
        + f"({var_pending} + {fixed_pending})"
    )

    fourth_line = str(
        cost_limit
        - (var_paid + fixed_paid + other_payments_paid)
        - (var_pending + fixed_pending)
    )

    returned_str = "\n".join([first_line, sec_line, third_line, fourth_line])

    return returned_str


def info7(available_credit_limit):
    # pega limite que está sobrando
    return "Limite disponível: " + str(available_credit_limit)


def main():
    data: PersonalFinanceControl.RequestedData = PersonalFinanceControl.request_data(
        use_cached=True
    )

    print(info6(data.all_payments_categorized, data.planned_payments_analyzed))
    print(info7(data.available_credit_limit))


if __name__ == "__main__":
    main()
