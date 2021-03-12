#%%
import pandas as pd
import numpy as np
import time
import datetime

cols = ["1", "60", "240"]
df = pd.DataFrame([[0,0,0],[0,0,2],[0,0,3]],columns = cols)
df = df.append(
    pd.Series(
        data=
        [
            10,
            15,
            20,
        ],
        index = cols
    ),
    ignore_index=True
)


# df = pd.DataFrame([[0,0,3]], index = [1274124], columns = cols)

# df = pd.DataFrame([[4, 9]] * 3, columns=['A', 'B'])
# df.apply(lambda x: pd.Series([1, 2], index=['foo', 'bar']), axis=1)

# df = pd.DataFrame(np.array(([1], [4],[4],[4],[4],[4],[4])),
#                   index=[4,5,6,7,8,9,10],
#                   columns=['one'])



# df = pd.DataFrame([[1, 0],[0, 1],[0, 1],[0, 1],[1, 0]], columns=['A', 'B'])
# print(df)
# print(df.shift(1))

# df['pA'] = df['A'].shift(1)
# df['pB'] = df['B'].shift(1)

# def calc(x):
#     if x.A == x.pA:
#         return None
#     elif x.A == x.pB == 1:
#         return True
#     else:
#         return False

# df['res'] = df.apply(calc, axis = 1)
# print(df)

# hour = datetime.datetime.fromtimestamp(1577275000).hour
# mint = datetime.datetime.fromtimestamp(1577275000).minute
# print(hour, mint)
# ts = 1614711600
# print(ts - datetime.datetime.fromtimestamp(ts). minute)


# df = pd.DataFrame({'key': ['K2', 'K2', 'K2', 'K3', 'K4', 'K4'],
#                    'A': ['A0', 'A1', 'A2', 'A3', 'A4', 'A5']})

# other = pd.DataFrame({'B': ['B0', 'B1', 'B2', 'B3', 'B4', 'B5'], 'C': ['C0', 'C1', 'C2', 'C3', 'C4', 'C5']}, index = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6'])
# print(df)
# print(other)

# df = df.join(other[['C','B']], on = "key")
# print(df)


# df = pd.DataFrame({'A': ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], 'B': [1,float("nan"),float("nan"),float("nan"),5,6]})
# df['B'] = df.apply(lambda x: x.name %2 ==0, axis = 1)
# df = df.fillna(method="ffill")
# print(df.iloc[-1].name)

# df = pd.DataFrame([[True,True, False, True]], columns = ['hma', 'aroon', 'a', 'b'])
# row = df.iloc[0]
# print(row)
# signals = ['hma', 'aroon']
# print(all([row[s] for s in signals]))
# print(not any(a))

print(int(time.time()))


# x = {'success': True, 'ret_msg': '', 'conn_id': '51700372-51d5-4a53-9fd2-e2f599baa5b0', 'request': {'op': 'subscribe', 'args': ['position', 'execution', 'order', 'klineV2.1.BTCUSD']}}
# print(x.get("request", {}).get("op"))
# print(False == None)

# from collections import deque
# x = deque([[1615119300.0, 50846.0, 50846.0, 50800.0, 50800.0, 1601387.0, 31.5052802], [1615119360.0, 50800.0, 50805.5, 50800.0, 50805.0, 1217352.0, 23.96241672], [1615119420.0, 50805.0, 50824.5, 50805.0, 50824.5, 1397918.0, 27.51087680000003], [1615119480.0, 50824.5, 50824.5, 50810.0, 50810.5, 1965923.0, 38.681934870000035], [1615119540.0, 50810.5, 50810.5, 50668.0, 50674.5, 8745269.0, 172.3508098799997], [1615119600.0, 50674.5, 50697.5, 50630.5, 50634.5, 3808455.0, 75.16149587000001], [1615119660.0, 50634.5, 50635.0, 50600.0, 50622.0, 4056159.0, 80.14147836000005]])