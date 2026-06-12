# Summary Load Test Results

Maximum concurrency achieved per endpoint

| ID | Release | Dimension | Level | Endpoint | Max Concurrency | p95 (ms) | p99 (ms) | Non-2xx | Error Rate (%) | Reqs/sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2.0.0 | utxo_count | 1-9 UTXOs | /account/balance | 1 | 1235ms | 1440ms | 0 | 0.00% | 1.10 |
| 2 | 2.0.0 | utxo_count | 1-9 UTXOs | /account/coins | 1 | 1207ms | 1251ms | 0 | 0.00% | 1.12 |
| 3 | 2.0.0 | utxo_count | 10-99 UTXOs | /account/balance | 1 | 1422ms | 1431ms | 0 | 0.00% | 0.81 |
| 4 | 2.0.0 | utxo_count | 10-99 UTXOs | /account/coins | 1 | 1401ms | 1460ms | 0 | 0.00% | 0.81 |
| 5 | 2.0.0 | utxo_count | 100-999 UTXOs | /account/balance | 1 | 1535ms | 1584ms | 0 | 0.00% | 0.70 |
| 6 | 2.0.0 | utxo_count | 100-999 UTXOs | /account/coins | 1 | 1784ms | 1784ms | 0 | 0.00% | 0.66 |
| 7 | 2.0.0 | utxo_count | 1000-9999 UTXOs | /account/balance | 1 | 9251ms | 9251ms | 0 | 0.00% | 0.26 |
| 8 | 2.0.0 | utxo_count | 1000-9999 UTXOs | /account/coins | 1 | 4332ms | 4332ms | 0 | 0.00% | 0.28 |
| 9 | 2.0.0 | utxo_count | ≥10000 UTXOs | /account/balance | 1 | 0ms | 0ms | 0 | 0.00% | 0.00 |
| 10 | 2.0.0 | utxo_count | ≥10000 UTXOs | /account/coins | 1 | 0ms | 0ms | 0 | 0.00% | 0.00 |
