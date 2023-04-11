import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from PersonalFinanceControl import PersonalFinanceControl


def main():
    data: PersonalFinanceControl.RequestedData = PersonalFinanceControl.request_data(
        use_cached=True
    )

    df = data.all_payments_categorized

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

    # plt.show()

    total_amount = df.groupby("type")["amount"].sum()
    percentages = 100 * total_amount / total_amount.sum()

    labels = [
        f"{type_}\n${amount:.2f}\n{percentage:.1f}%"
        for type_, amount, percentage in zip(
            total_amount.index, total_amount, percentages
        )
    ]

    plt.pie(x=total_amount, labels=labels)

    plt.show()


if __name__ == "__main__":
    main()
