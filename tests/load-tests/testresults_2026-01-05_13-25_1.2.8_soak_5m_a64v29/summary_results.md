# Soak Test Results Summary

**Test Parameters:**
- URL: http://localhost:8082
- Users: 10
- Spawn Rate: 5/s
- Duration: 5m
- Network: mainnet
- Release: 1.2.8

## Per-Endpoint Results

| Endpoint | Requests | Failures | Avg (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Req/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /account/balance [token_count_1000] | 2 | 0 | 1899.430248498902 | 1928 | 1928 | 1928 | 0.009 |
| /account/balance [token_count_100] | 3 | 0 | 2037.5800869999996 | 595 | 4972 | 4972 | 0.014 |
| /account/balance [token_count_10] | 3 | 0 | 583.8264300000446 | 400 | 1091 | 1091 | 0.014 |
| /account/balance [token_count_1] | 2 | 0 | 396.19781100009277 | 396 | 396 | 396 | 0.009 |
| /account/balance [utxo_count_10000] | 3 | 0 | 87224.09800399934 | 64712 | 137436 | 137436 | 0.014 |
| /account/balance [utxo_count_1000] | 5 | 0 | 35287.85732920005 | 17078 | 87421 | 87421 | 0.023 |
| /account/balance [utxo_count_100] | 1 | 0 | 2663.8408889994025 | 2663 | 2663 | 2663 | 0.005 |
| /account/balance [utxo_count_10] | 3 | 0 | 814.3361956669347 | 821 | 1290 | 1290 | 0.014 |
| /account/balance [utxo_count_1] | 1 | 0 | 375.0142409990076 | 375 | 375 | 375 | 0.005 |
| /account/coins [token_count_1000] | 2 | 0 | 2580.7337520000146 | 2916 | 2916 | 2916 | 0.009 |
| /account/coins [token_count_100] | 1 | 0 | 668.5856799995236 | 668 | 668 | 668 | 0.005 |
| /account/coins [token_count_10] | 4 | 0 | 456.38750524994975 | 431 | 763 | 763 | 0.018 |
| /account/coins [token_count_1] | 1 | 0 | 398.27530100228614 | 398 | 398 | 398 | 0.005 |
| /account/coins [utxo_count_10000] | 1 | 0 | 115827.23507699848 | 115827 | 115827 | 115827 | 0.005 |
| /account/coins [utxo_count_1000] | 1 | 0 | 197704.36381900072 | 197704 | 197704 | 197704 | 0.005 |
| /account/coins [utxo_count_100] | 4 | 0 | 2468.898301500303 | 3062 | 3073 | 3073 | 0.018 |
| /account/coins [utxo_count_10] | 5 | 0 | 5109.373126999708 | 1206 | 14303 | 14303 | 0.023 |
| /account/coins [utxo_count_1] | 1 | 0 | 397.1003840015328 | 397 | 397 | 397 | 0.005 |
| /block [block_body_size_p50] | 2 | 0 | 345.9906374991988 | 360 | 360 | 360 | 0.009 |
| /block [block_body_size_p90] | 2 | 0 | 684.1641350001737 | 759 | 759 | 759 | 0.009 |
| /block [block_era_babbage] | 1 | 0 | 479.21280300215585 | 479 | 479 | 479 | 0.005 |
| /block [block_era_byron] | 2 | 0 | 368.6145240026235 | 372 | 372 | 372 | 0.009 |
| /block [block_era_conway] | 1 | 0 | 444.46774300013203 | 444 | 444 | 444 | 0.005 |
| /block [block_era_mary] | 1 | 0 | 339.52314099951764 | 339 | 339 | 339 | 0.005 |
| /block [block_tx_count_p50] | 1 | 0 | 384.7387929999968 | 384 | 384 | 384 | 0.005 |
| /block [block_tx_count_p95] | 2 | 0 | 1647.5747390013566 | 2526 | 2526 | 2526 | 0.009 |
| /block [block_tx_count_p99] | 2 | 0 | 1481.441571000687 | 2320 | 2320 | 2320 | 0.009 |
| /block/transaction [tx_has_script_false] | 1 | 0 | 417.57778499959386 | 417 | 417 | 417 | 0.005 |
| /block/transaction [tx_io_count_100] | 2 | 0 | 714.6589994990791 | 830 | 830 | 830 | 0.009 |
| /block/transaction [tx_io_count_10] | 1 | 0 | 569.0669980031089 | 569 | 569 | 569 | 0.005 |
| /block/transaction [tx_token_count_p50] | 1 | 0 | 349.2503880006552 | 349 | 349 | 349 | 0.005 |
| /block/transaction [tx_token_count_p75] | 1 | 0 | 571.2823149988253 | 571 | 571 | 571 | 0.005 |
| /block/transaction [tx_token_count_p90] | 1 | 0 | 390.8429729999625 | 390 | 390 | 390 | 0.005 |
| /block/transaction [tx_token_count_p95] | 1 | 0 | 640.6792569978279 | 640 | 640 | 640 | 0.005 |
| /block/transaction [tx_token_count_p99] | 1 | 0 | 324.27016599831404 | 324 | 324 | 324 | 0.005 |
| /construction/metadata [large_tx] | 1 | 0 | 195.0782479980262 | 195 | 195 | 195 | 0.005 |
| /construction/metadata [small_tx] | 4 | 0 | 296.2516202487677 | 370 | 424 | 424 | 0.018 |
| /network/status | 3 | 0 | 1154.4322669991136 | 1536 | 1539 | 1539 | 0.014 |
| /search/transactions [tx_has_script_false] | 1 | 0 | 1535.8569449999777 | 1535 | 1535 | 1535 | 0.005 |
| /search/transactions [tx_io_count_100] | 3 | 0 | 584.0104036663737 | 688 | 730 | 730 | 0.014 |
| /search/transactions [tx_io_count_1] | 2 | 0 | 284.5310945012898 | 347 | 347 | 347 | 0.009 |
| /search/transactions [tx_token_count_p50] | 1 | 0 | 408.689374999085 | 408 | 408 | 408 | 0.005 |
| /search/transactions [tx_token_count_p75] | 4 | 0 | 843.6582784997881 | 405 | 2318 | 2318 | 0.018 |
| /search/transactions [tx_token_count_p90] | 1 | 0 | 317.0508830007748 | 317 | 317 | 317 | 0.005 |
| /search/transactions [tx_token_count_p99] | 1 | 0 | 1535.0777120002022 | 1535 | 1535 | 1535 | 0.005 |

**Aggregated:** 87 requests, 0 failures, avg 9691.787829942477ms, p95 64712ms, p99 197704ms, 0.401 req/s
