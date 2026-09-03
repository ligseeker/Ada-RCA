# Magnitude-Inversion Audit

The frozen service magnitude is `A_i = mean over available channels of min(20, post-event magnitude)`. Rankings sort decreasing magnitude with canonical registry order for exact ties. This audit is label-free during score computation; labels are joined only for evaluation.

MI-1 means the true root is not rank 1. MI-3 means the true root rank is greater than 3. The terms are neutral diagnostics and do not imply propagated symptoms.

## RE2OB

Overall: MI-1 `66/0.7333`; MI-3 `25/0.2778`.

| Fault | Cases | MI-1 count/ratio | MI-3 count/ratio | Root rank distribution |
|---|---:|---:|---:|---|
| CPU | 15 | 11/0.7333 | 5/0.3333 | {'1': 4, '2': 4, '3': 2, '4': 2, '5': 2, '6': 1} |
| MEM | 15 | 12/0.8000 | 6/0.4000 | {'1': 3, '2': 4, '3': 2, '4': 5, '5': 1} |
| DISK | 15 | 11/0.7333 | 3/0.2000 | {'1': 4, '2': 7, '3': 1, '4': 2, '6': 1} |
| SOCKET | 15 | 11/0.7333 | 3/0.2000 | {'1': 4, '2': 6, '3': 2, '6': 1, '7': 2} |
| DELAY | 15 | 10/0.6667 | 3/0.2000 | {'1': 5, '2': 4, '3': 3, '4': 2, '5': 1} |
| LOSS | 15 | 11/0.7333 | 5/0.3333 | {'1': 4, '2': 1, '3': 5, '4': 2, '5': 3} |

Root rank distribution: `{'1': 24, '2': 26, '3': 15, '4': 13, '5': 7, '6': 3, '7': 2}`.

## RE2TT

Overall: MI-1 `90/1.0000`; MI-3 `85/0.9444`.

| Fault | Cases | MI-1 count/ratio | MI-3 count/ratio | Root rank distribution |
|---|---:|---:|---:|---|
| CPU | 15 | 15/1.0000 | 14/0.9333 | {'2': 1, '5': 2, '6': 1, '7': 1, '8': 3, '10': 1, '11': 1, '17': 2, '18': 1, '19': 1, '24': 1} |
| MEM | 15 | 15/1.0000 | 15/1.0000 | {'8': 1, '12': 2, '16': 2, '20': 1, '22': 1, '23': 2, '26': 1, '27': 1, '28': 2, '30': 2} |
| DISK | 15 | 15/1.0000 | 14/0.9333 | {'3': 1, '4': 1, '6': 1, '9': 2, '10': 1, '11': 1, '13': 1, '15': 2, '16': 1, '17': 1, '20': 1, '23': 1, '26': 1} |
| SOCKET | 15 | 15/1.0000 | 14/0.9333 | {'2': 1, '5': 1, '7': 1, '8': 1, '10': 1, '11': 1, '14': 1, '16': 1, '17': 2, '18': 4, '35': 1} |
| DELAY | 15 | 15/1.0000 | 15/1.0000 | {'6': 1, '7': 1, '10': 2, '11': 2, '13': 1, '15': 3, '16': 1, '17': 1, '24': 1, '53': 1, '54': 1} |
| LOSS | 15 | 15/1.0000 | 13/0.8667 | {'3': 2, '4': 1, '11': 1, '12': 1, '14': 2, '16': 1, '17': 1, '18': 1, '19': 1, '20': 1, '36': 1, '53': 1, '54': 1} |

Root rank distribution: `{'2': 2, '3': 3, '4': 2, '5': 3, '6': 3, '7': 3, '8': 5, '9': 2, '10': 5, '11': 6, '12': 3, '13': 2, '14': 3, '15': 5, '16': 6, '17': 7, '18': 6, '19': 2, '20': 3, '22': 1, '23': 3, '24': 2, '26': 2, '27': 1, '28': 2, '30': 2, '35': 1, '36': 1, '53': 2, '54': 2}`.

MI audit is diagnostic and does not replace the full benchmark or the P3-G1 gate.
