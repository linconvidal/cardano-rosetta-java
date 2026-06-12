# Detailed Load Test Results

Per concurrency step results for each endpoint

## /account/balance

| Dimension | Level | Concurrency | p95 (ms) | p99 (ms) | Meets SLA | Complete Reqs | Reqs/sec | Mean Time (ms) | Non-2xx | Error Rate (%) | Meets Error Threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| utxo_count | 1-9 UTXOs | 1 | 1235ms | 1440ms | No | 34 | 1.10 | 906.20ms | 0 | 0.00% | Yes |
| utxo_count | 10-99 UTXOs | 1 | 1422ms | 1431ms | No | 25 | 0.81 | 1237.10ms | 0 | 0.00% | Yes |
| utxo_count | 100-999 UTXOs | 1 | 1535ms | 1584ms | No | 21 | 0.70 | 1430.70ms | 0 | 0.00% | Yes |
| utxo_count | 1000-9999 UTXOs | 1 | 9251ms | 9251ms | No | 8 | 0.26 | 3882.46ms | 0 | 0.00% | Yes |
| utxo_count | ≥10000 UTXOs | 1 | 0ms | 0ms | Yes | 0 | 0.00 | 0.00ms | 0 | 0.00% | Yes |

## /account/coins

| Dimension | Level | Concurrency | p95 (ms) | p99 (ms) | Meets SLA | Complete Reqs | Reqs/sec | Mean Time (ms) | Non-2xx | Error Rate (%) | Meets Error Threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| utxo_count | 1-9 UTXOs | 1 | 1207ms | 1251ms | No | 34 | 1.12 | 894.60ms | 0 | 0.00% | Yes |
| utxo_count | 10-99 UTXOs | 1 | 1401ms | 1460ms | No | 25 | 0.81 | 1236.28ms | 0 | 0.00% | Yes |
| utxo_count | 100-999 UTXOs | 1 | 1784ms | 1784ms | No | 20 | 0.66 | 1509.53ms | 0 | 0.00% | Yes |
| utxo_count | 1000-9999 UTXOs | 1 | 4332ms | 4332ms | No | 9 | 0.28 | 3611.62ms | 0 | 0.00% | Yes |
| utxo_count | ≥10000 UTXOs | 1 | 0ms | 0ms | Yes | 0 | 0.00 | 0.00ms | 0 | 0.00% | Yes |

