import pandas as pd
from pathlib import Path

result_path_sa = 'results/data_test02/results_sa-east-1.csv'
result_path_us = 'results/data_test02/results_us-east-1.csv'


def get_round_to_market(all_test_size,df):
    current_size = all_test_size
    round = []
    for index, row in df.iterrows():
        if len(round) < current_size:
            round.append(row)
            if ( (row['Status'] != 'SUCCESS') ):
                current_size = current_size - 4
        else:
            break
    return round
def process_round(df):
    new_df = df.groupby('Instance')[['Price','Time_in_Seconds','Mops_Total','Mops_per_Thread']].mean()
    estimatize_cost = (new_df['Time_in_Seconds'] * new_df['Price']) / 3600
    print(estimatize_cost)


all_test_size = 8*5
csv_file1 = Path(result_path_sa)
csv_file2 = Path(result_path_us)

if not csv_file1.exists():
    print(f"File {csv_file1} not found")
    raise FileNotFoundError

df1 = pd.read_csv(csv_file1)

if not csv_file2.exists():
    print(f"File {csv_file2} not found")
    raise FileNotFoundError

df2 = pd.read_csv(csv_file2)
dfaux1 = df1
dfaux2 = df2
dfaux1['Calculated_Cost'] = ((dfaux1['Time_in_Seconds'] * dfaux1['Price']) / 3600)
dfaux2['Calculated_Cost'] = ((dfaux2['Time_in_Seconds'] * dfaux2['Price']) / 3600)
def calculated_cost_for_periodic(dfaux1,hours):
    shift = 24/hours
    df = dfaux1[dfaux1['Market'] == 'ondemand'].copy()

    df['Cost * X'] = df['Calculated_Cost'] * shift

    #print(f"Estimativa de custo de testes por instância a cada: {hours}")
    #print(df.groupby('Instance')[['Cost * X']].mean())
    total_cost = 0
    test = df.groupby('Instance')['Cost * X'].mean()

    for idx in range(len(test)):
        if not pd.isna(test.iloc[idx]):
            total_cost += test.iloc[idx]
    print(f"Custo total estimado por dia: {total_cost}")

hour = 6
print(f"Estimativa de custos com rodadas a cada: {hour} horas")
print("SA-EAST-1:")
calculated_cost_for_periodic(dfaux1,hour)
print("US-EAST-1:")
calculated_cost_for_periodic(dfaux2,hour)